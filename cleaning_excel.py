"""
Excel Processing Script
-----------------------
1. Cleans the trial_id column by removing parenthetical suffixes like (ABCDEF).
2. Adds a 'TA - I' column combining therapy_area and ot_disease_name.
3. Deduplicates on TA - I by keeping only the highest-phase row(s).
4. Deduplicates on (TA - I, trial_id).
5. Fetches trial_id, primary_region, secondary_countries, size, drug_arm_size_n from BigQuery
   and left-joins them onto the processed Excel data on trial_id.
6. For rows where primary_region, size, or drug_arm_size_n are still missing:
   a. ClinicalTrials.gov REST API (v2) for each NCT* trial ID.
   b. Gemini with Google Search grounding for anything still missing.

.env variables required:
    OUTPUT_FILE                    - Path to the input Excel file
    GOOGLE_APPLICATION_CREDENTIALS - Path to the GCP service account JSON
    PROJECT_ID                     - GCP project ID
    BQ_DATASET_ID                  - BigQuery dataset ID
    SSTABLE                        - BigQuery table name
    GEMINI_API_KEY                 - Gemini API key
    FALLBACK_TRIALS_PER_CALL       - Number of trials per Gemini call (default: 5)
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_missing(val) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() in ("", "nan", "None"):
        return True
    return False


# ---------------------------------------------------------------------------
# Phase ranking
# ---------------------------------------------------------------------------

def phase_rank(phase_value) -> int:
    if pd.isna(phase_value):
        return -1
    text = str(phase_value).strip().lower()
    if "approved" in text or "approv" in text or "market" in text:
        return 4
    roman = {"iii": 3, "ii": 2, "i": 1, "iv": 4}
    for numeral, val in roman.items():
        if re.search(rf"\b{numeral}\b", text):
            return val
    m = re.search(r"\b([1-4])\b", text)
    if m:
        return int(m.group(1))
    return -1


# ---------------------------------------------------------------------------
# BigQuery fetch
# ---------------------------------------------------------------------------

def fetch_bq_data(project_id, dataset_id, table):
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT trial_id, primary_region, secondary_countries, size, drug_arm_size_n
        FROM `{project_id}.{dataset_id}.{table}`
    """
    print(f"Fetching BQ data from `{project_id}.{dataset_id}.{table}` ...")
    bq_df = client.query(query).to_dataframe()
    print(f"  Fetched {len(bq_df)} rows from BigQuery.")
    return bq_df


# ---------------------------------------------------------------------------
# Step 6a — ClinicalTrials.gov API
# ---------------------------------------------------------------------------

_COUNTRY_TO_REGION = {
    "United States": "United States",
    "Canada": "North America", "Mexico": "North America",
    "United Kingdom": "Europe", "Germany": "Europe", "France": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Netherlands": "Europe",
    "Belgium": "Europe", "Switzerland": "Europe", "Sweden": "Europe",
    "Norway": "Europe", "Denmark": "Europe", "Finland": "Europe",
    "Austria": "Europe", "Poland": "Europe", "Czech Republic": "Europe",
    "Portugal": "Europe", "Greece": "Europe", "Hungary": "Europe",
    "Romania": "Europe", "Russia": "Europe", "Ukraine": "Europe",
    "Turkey": "Europe", "Turkey (Turkiye)": "Europe", "Turkiye": "Europe",
    "China": "Asia-Pacific", "Japan": "Asia-Pacific", "South Korea": "Asia-Pacific",
    "Korea, Republic of": "Asia-Pacific", "Australia": "Asia-Pacific",
    "India": "Asia-Pacific", "Taiwan": "Asia-Pacific", "Singapore": "Asia-Pacific",
    "Hong Kong": "Asia-Pacific", "New Zealand": "Asia-Pacific",
    "Thailand": "Asia-Pacific", "Malaysia": "Asia-Pacific",
    "Indonesia": "Asia-Pacific", "Philippines": "Asia-Pacific", "Vietnam": "Asia-Pacific",
    "Brazil": "Latin America", "Argentina": "Latin America", "Chile": "Latin America",
    "Colombia": "Latin America", "Peru": "Latin America",
    "Israel": "Middle East", "Saudi Arabia": "Middle East",
    "United Arab Emirates": "Middle East", "Qatar": "Middle East",
    "Kuwait": "Middle East", "Jordan": "Middle East", "Lebanon": "Middle East",
    "Egypt": "Middle East",
    "South Africa": "Africa", "Nigeria": "Africa", "Kenya": "Africa",
}

