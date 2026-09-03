"""
Excel Processing Script
-----------------------
1. Cleans the trial_id column by removing parenthetical suffixes like (ABCDEF).
2. Adds a 'TA - I' column combining therapy_area and ot_disease_name.
3. Deduplicates on TA - I by keeping only the highest-phase row(s).
   Phase priority: Approved > 3 > 2 > 1 (fuzzy-matched).
   If multiple rows share the same TA - I and the same (highest) phase, all are kept.
4. Deduplicates on (TA - I, trial_id) — each combination must be unique, first occurrence kept.
5. Fetches trial_id, primary_region, secondary_countries, size, drug_arm_size_n from BigQuery
   and left-joins them onto the processed Excel data on trial_id.
6. For rows where primary_region, size, or drug_arm_size_n are still missing after the BQ join:
   a. First queries ClinicalTrials.gov REST API (v2) directly for each NCT* trial ID.
      Uses filter.ids (exact match) + browser User-Agent to avoid 403s.
   b. Any trial IDs still missing after that (e.g. EudraCT, non-NCT IDs) are sent to Gemini
      with Google Search grounding as a true last resort.

.env variables required:
    OUTPUT_FILE                    - Path to the input Excel file
    GOOGLE_APPLICATION_CREDENTIALS - Path to the GCP service account JSON
    PROJECT_ID                     - GCP project ID
    BQ_DATASET_ID                  - BigQuery dataset ID
    SSTABLE                        - BigQuery table name
    GEMINI_API_KEY                 - Gemini API key
    FALLBACK_TRIALS_PER_CALL       - Number of trials to send to Gemini in one call (default: 5)

Usage:
    python process_excel.py
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
    """Return True if a value is NaN, None, or an empty/whitespace string."""
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


# ---------------------------------------------------------------------------
# Phase ranking logic
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

def fetch_bq_data(project_id: str, dataset_id: str, table: str) -> pd.DataFrame:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT
            trial_id,
            primary_region,
            secondary_countries,
            size,
            drug_arm_size_n
        FROM `{project_id}.{dataset_id}.{table}`
    """
    print(f"Fetching BQ data from `{project_id}.{dataset_id}.{table}` ...")
    bq_df = client.query(query).to_dataframe()
    print(f"  Fetched {len(bq_df)} rows from BigQuery.")
    return bq_df


# ---------------------------------------------------------------------------
# Step 6a — ClinicalTrials.gov API (primary fallback, NCT IDs only)
# ---------------------------------------------------------------------------

_COUNTRY_TO_REGION = {
    # North America
    "United States": "United States",
    "Canada": "North America",
    "Mexico": "North America",
    # Europe
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Italy": "Europe",
    "Spain": "Europe",
    "Netherlands": "Europe",
    "Belgium": "Europe",
    "Switzerland": "Europe",
    "Sweden": "Europe",
    "Norway": "Europe",
    "Denmark": "Europe",
    "Finland": "Europe",
    "Austria": "Europe",
    "Poland": "Europe",
    "Czech Republic": "Europe",
    "Portugal": "Europe",
    "Greece": "Europe",
    "Hungary": "Europe",
    "Romania": "Europe",
    "Russia": "Europe",
    "Ukraine": "Europe",
    "Turkey": "Europe",
    "Turkey (Turkiye)": "Europe",
    "Turkiye": "Europe",
    # Asia-Pacific
    "China": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
    "Korea, Republic of": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "India": "Asia-Pacific",
    "Taiwan": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
    "Hong Kong": "Asia-Pacific",
    "New Zealand": "Asia-Pacific",
    "Thailand": "Asia-Pacific",
    "Malaysia": "Asia-Pacific",
    "Indonesia": "Asia-Pacific",
    "Philippines": "Asia-Pacific",
    "Vietnam": "Asia-Pacific",
    # Latin America
    "Brazil": "Latin America",
    "Argentina": "Latin America",
    "Chile": "Latin America",
    "Colombia": "Latin America",
    "Peru": "Latin America",
    # Middle East
    "Israel": "Middle East",
    "Saudi Arabia": "Middle East",
    "United Arab Emirates": "Middle East",
    "Qatar": "Middle East",
    "Kuwait": "Middle East",
    "Jordan": "Middle East",
    "Lebanon": "Middle East",
    "Egypt": "Middle East",
    # Africa
    "South Africa": "Africa",
    "Nigeria": "Africa",
    "Kenya": "Africa",
    "Ethiopia": "Africa",
}

