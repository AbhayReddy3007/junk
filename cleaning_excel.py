"""
Excel Processing Script
-----------------------
1. Cleans the trial_id column by removing parenthetical suffixes like (ABCDEF).
2. Adds a 'TA - I' column combining therapy_area and ot_disease_name.
3. Deduplicates on TA - I by keeping only the highest-phase row(s).
4. Deduplicates on (TA - I, trial_id).
5. Fetches trial_id, primary_region, secondary_countries, size, drug_arm_size_n, dosage from BigQuery
   and left-joins them onto the processed Excel data on trial_id.
6. For rows where primary_region, size, drug_arm_size_n, or dosage are still missing:
   a. ClinicalTrials.gov REST API (v2) for each NCT* trial ID.
   b. Gemini with Google Search grounding for anything still missing.
7. Drops rows where size is still empty after all fallbacks.
8. Within each (TA - I, phase) group, retains only the row(s) with the
   highest-priority primary_region per the hierarchy:
       Tier 1 (highest): United States / US / UK / Europe / EU and full EU country names
       Tier 2          : Canada, Switzerland, Australia, Japan
       Tier 3 (lowest) : any other region / country
9. Within each (TA - I, phase, primary_region) group, retains only the row
   with the highest size value.

IMPORTANT — definition of 'size':
    size = number of patients in the drug/treatment arm(s) only.
    This EXCLUDES placebo, healthy volunteers, and control-only arms.
    It is the same concept as drug_arm_size_n.
    If drug-arm-only count cannot be determined, falls back to total enrollment.

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
    # Use pd.isna() directly — catches np.nan, pd.NA (NAType from nullable
    # Int64/string dtypes returned by BigQuery), and pd.NaT.
    # Wrap in try/except because pd.isna() raises ValueError for lists/arrays.
    try:
        if pd.isna(val):
            return True
    except (ValueError, TypeError):
        pass
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
# Region priority ranking  (Step 8)
# ---------------------------------------------------------------------------

# Full EU member-state names that should be treated as Tier 1 "EU" entries.
_EU_COUNTRY_NAMES = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
    "czechia", "denmark", "estonia", "finland", "france", "germany", "greece",
    "hungary", "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta",
    "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia",
    "spain", "sweden",
}

# Tier 2 full-name variants (lower-cased for comparison).
_TIER2_NAMES = {
    "canada", "switzerland", "australia", "japan",
}


def region_priority(region_val) -> int:
    """
    Return a priority tier for a primary_region value.

    Tier 1 (highest, returned as 1):
        - United States / US / USA / U.S. / U.S.A.
        - United Kingdom / UK / U.K. / Great Britain / GB
        - Europe / EU / European Union / E.U.
        - Any full EU member-state country name (see _EU_COUNTRY_NAMES)

    Tier 2 (returned as 2):
        - Canada, Switzerland, Australia, Japan

    Tier 3 (lowest, returned as 3):
        - Anything else (including None / missing)

    Lower integer = higher priority (so we can use min() or sort ascending).
    """
    if is_missing(region_val):
        return 3

    text = str(region_val).strip().lower()

    # ---- Tier 1 checks ----
    # United States variants
    if re.search(r"\b(us|usa|united states|u\.s\.a?\.?)\b", text):
        return 1
    # United Kingdom variants
    if re.search(r"\b(uk|u\.k\.|united kingdom|great britain|gb)\b", text):
        return 1
    # Europe / EU variants
    if re.search(r"\b(europe|eu|european union|e\.u\.)\b", text):
        return 1
    # Full EU member-state names
    if text in _EU_COUNTRY_NAMES:
        return 1

    # ---- Tier 2 checks ----
    if text in _TIER2_NAMES:
        return 2
    # Also catch abbreviated / partial forms for Tier 2 countries
    if re.search(r"\b(canada|switzerland|australia|japan)\b", text):
        return 2

    # ---- Tier 3: everything else ----
    return 3


# ---------------------------------------------------------------------------
# BigQuery fetch
# ---------------------------------------------------------------------------

def fetch_bq_data(project_id, dataset_id, table):
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT trial_id, primary_region, secondary_countries, size, drug_arm_size_n, dosage
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

# Keywords that identify non-drug arms to exclude from size calculation
_CONTROL_ARM_KEYWORDS = (
    "placebo", "control", "sham", "no treatment", "observation",
    "vehicle", "standard of care", "watchful waiting", "best supportive",
    "healthy", "normal volunteer",
)


def _infer_region(countries):
    if not countries:
        return None
    region_counts = {}
    for c in countries:
        region = _COUNTRY_TO_REGION.get(c, "Other")
        region_counts[region] = region_counts.get(region, 0) + 1
    if len(countries) == 1:
        return _COUNTRY_TO_REGION.get(countries[0], countries[0])
    if all(c == "United States" for c in countries):
        return "United States"
    regions = set(region_counts.keys())
    if len(regions) == 1:
        return regions.pop()
    return "Global"


def _is_drug_arm(arm_type: str, arm_label: str) -> bool:
    """
    Return True if this arm counts as a drug/treatment arm for size purposes.
    Excludes placebo, control-only, healthy volunteer, and observation arms.
    """
    label_lower = arm_label.lower()
    if any(kw in label_lower for kw in _CONTROL_ARM_KEYWORDS):
        return False
    # CT.gov arm types: EXPERIMENTAL, ACTIVE_COMPARATOR, PLACEBO_COMPARATOR,
    # NO_INTERVENTION, SHAM_COMPARATOR, OTHER
    return arm_type.upper() in ("EXPERIMENTAL", "ACTIVE_COMPARATOR")


def _extract_drug_arm_size(study) -> int | None:
    """
    Extract the number of patients in drug/treatment arms only.
    This is what 'size' means: drug arm population, not total enrollment.

    Tries sources in priority order:
      1. armsInterventionsModule.armGroups[].count  (direct per-arm count)
      2. resultsSection.participantFlowModule        (completed trials with posted results)
      3. Total enrollment if the trial has exactly one arm (single-arm — all participants
         are in the drug arm)
      4. FALLBACK: Total enrollment (enrollmentInfo.count) as best-effort approximation
         when drug-arm count cannot be determined any other way. This is logged clearly.
    """
    protocol = study.get("protocolSection", {})
    arms = protocol.get("armsInterventionsModule", {}).get("armGroups", [])

    # Source 1: per-arm count field (sometimes populated for ongoing trials)
    drug_arm_total = None
    has_any_drug_arm = False
    for arm in arms:
        if _is_drug_arm(arm.get("type", ""), arm.get("label", "")):
            has_any_drug_arm = True
            count = arm.get("count")
            if count is not None:
                try:
                    drug_arm_total = (drug_arm_total or 0) + int(count)
                except (ValueError, TypeError):
                    pass

    if drug_arm_total is not None:
        return drug_arm_total

    # Source 2: participantFlowModule (completed trials that posted results)
    flow = study.get("resultsSection", {}).get("participantFlowModule", {})
    groups = flow.get("groups", [])
    periods = flow.get("periods", [])

    drug_group_ids = {
        g["id"] for g in groups
        if g.get("id") and not any(kw in g.get("title", "").lower() for kw in _CONTROL_ARM_KEYWORDS)
    }

    if drug_group_ids and periods:
        total = 0
        found = False
        for period in periods[:1]:  # first period = enrolled/started
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

    # Get total enrollment for sources 3 and 4
    enroll_count = (
        protocol.get("designModule", {})
                .get("enrollmentInfo", {})
                .get("count")
    )

    # Source 3: single-arm trial — total enrollment == drug arm size
    n_arms = len(arms)
    if n_arms <= 1:
        if enroll_count is not None:
            try:
                return int(enroll_count)
            except (ValueError, TypeError):
                pass

    # Source 4: FALLBACK — use total enrollment as best-effort approximation.
    # This is intentionally broad: for multi-arm trials where per-arm counts are
    # unavailable, total enrollment is the closest available proxy. Log it clearly.
    if enroll_count is not None:
        try:
            val = int(enroll_count)
            nct_id = protocol.get("identificationModule", {}).get("nctId", "?")
            print(f"      [size fallback] {nct_id}: using total enrollment ({val}) — "
                  f"per-arm counts unavailable (arms={n_arms}, drug_arms={has_any_drug_arm})")
            return val
        except (ValueError, TypeError):
            pass

    return None


def _fetch_one_nct(nct_id, retries=4, delay=2.0):
    """
    Fetch a single NCT study from ClinicalTrials.gov v2.
    Returns dict with primary_region, size, drug_arm_size_n — or None on failure.
    size and drug_arm_size_n are both set to the drug-arm-only patient count
    (or best-effort total enrollment if arm-level data is unavailable).
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

    # Verify NCT ID matches
    returned_nct = protocol.get("identificationModule", {}).get("nctId", "")
    if returned_nct.upper() != nct_id.upper():
        print(f"    CT.gov ID mismatch for {nct_id} (got {returned_nct}), skipping.")
        return None

    # Drug-arm patient count (= size = drug_arm_size_n), with fallback to total enrollment
    drug_arm_size = _extract_drug_arm_size(study)

    # Primary region from site locations
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})
    primary_region = _infer_region(countries)

    return {
        "primary_region": primary_region,
        # Both columns represent drug-arm patient count (or best-effort total enrollment)
        "size": drug_arm_size,
        "drug_arm_size_n": drug_arm_size,
    }