_CT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _infer_region(countries):
    if not countries:
        return None
    region_counts = {}
    for c in countries:
        region = _COUNTRY_TO_REGION.get(c, "Other")
        region_counts[region] = region_counts.get(region, 0) + 1
    if len(countries) == 1:
        return _COUNTRY_TO_REGION.get(countries[0], countries[0])
    if "United States" in countries and all(c == "United States" for c in countries):
        return "United States"
    regions = set(region_counts.keys())
    if len(regions) == 1:
        return regions.pop()
    return "Global"


def _extract_size(study):
    """
    Try every known location in the CT.gov v2 JSON where enrollment count can appear.
    Returns an int or None.
    """
    protocol = study.get("protocolSection", {})

    # 1. designModule.enrollmentInfo.count  (most common)
    count = (
        protocol.get("designModule", {})
                .get("enrollmentInfo", {})
                .get("count")
    )
    if count is not None:
        try:
            return int(count)
        except (ValueError, TypeError):
            pass

    # 2. resultsSection.participantFlowModule — sum of all "STARTED" achievements
    #    (completed trials that posted results)
    flow = (
        study.get("resultsSection", {})
             .get("participantFlowModule", {})
    )
    periods = flow.get("periods", [])
    if periods:
        total = 0
        found = False
        for period in periods:
            for milestone in period.get("milestones", []):
                if milestone.get("type", "").upper() == "STARTED":
                    for achieve in milestone.get("achievements", []):
                        n = achieve.get("numSubjects")
                        if n is not None:
                            try:
                                total += int(n)
                                found = True
                            except (ValueError, TypeError):
                                pass
        if found:
            return total

    # 3. eligibilityModule sometimes has maximumAge / targetEnrollment in older records
    #    (rarely populated but worth checking)
    target = (
        protocol.get("eligibilityModule", {})
                .get("targetEnrollment")
    )
    if target is not None:
        try:
            return int(target)
        except (ValueError, TypeError):
            pass

    return None


def _extract_drug_arm_size(study):
    """
    Try every known location for drug/treatment arm participant count.
    Returns an int or None.
    """
    protocol = study.get("protocolSection", {})

    # Source 1: armsInterventionsModule.armGroups[].count
    arms = (
        protocol.get("armsInterventionsModule", {})
                .get("armGroups", [])
    )
    drug_arm_size = None
    for arm in arms:
        arm_type = arm.get("type", "").upper()
        if arm_type in ("EXPERIMENTAL", "ACTIVE_COMPARATOR"):
            count = arm.get("count")
            if count is not None:
                try:
                    drug_arm_size = (drug_arm_size or 0) + int(count)
                except (ValueError, TypeError):
                    pass

    if drug_arm_size is not None:
        return drug_arm_size

    # Source 2: resultsSection.participantFlowModule — STARTED milestones,
    #           excluding placebo/control/sham groups
    flow = (
        study.get("resultsSection", {})
             .get("participantFlowModule", {})
    )
    groups = flow.get("groups", [])
    periods = flow.get("periods", [])

    skip_kw = ("placebo", "control", "sham", "no treatment", "observation", "vehicle")
    drug_group_ids = {
        g["id"] for g in groups
        if not any(kw in g.get("title", "").lower() for kw in skip_kw)
        and g.get("id")
    }

    if drug_group_ids and periods:
        total = 0
        found = False
        for period in periods:
            for milestone in period.get("milestones", []):
                if milestone.get("type", "").upper() == "STARTED":
                    for achieve in milestone.get("achievements", []):
                        if achieve.get("groupId") in drug_group_ids:
                            n = achieve.get("numSubjects")
                            if n is not None:
                                try:
                                    total += int(n)
                                    found = True
                                except (ValueError, TypeError):
                                    pass
        if found:
            return total

    return None