# Browser-like User-Agent — CT.gov returns 403 for Python's default UA
_CT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _infer_region(countries: list) -> str:
    """
    Given a list of country strings from ClinicalTrials.gov, return the
    most appropriate primary_region label.
    """
    if not countries:
        return None

    region_counts = {}
    for c in countries:
        region = _COUNTRY_TO_REGION.get(c, "Other")
        region_counts[region] = region_counts.get(region, 0) + 1

    if len(countries) == 1:
        return _COUNTRY_TO_REGION.get(countries[0], countries[0])

    if "United States" in countries:
        non_us = [c for c in countries if c != "United States"]
        if not non_us:
            return "United States"

    regions = set(region_counts.keys())
    if len(regions) == 1:
        return regions.pop()

    return "Global"


def _fetch_one_nct(nct_id: str, retries: int = 4, delay: float = 2.0):
    """
    Query the ClinicalTrials.gov v2 REST API for a single NCT ID.
    Returns a dict with keys: primary_region, size, drug_arm_size_n  (or None on failure).

    IMPORTANT fixes vs prior version:
    - Uses `filter.ids` (exact NCT ID match), NOT `query.id` (fuzzy text search
      that silently returns wrong/no results for many valid NCT IDs).
    - Sends a browser-like User-Agent; CT.gov returns 403 for Python's default UA.
    - Verifies the returned NCT ID matches the requested one.
    - Exponential backoff on 429/5xx.
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = urllib.parse.urlencode({
        "filter.ids": nct_id,   # <-- exact match, not fuzzy query.id
        "pageSize": 1,
    })
    url = f"{base_url}?{params}"

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
                print(f"    CT.gov HTTP {e.code} for {nct_id}, retrying in {wait:.0f}s ...")
                time.sleep(wait)
                if attempt == retries:
                    print(f"    CT.gov: gave up on {nct_id} after {retries} attempts.")
                    return None
            else:
                print(f"    CT.gov fetch failed for {nct_id}: HTTP {e.code} {e.reason}")
                return None
        except Exception as e:
            if attempt == retries:
                print(f"    CT.gov fetch failed for {nct_id}: {e}")
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

    # Verify returned NCT ID matches (guard against API quirks)
    returned_nct = (
        protocol.get("identificationModule", {}).get("nctId", "")
    )
    if returned_nct.upper() != nct_id.upper():
        print(f"    CT.gov ID mismatch for {nct_id} (got {returned_nct}), skipping.")
        return None

    # --- enrollment / size ---
    design = protocol.get("designModule", {})
    enrollment_info = design.get("enrollmentInfo", {})
    size = enrollment_info.get("count")

    # --- drug arm size ---
    # Source 1: armsInterventionsModule (sometimes has count per arm)
    arms_module = protocol.get("armsInterventionsModule", {})
    arms = arms_module.get("armGroups", [])
    drug_arm_size = None

    for arm in arms:
        arm_type = arm.get("type", "").upper()
        if arm_type in ("EXPERIMENTAL", "ACTIVE_COMPARATOR"):
            count = arm.get("count")
            if count is not None:
                drug_arm_size = (drug_arm_size or 0) + int(count)

    # Source 2: resultsSection participantFlowModule (completed trials)
    if drug_arm_size is None:
        results_section = study.get("resultsSection", {})
        flow_module = results_section.get("participantFlowModule", {})
        groups = flow_module.get("groups", [])
        for group in groups:
            title = group.get("title", "").lower()
            if any(kw in title for kw in ("placebo", "control", "sham", "no treatment", "observation")):
                continue
            periods = flow_module.get("periods", [])
            for period in periods:
                for milestone in period.get("milestones", []):
                    if milestone.get("type", "").upper() == "STARTED":
                        for achieve in milestone.get("achievements", []):
                            if achieve.get("groupId") == group.get("id"):
                                n = achieve.get("numSubjects")
                                if n is not None:
                                    try:
                                        drug_arm_size = (drug_arm_size or 0) + int(n)
                                    except (ValueError, TypeError):
                                        pass

    # --- primary region ---
    locations_module = protocol.get("contactsLocationsModule", {})
    locations = locations_module.get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})
    primary_region = _infer_region(countries)

    return {
        "primary_region": primary_region,
        "size": int(size) if size is not None else None,
        "drug_arm_size_n": int(drug_arm_size) if drug_arm_size is not None else None,
    }


def clinicaltrials_lookup(trial_ids: list, rate_limit_delay: float = 0.5) -> dict:
    """
    Fetch data from ClinicalTrials.gov for all NCT* trial IDs.
    Returns mapping: trial_id -> {primary_region, size, drug_arm_size_n}.
    Non-NCT IDs are skipped (handled by Gemini fallback).
    """
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
            parts = [f"{k}={v}" for k, v in result.items()]
            print(", ".join(parts))
        else:
            print("not found")
        if i < len(nct_ids):
            time.sleep(rate_limit_delay)

    return results


# ---------------------------------------------------------------------------
# Step 6b — Gemini fallback with Google Search grounding (non-NCT / still missing)
# ---------------------------------------------------------------------------

def _build_gemini_prompt(trial_ids: list) -> str:
    trials_list = "\n".join(f"- {t}" for t in trial_ids)
    return f"""You are a clinical trial data expert. Use Google Search to look up each of the following clinical trial IDs and return their details.