def clinicaltrials_lookup(trial_ids, rate_limit_delay=0.5):
    """
    Look up ALL provided trial IDs that match the NCT pattern.
    Returns a dict keyed by trial_id (uppercased) with the fetched fields.
    """
    nct_ids = [t for t in trial_ids if re.match(r"^NCT\d+", str(t).strip(), re.IGNORECASE)]
    results = {}
    if not nct_ids:
        return results

    print(f"  Querying ClinicalTrials.gov for {len(nct_ids)} NCT ID(s) ...")
    for i, nct_id in enumerate(nct_ids, 1):
        nct_id_clean = str(nct_id).strip().upper()
        print(f"    [{i}/{len(nct_ids)}] {nct_id_clean} ...", end=" ", flush=True)
        result = _fetch_one_nct(nct_id_clean)
        if result:
            results[nct_id_clean] = result
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

- primary_region: The primary geographic region of the trial sites (e.g. "United States", "Europe", "Asia-Pacific", "Global").

- size: The number of patients enrolled in the DRUG or TREATMENT arm(s) only.
  EXCLUDE placebo recipients, healthy volunteers, and control-only arms.
  If the trial is single-arm, all enrolled patients count.
  If per-arm counts are not available, use total enrollment as a best-effort value.
  Do NOT leave this null if any enrollment figure is available.