def _fetch_one_nct(nct_id, retries=4, delay=2.0):
    """
    Fetch a single NCT study from ClinicalTrials.gov v2.
    Returns dict with primary_region, size, drug_arm_size_n — or None on failure.
    """
    params = urllib.parse.urlencode({"filter.ids": nct_id, "pageSize": 1})
    url = f"https://clinicaltrials.gov/api/v2/studies?{params}"

    data = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=_CT_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                wait = delay * (2 ** (attempt - 1))
                print(f"    CT.gov HTTP {e.code} for {nct_id}, retry in {wait:.0f}s ...")
                time.sleep(wait)
                if attempt == retries:
                    print(f"    CT.gov: gave up on {nct_id}.")
                    return None
            else:
                print(f"    CT.gov fetch error for {nct_id}: HTTP {e.code} {e.reason}")
                return None
        except Exception as e:
            if attempt == retries:
                print(f"    CT.gov fetch error for {nct_id}: {e}")
                return None
            time.sleep(delay * attempt)

    if data is None:
        return None

    studies = data.get("studies", [])
    if not studies:
        print(f"    CT.gov: no study found for {nct_id}")
        return None

    study = studies[0]
    protocol = study.get("protocolSection", {})

    # Verify the returned NCT ID matches
    returned_nct = protocol.get("identificationModule", {}).get("nctId", "")
    if returned_nct.upper() != nct_id.upper():
        print(f"    CT.gov ID mismatch for {nct_id} (got {returned_nct}), skipping.")
        return None

    size = _extract_size(study)
    drug_arm_size = _extract_drug_arm_size(study)

    # Primary region from locations
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})
    primary_region = _infer_region(countries)

    return {
        "primary_region": primary_region,
        "size": size,
        "drug_arm_size_n": drug_arm_size,
    }


def clinicaltrials_lookup(trial_ids, rate_limit_delay=0.5):
    nct_ids = [t for t in trial_ids if re.match(r"^NCT\d+", t, re.IGNORECASE)]
    results = {}
    if not nct_ids:
        return results

    print(f"  Querying ClinicalTrials.gov for {len(nct_ids)} NCT ID(s) ...")
    for i, nct_id in enumerate(nct_ids, 1):
        print(f"    [{i}/{len(nct_ids)}] {nct_id} ...", end=" ", flush=True)
        result = _fetch_one_nct(nct_id)
        if result:
            results[nct_id] = result
            print(", ".join(f"{k}={v}" for k, v in result.items()))
        else:
            print("not found")
        if i < len(nct_ids):
            time.sleep(rate_limit_delay)

    return results


# ---------------------------------------------------------------------------
# Step 6b — Gemini fallback
# ---------------------------------------------------------------------------

def _build_gemini_prompt(trial_ids):
    trials_list = "\n".join(f"- {t}" for t in trial_ids)
    return f"""You are a clinical trial data expert. Use Google Search to look up each trial ID below.

Trial IDs:
{trials_list}

For each trial find:
- primary_region: Primary geographic region (e.g. "United States", "Europe", "Global", "Asia-Pacific")
- size: Total planned/actual enrollment (integer, total participants across all arms)
- drug_arm_size_n: Participants in drug/treatment arm only (integer), excluding placebo/control. null if unavailable.

Return ONLY a valid JSON array, no explanation, no markdown fences:
[
  {{"trial_id": "NCT12345678", "primary_region": "United States", "size": 500, "drug_arm_size_n": 250}},
  {{"trial_id": "NCT87654321", "primary_region": "Europe", "size": 300, "drug_arm_size_n": null}}
]

Use null if a value genuinely cannot be found. Do not guess.
"""


def _gemini_lookup_batch(trial_ids, api_key):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": _build_gemini_prompt(trial_ids)}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    try:
        parts = raw["candidates"][0]["content"]["parts"]
        text = next(
            (p["text"] for p in parts if "text" in p and not p.get("thought", False)),
            None,
        )
        if text is None:
            raise ValueError("No text part in Gemini response")
    except (KeyError, IndexError, ValueError) as e:
        print(f"  WARNING: Unexpected Gemini response: {e}")
        return []

    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    try:
        results = json.loads(text)
        return results if isinstance(results, list) else []
    except json.JSONDecodeError as e:
        print(f"  WARNING: Could not parse Gemini JSON: {e}\n  Raw: {text[:500]}")
        return []


def gemini_fallback(trial_ids, api_key, batch_size):
    if not trial_ids:
        return {}
    print(f"  Sending {len(trial_ids)} trial(s) to Gemini (batch size {batch_size}) ...")
    batches = [trial_ids[i: i + batch_size] for i in range(0, len(trial_ids), batch_size)]
    results = {}
    for i, batch in enumerate(batches, 1):
        print(f"    Gemini batch {i}/{len(batches)}: {batch}")
        try:
            entries = _gemini_lookup_batch(batch, api_key)
            for entry in entries:
                tid = str(entry.get("trial_id", "")).strip()
                if tid:
                    results[tid] = entry
        except Exception as e:
            print(f"  WARNING: Gemini call failed for batch {i}: {e}")
        if i < len(batches):
            time.sleep(2)
    return results