Trial IDs:
{trials_list}

For each trial, find:
- primary_region: The primary geographic region where the trial is conducted (e.g. "United States", "Europe", "Global", "Asia-Pacific"). Use the most specific single region that best represents the trial's primary location.
- size: The total planned or actual enrollment number (integer). This is the total number of participants.
- drug_arm_size_n: The number of participants in the drug/treatment arm only (integer), excluding placebo/control arms. If not separately reported, return null.

Return ONLY a valid JSON array with no explanation, no markdown, no code fences. Example format:
[
  {{"trial_id": "NCT12345678", "primary_region": "United States", "size": 500, "drug_arm_size_n": 250}},
  {{"trial_id": "NCT87654321", "primary_region": "Europe", "size": 300, "drug_arm_size_n": null}}
]

If a value cannot be found after thorough searching, use null. Do not guess.
"""


def _gemini_lookup_batch(trial_ids: list, api_key: str) -> list:
    """Single Gemini API call for a batch of trial IDs."""
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
        url,
        data=body,
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
        print(f"  WARNING: Unexpected Gemini response structure: {e}")
        return []

    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    try:
        results = json.loads(text)
        return results if isinstance(results, list) else []
    except json.JSONDecodeError as e:
        print(f"  WARNING: Could not parse Gemini JSON: {e}\n  Raw: {text[:500]}")
        return []


def gemini_fallback(trial_ids: list, api_key: str, batch_size: int) -> dict:
    """
    Send trial IDs to Gemini (with Google Search grounding) in batches.
    Returns mapping: trial_id -> {primary_region, size, drug_arm_size_n}.
    """
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
# Combined fallback orchestrator
# ---------------------------------------------------------------------------

def fill_missing_fields(df: pd.DataFrame, api_key: str, batch_size: int) -> pd.DataFrame:
    """
    For rows where primary_region, size, or drug_arm_size_n are missing:
      1. Query ClinicalTrials.gov for NCT IDs (structured, free, reliable).
      2. Query Gemini (Google Search grounded) for anything still missing.
    """
    target_cols = ["primary_region", "size", "drug_arm_size_n"]

    for col in target_cols:
        if col not in df.columns:
            df[col] = None

    def _needs_fill(row):
        return any(is_missing(row.get(col)) for col in target_cols)

    needs_fill_mask = df.apply(_needs_fill, axis=1)
    needs_fill_idx = df.index[needs_fill_mask].tolist()

    if not needs_fill_idx:
        print("Step 6: No rows with missing fields. Skipping fallback.")
        return df

    unique_trials = [
        t for t in df.loc[needs_fill_idx, "trial_id"].dropna().unique()
        if str(t).strip().lower() not in ("", "nan")
    ]
    print(f"\nStep 6: {len(needs_fill_idx)} row(s) need fallback across {len(unique_trials)} unique trial ID(s).")

    # ---- 6a: ClinicalTrials.gov (NCT IDs) ----
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

    # ---- 6b: Gemini for still-missing trials ----
    still_missing_mask = df.apply(_needs_fill, axis=1)
    still_missing_idx = df.index[still_missing_mask & needs_fill_mask].tolist()

    still_missing_trials = [
        t for t in df.loc[still_missing_idx, "trial_id"].dropna().unique()
        if str(t).strip().lower() not in ("", "nan")
    ]

    if still_missing_trials:
        print(f"  {len(still_missing_trials)} trial(s) still have missing fields → sending to Gemini ...")
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

    # ---- Final report (fixed: use boolean mask, not list index) ----
    originally_missing_df = df.loc[needs_fill_idx]
    final_still_missing = originally_missing_df.apply(_needs_fill, axis=1)
    still_empty = final_still_missing.sum()
    if still_empty:
        missing_ids = originally_missing_df.loc[final_still_missing, "trial_id"].unique()
        print(f"  WARNING: {still_empty} row(s) still have missing fields after all fallbacks.")
        print(f"  Affected trial IDs: {list(missing_ids)}")
    else:
        print("  All missing fields have been resolved.")

    print("Step 6 done.")
    return df


# ---------------------------------------------------------------------------
# Main processing
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
        print(f"ERROR: Missing required .env variable(s): {', '.join(missing_vars)}")
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
        print("WARNING: Column 'trial_id' not found. Skipping step 1.")
    else:
        df["trial_id"] = (
            df["trial_id"]
            .astype(str)
            .str.replace(r"\s*\(.*?\)\s*$", "", regex=True)
            .str.strip()
        )
        print("Step 1 done: trial_id cleaned.")

    # 2. Add 'TA - I' column
    missing_cols = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing_cols:
        print(f"WARNING: Column(s) {missing_cols} not found. Skipping steps 2, 3 & 4.")
    else:
        df["TA - I"] = df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        print("Step 2 done: 'TA - I' column added.")

        # 3. Deduplicate on TA - I by keeping highest-phase row(s)
        if "phase" not in df.columns:
            print("WARNING: Column 'phase' not found. Skipping step 3.")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)
            df["_max_rank"]   = df.groupby("TA - I")["_phase_rank"].transform("max")
            original_count    = len(df)
            df = df[df["_phase_rank"] == df["_max_rank"]]
            df = df.sort_index().drop(columns=["_phase_rank", "_max_rank"])
            print(f"Step 3 done: {original_count - len(df)} lower-phase duplicate TA - I row(s) removed.")

        # 4. Deduplicate on (TA - I, trial_id)
        if "trial_id" not in df.columns:
            print("WARNING: Column 'trial_id' not found. Skipping step 4.")
        else:
            before = len(df)
            df = df.drop_duplicates(subset=["TA - I", "trial_id"], keep="first").sort_index()
            print(f"Step 4 done: {before - len(df)} duplicate (TA - I, trial_id) combination(s) removed.")

    # 5. Fetch from BigQuery and left-join on trial_id
    if "trial_id" not in df.columns:
        print("WARNING: Column 'trial_id' not found. Skipping BQ join (step 5).")
    else:
        bq_df = fetch_bq_data(project_id, dataset_id, bq_table)
        bq_df["trial_id"] = bq_df["trial_id"].astype(str).str.strip()

        bq_cols = ["trial_id", "primary_region", "secondary_countries", "size", "drug_arm_size_n"]
        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            print(f"  Note: Overwriting existing column(s) from BQ data: {existing}")
            df = df.drop(columns=existing)

        df = df.merge(bq_df[bq_cols], on="trial_id", how="left")
        print("Step 5 done: BQ columns joined.")

    # 6. Fill missing fields: CT.gov first, then Gemini for anything left
    if "trial_id" not in df.columns:
        print("WARNING: Column 'trial_id' not found. Skipping fallback (step 6).")
    else:
        df = fill_missing_fields(df, gemini_api_key, batch_size)

    df.to_excel(output_path, index=False)
    print(f"\nOutput saved: {output_path}")


if __name__ == "__main__":
    process()