- drug_arm_size_n: Same value as size (drug/treatment arm patients only, or total enrollment if arm-level unavailable).

- dosage: The dose and regimen of the investigational drug arm (e.g. "10 mg once daily", "200 mg BID",
  "100 mg/m² IV q3w"). Include the numeric dose, unit, and frequency/route where available.
  If multiple drug arms exist, list each separated by " | ".
  Use null only if genuinely not findable.

Return ONLY a valid JSON array, no explanation, no markdown fences:
[
  {{"trial_id": "NCT12345678", "primary_region": "United States", "size": 250, "drug_arm_size_n": 250, "dosage": "10 mg once daily"}},
  {{"trial_id": "NCT87654321", "primary_region": "Europe", "size": 200, "drug_arm_size_n": 200, "dosage": "200 mg BID"}}
]

Use null only if the value genuinely cannot be found after searching. Do not guess.
"""


def _gemini_lookup_batch(trial_ids, api_key):
    # Primary model; fall back to gemini-3.1-flash-lite if this fails.
    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

    for model_name in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent"
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
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            break  # success — stop trying models
        except urllib.error.HTTPError as e:
            print(f"  WARNING: Gemini model {model_name} returned HTTP {e.code}")
            if model_name == models[-1]:
                print(f"  WARNING: All Gemini models failed.")
                return []
            print(f"  Retrying with next model ...")
            continue
        except Exception as e:
            print(f"  WARNING: Gemini model {model_name} error: {e}")
            if model_name == models[-1]:
                return []
            continue
    else:
        # for-loop completed without break — all models failed
        return []

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
                tid = str(entry.get("trial_id", "")).strip().upper()
                if tid:
                    results[tid] = entry
        except Exception as e:
            print(f"  WARNING: Gemini call failed for batch {i}: {e}")
        if i < len(batches):
            time.sleep(2)
    return results


# ---------------------------------------------------------------------------
# Combined fallback
# ---------------------------------------------------------------------------

def fill_missing_fields(df, api_key, batch_size):
    """
    For EVERY row in the dataframe, fills primary_region, size, drug_arm_size_n,
    and dosage wherever missing. Operates on all rows, not just a pre-filtered subset.
    size and drug_arm_size_n both represent the drug-arm patient count (or total
    enrollment as a best-effort fallback when arm-level data is unavailable).
    dosage is the dose/regimen of the investigational drug arm(s).
    """
    target_cols = ["primary_region", "size", "drug_arm_size_n", "dosage"]

    # Ensure clean 0..N-1 integer index for safe df.at[idx, col] access
    df = df.reset_index(drop=True)

    for col in target_cols:
        if col not in df.columns:
            df[col] = None

    # Normalize numeric/string columns to object dtype so assignments from
    # CT.gov/Gemini don't get silently coerced to NaN by a typed column.
    for col in ["size", "drug_arm_size_n", "dosage"]:
        if col in df.columns:
            df[col] = df[col].astype(object)

    # Also normalize primary_region to object
    if "primary_region" in df.columns:
        df["primary_region"] = df["primary_region"].astype(object)

    # Normalize trial_id to uppercase in the dataframe so lookups match consistently.
    df["_trial_id_upper"] = df["trial_id"].astype(str).str.strip().str.upper()

    def _needs_fill(row):
        return any(is_missing(row.get(col)) for col in target_cols)

    print(f"\nStep 6 — Missing field summary (before fallback):")
    print(f"  Total rows : {len(df)}")
    for col in target_cols:
        print(f"  Missing {col:25s}: {df[col].apply(is_missing).sum()} row(s)")

    # Collect ALL unique trial IDs that have at least one missing field.
    # Use the uppercased key for consistent dict lookups.
    missing_per_trial = {}
    for _, row in df.iterrows():
        if not _needs_fill(row):
            continue
        tid = row["_trial_id_upper"]
        if not tid or tid in ("", "NAN", "NONE"):
            continue
        if tid not in missing_per_trial:
            missing_per_trial[tid] = set()
        for col in target_cols:
            if is_missing(row.get(col)):
                missing_per_trial[tid].add(col)

    unique_trials_needing_fill = list(missing_per_trial.keys())
    total_missing_rows = df.apply(_needs_fill, axis=1).sum()
    print(f"\n  {total_missing_rows} row(s) across "
          f"{len(unique_trials_needing_fill)} unique trial ID(s) need fallback.")
    print("  Fields missing per trial:")
    for tid, cols in sorted(missing_per_trial.items()):
        print(f"    {tid}: {sorted(cols)}")

    if not unique_trials_needing_fill:
        print("Step 6: No rows with missing fields. Skipping fallback.")
        df = df.drop(columns=["_trial_id_upper"])
        return df

    # ---- 6a: ClinicalTrials.gov — query ALL NCT IDs that need any field ----
    ctgov_results = clinicaltrials_lookup(unique_trials_needing_fill)

    # Apply CT.gov results to ALL rows for each matched trial_id
    filled_ctgov = 0
    fill_detail = {}
    for idx in df.index:
        tid = df.at[idx, "_trial_id_upper"]
        entry = ctgov_results.get(tid)
        if not entry:
            continue
        for col in target_cols:
            val = entry.get(col)
            if is_missing(df.at[idx, col]) and val is not None:
                df.at[idx, col] = val
                filled_ctgov += 1
                fill_detail.setdefault(col, 0)
                fill_detail[col] += 1
    print(f"  CT.gov filled {filled_ctgov} cell(s): {fill_detail}")

    # Verify CT.gov fill actually stuck
    print(f"  Verification after CT.gov fill:")
    for col in target_cols:
        still_missing = df[col].apply(is_missing).sum()
        print(f"    Missing {col:25s}: {still_missing} row(s)")

    # ---- 6b: Gemini for anything still missing ----
    # Recompute which trial IDs still have missing fields after CT.gov pass
    still_missing_per_trial = {}
    for _, row in df.iterrows():
        if not _needs_fill(row):
            continue
        tid = row["_trial_id_upper"]
        if not tid or tid in ("", "NAN", "NONE"):
            continue
        if tid not in still_missing_per_trial:
            still_missing_per_trial[tid] = set()
        for col in target_cols:
            if is_missing(row.get(col)):
                still_missing_per_trial[tid].add(col)

    still_missing_trials = list(still_missing_per_trial.keys())

    if still_missing_trials:
        print(f"  {len(still_missing_trials)} trial(s) still missing fields → Gemini ...")
        for tid, cols in still_missing_per_trial.items():
            print(f"    {tid}: missing {sorted(cols)}")

        gemini_results = gemini_fallback(still_missing_trials, api_key, batch_size)

        # Apply Gemini results to ALL rows for each matched trial_id
        filled_gemini = 0
        fill_detail_g = {}
        for idx in df.index:
            tid = df.at[idx, "_trial_id_upper"]
            entry = gemini_results.get(tid)
            if not entry:
                continue
            for col in target_cols:
                val = entry.get(col)
                if is_missing(df.at[idx, col]) and val is not None:
                    df.at[idx, col] = val
                    filled_gemini += 1
                    fill_detail_g.setdefault(col, 0)
                    fill_detail_g[col] += 1
        print(f"  Gemini filled {filled_gemini} cell(s): {fill_detail_g}")
    else:
        print("  All fields resolved by CT.gov. Gemini not needed.")

    # Drop temp column before final checks and return
    df = df.drop(columns=["_trial_id_upper"])

    # ---- Final summary ----
    print(f"\nStep 6 — Missing field summary (after fallback):")
    print(f"  Total rows : {len(df)}")
    for col in target_cols:
        print(f"  Still missing {col:20s}: {df[col].apply(is_missing).sum()} row(s)")

    # Report any trial IDs that remain unresolved
    still_any_mask = df.apply(_needs_fill, axis=1)
    remaining = (
        df.loc[still_any_mask, ["trial_id"] + target_cols]
        .drop_duplicates("trial_id")
    )
    if not remaining.empty:
        print("  Unresolved trial IDs (still have missing fields):")
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

        bq_cols = ["trial_id", "primary_region", "secondary_countries", "size", "drug_arm_size_n", "dosage"]

        # Deduplicate BQ rows per trial_id — prefer rows with the most non-null values
        # to avoid merge-induced NaN from duplicate BQ entries
        bq_df = bq_df[bq_cols].copy()
        bq_df["_non_null_count"] = bq_df[["primary_region", "secondary_countries", "size", "drug_arm_size_n", "dosage"]].notna().sum(axis=1)
        bq_df = (
            bq_df.sort_values("_non_null_count", ascending=False)
                 .drop_duplicates(subset=["trial_id"], keep="first")
                 .drop(columns=["_non_null_count"])
        )

        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            df = df.drop(columns=existing)

        df = df.merge(bq_df, on="trial_id", how="left")

        # Reset index after merge to ensure clean 0..N-1 integer index.
        # This prevents stale-index issues from prior filter/dedup steps.
        df = df.reset_index(drop=True)

        bq_matched = df["secondary_countries"].notna()
        print("Step 5 done: BQ columns joined.")
        print(f"  Total rows        : {len(df)}")
        print(f"  Matched in BQ     : {bq_matched.sum()}")
        print(f"  Not matched in BQ : {(~bq_matched).sum()}")
        for col in ["primary_region", "size", "drug_arm_size_n", "dosage"]:
            n_missing = df[col].apply(is_missing).sum()
            print(f"  Missing {col:25s}: {n_missing}")

        # Diagnostic: show which trial_ids have missing fields after BQ join
        print("  Detailed missing fields per trial_id after BQ join:")
        for col in ["primary_region", "size", "drug_arm_size_n", "dosage"]:
            missing_tids = df.loc[df[col].apply(is_missing), "trial_id"].unique()
            if len(missing_tids) > 0:
                print(f"    {col}: {len(missing_tids)} unique trial(s) — {list(missing_tids[:10])}{'...' if len(missing_tids) > 10 else ''}")

    # 6. Fill all missing fields — processes EVERY row in the dataframe
    if "trial_id" in df.columns:
        df = fill_missing_fields(df, gemini_api_key, batch_size)

    # -----------------------------------------------------------------------
    # 7. Drop rows where size is still empty after all fallbacks
    # -----------------------------------------------------------------------
    if "size" in df.columns:
        before = len(df)
        df = df[~df["size"].apply(is_missing)].reset_index(drop=True)
        dropped = before - len(df)
        print(f"\nStep 7 done: {dropped} row(s) dropped because size is still empty. "
              f"Remaining rows: {len(df)}")
    else:
        print("\nStep 7: 'size' column not found — skipping row drop.")

    # -----------------------------------------------------------------------
    # 8. Within each (TA - I, phase) group, keep only the row(s) with the
    #    highest-priority primary_region.
    #
    #    Hierarchy (lower number = higher priority):
    #      Tier 1: United States / US / UK / Europe / EU / any EU member state
    #      Tier 2: Canada, Switzerland, Australia, Japan
    #      Tier 3: anything else
    #
    #    If ALL rows in a group are Tier 3, all are kept (no drop).
    # -----------------------------------------------------------------------
    required_cols_8 = {"TA - I", "phase", "primary_region"}
    if required_cols_8.issubset(df.columns):
        before = len(df)

        # Compute per-row priority (1 = best, 3 = lowest)
        df["_region_priority"] = df["primary_region"].apply(region_priority)

        # Best (minimum) priority tier within each (TA - I, phase) group
        df["_best_region_priority"] = df.groupby(
            ["TA - I", "phase"], sort=False
        )["_region_priority"].transform("min")

        # Keep only rows that match the best tier for their group
        df = df[df["_region_priority"] == df["_best_region_priority"]].reset_index(drop=True)

        df = df.drop(columns=["_region_priority", "_best_region_priority"])
        print(f"\nStep 8 done: {before - len(df)} row(s) removed by region-priority filter. "
              f"Remaining rows: {len(df)}")
        print("  Region hierarchy applied: "
              "Tier 1 (US/UK/EU) > Tier 2 (Canada/Switzerland/Australia/Japan) > Tier 3 (other)")
    else:
        missing = required_cols_8 - set(df.columns)
        print(f"\nStep 8 skipped: missing column(s) {missing}.")

    # -----------------------------------------------------------------------
    # 9. Within each (TA - I, phase, primary_region) group, keep the single
    #    row with the highest size value.
    #    If multiple rows share the exact same maximum size, keep the first one
    #    (preserving original row order).
    # -----------------------------------------------------------------------
    required_cols_9 = {"TA - I", "phase", "primary_region", "size"}
    if required_cols_9.issubset(df.columns):
        before = len(df)

        # Coerce size to numeric for a reliable max comparison.
        # Non-numeric / missing values become NaN and are treated as 0 so they
        # lose against any real number (Step 7 already removed truly-empty rows,
        # but this guards against any residual edge cases).
        df["_size_numeric"] = pd.to_numeric(df["size"], errors="coerce").fillna(0)

        df["_max_size"] = df.groupby(
            ["TA - I", "phase", "primary_region"], sort=False
        )["_size_numeric"].transform("max")

        # Keep only the row(s) that have the maximum size for their group
        df = df[df["_size_numeric"] == df["_max_size"]]

        # Among ties (same max size), keep only the first occurrence
        df = df.drop_duplicates(subset=["TA - I", "phase", "primary_region"], keep="first")

        df = df.drop(columns=["_size_numeric", "_max_size"]).reset_index(drop=True)
        print(f"\nStep 9 done: {before - len(df)} row(s) removed by max-size filter. "
              f"Remaining rows: {len(df)}")
    else:
        missing = required_cols_9 - set(df.columns)
        print(f"\nStep 9 skipped: missing column(s) {missing}.")

    # -----------------------------------------------------------------------
    # Clean up pd.NA values (from BQ nullable dtypes) before saving.
    # openpyxl handles np.nan/None correctly but pd.NA can cause issues.
    # -----------------------------------------------------------------------
    for col in df.columns:
        df[col] = df[col].where(df[col].notna(), other=None)

    df.to_excel(output_path, index=False)
    print(f"\nOutput saved: {output_path}")


if __name__ == "__main__":
    process()