# ---------------------------------------------------------------------------
# Combined fallback — fills missing fields column-by-column
# ---------------------------------------------------------------------------

def fill_missing_fields(df, api_key, batch_size):
    """
    Fills primary_region, size, and drug_arm_size_n wherever missing.
    Processes each column independently so a row with only `size` missing
    is still looked up — it is NOT skipped just because other fields are filled.
    """
    target_cols = ["primary_region", "size", "drug_arm_size_n"]

    for col in target_cols:
        if col not in df.columns:
            df[col] = None

    # Build a per-column missing mask so we know exactly what needs filling
    missing_masks = {
        col: df[col].apply(is_missing)
        for col in target_cols
    }

    # Rows missing at least one target column
    any_missing_mask = missing_masks["primary_region"] | missing_masks["size"] | missing_masks["drug_arm_size_n"]
    needs_fill_idx = df.index[any_missing_mask].tolist()

    if not needs_fill_idx:
        print("Step 6: No rows with missing fields. Skipping fallback.")
        return df

    # Detailed per-column summary
    print(f"\nStep 6 — Missing field summary (before fallback):")
    print(f"  Total rows              : {len(df)}")
    for col in target_cols:
        n = missing_masks[col].sum()
        print(f"  Missing {col:25s}: {n} row(s)")

    unique_trials = [
        t for t in df.loc[needs_fill_idx, "trial_id"].dropna().unique()
        if str(t).strip().lower() not in ("", "nan")
    ]
    print(f"\n  {len(needs_fill_idx)} row(s) need fallback across {len(unique_trials)} unique trial ID(s).")

    # ---- 6a: ClinicalTrials.gov ----
    ctgov_results = clinicaltrials_lookup(unique_trials)

    filled_ctgov = 0
    for idx in needs_fill_idx:
        tid = str(df.at[idx, "trial_id"]).strip()
        entry = ctgov_results.get(tid)
        if not entry:
            continue
        for col in target_cols:
            if is_missing(df.at[idx, col]) and entry.get(col) is not None:
                df.at[idx, col] = entry[col]
                filled_ctgov += 1
    print(f"  CT.gov filled {filled_ctgov} cell(s).")

    # ---- 6b: Gemini for still-missing ----
    # Recompute which rows still have any missing field
    still_missing_mask = df[target_cols].apply(lambda c: c.apply(is_missing)).any(axis=1)
    still_missing_idx = df.index[still_missing_mask & any_missing_mask].tolist()

    still_missing_trials = [
        t for t in df.loc[still_missing_idx, "trial_id"].dropna().unique()
        if str(t).strip().lower() not in ("", "nan")
    ]

    if still_missing_trials:
        print(f"  {len(still_missing_trials)} trial(s) still missing fields → Gemini ...")
        gemini_results = gemini_fallback(still_missing_trials, api_key, batch_size)

        filled_gemini = 0
        for idx in still_missing_idx:
            tid = str(df.at[idx, "trial_id"]).strip()
            entry = gemini_results.get(tid)
            if not entry:
                continue
            for col in target_cols:
                if is_missing(df.at[idx, col]) and entry.get(col) is not None:
                    df.at[idx, col] = entry[col]
                    filled_gemini += 1
        print(f"  Gemini filled {filled_gemini} cell(s).")
    else:
        print("  All fields resolved by CT.gov. Gemini not needed.")

    # ---- Final summary ----
    print(f"\nStep 6 — Missing field summary (after fallback):")
    print(f"  Total rows              : {len(df)}")
    for col in target_cols:
        n = df[col].apply(is_missing).sum()
        print(f"  Still missing {col:20s}: {n} row(s)")

    still_any = df[target_cols].apply(lambda c: c.apply(is_missing)).any(axis=1)
    remaining = df.loc[still_any, ["trial_id"] + target_cols].drop_duplicates("trial_id")
    if not remaining.empty:
        print("  Unresolved trial IDs:")
        for _, row in remaining.iterrows():
            gaps = [c for c in target_cols if is_missing(row[c])]
            print(f"    {row['trial_id']} — still missing: {gaps}")

    print("Step 6 done.")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process():
    input_file     = os.getenv("OUTPUT_FILE")
    credentials    = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id     = os.getenv("PROJECT_ID")
    dataset_id     = os.getenv("BQ_DATASET_ID")
    bq_table       = os.getenv("SSTABLE")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    fallback_batch = os.getenv("FALLBACK_TRIALS_PER_CALL", "5")

    missing_vars = [k for k, v in {
        "OUTPUT_FILE": input_file,
        "GOOGLE_APPLICATION_CREDENTIALS": credentials,
        "PROJECT_ID": project_id,
        "BQ_DATASET_ID": dataset_id,
        "SSTABLE": bq_table,
        "GEMINI_API_KEY": gemini_api_key,
    }.items() if not v]

    if missing_vars:
        print(f"ERROR: Missing .env variable(s): {', '.join(missing_vars)}")
        sys.exit(1)

    try:
        batch_size = int(fallback_batch)
        if batch_size < 1:
            raise ValueError
    except ValueError:
        print("ERROR: FALLBACK_TRIALS_PER_CALL must be a positive integer.")
        sys.exit(1)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    output_path = input_path.with_name(input_path.stem + "_processed.xlsx")
    print(f"Input file  : {input_path}")
    print(f"Output file : {output_path}")

    df = pd.read_excel(input_path)

    # 1. Clean trial_id
    if "trial_id" not in df.columns:
        print("WARNING: 'trial_id' not found. Skipping step 1.")
    else:
        df["trial_id"] = (
            df["trial_id"].astype(str)
            .str.replace(r"\s*\(.*?\)\s*$", "", regex=True)
            .str.strip()
        )
        print("Step 1 done: trial_id cleaned.")

    # 2. Add TA - I
    missing_cols = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing_cols:
        print(f"WARNING: {missing_cols} not found. Skipping steps 2-4.")
    else:
        df["TA - I"] = df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        print("Step 2 done: 'TA - I' column added.")

        # 3. Deduplicate by highest phase
        if "phase" not in df.columns:
            print("WARNING: 'phase' not found. Skipping step 3.")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)
            df["_max_rank"]   = df.groupby("TA - I")["_phase_rank"].transform("max")
            before = len(df)
            df = df[df["_phase_rank"] == df["_max_rank"]].sort_index()
            df = df.drop(columns=["_phase_rank", "_max_rank"])
            print(f"Step 3 done: {before - len(df)} lower-phase row(s) removed.")

        # 4. Deduplicate (TA - I, trial_id)
        if "trial_id" in df.columns:
            before = len(df)
            df = df.drop_duplicates(subset=["TA - I", "trial_id"], keep="first").sort_index()
            print(f"Step 4 done: {before - len(df)} duplicate (TA-I, trial_id) row(s) removed.")

    # 5. BQ join
    if "trial_id" not in df.columns:
        print("WARNING: 'trial_id' not found. Skipping BQ join.")
    else:
        bq_df = fetch_bq_data(project_id, dataset_id, bq_table)
        bq_df["trial_id"] = bq_df["trial_id"].astype(str).str.strip()

        bq_cols = ["trial_id", "primary_region", "secondary_countries", "size", "drug_arm_size_n"]
        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            df = df.drop(columns=existing)

        df = df.merge(bq_df[bq_cols], on="trial_id", how="left")

        # Diagnostic: show what's missing and why after join
        target_check = ["primary_region", "size", "drug_arm_size_n"]
        bq_matched = df["secondary_countries"].notna()
        missing_any = df[target_check].apply(lambda c: c.apply(is_missing)).any(axis=1)

        print("Step 5 done: BQ columns joined.")
        print(f"  Total rows            : {len(df)}")
        print(f"  Matched in BQ         : {bq_matched.sum()}")
        print(f"  Not matched in BQ     : {(~bq_matched).sum()}")
        for col in target_check:
            n = df[col].apply(is_missing).sum()
            print(f"  Missing {col:25s}: {n}")
        print(f"  Matched in BQ but still missing fields : {(bq_matched & missing_any).sum()} (BQ has nulls)")
        print(f"  Not in BQ, missing fields              : {(~bq_matched & missing_any).sum()}")

    # 6. Fill all missing fields
    if "trial_id" in df.columns:
        df = fill_missing_fields(df, gemini_api_key, batch_size)

    df.to_excel(output_path, index=False)
    print(f"\nOutput saved: {output_path}")


if __name__ == "__main__":
    process()
