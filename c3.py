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
7. Sets size = 0 for rows where size is still empty after all fallbacks (rows are retained).
8. Within each (TA - I, phase) group, retains only the row(s) with the
   highest-priority primary_region per the hierarchy:
       Tier 1 (highest): United States / US / UK / Europe / EU and full EU country names
       Tier 2          : Canada, Switzerland, Australia, Japan
       Tier 3 (lowest) : any other region / country
9. Within each (TA - I, phase, primary_region) group, retains only the row
   with the highest size value.
10. Adds a 'TA-I Comparison' sheet showing which TA-Is were retained or removed,
    the step that caused removal, and a plain-English explanation of why.

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
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_missing(val) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (ValueError, TypeError):
        pass
    if isinstance(val, str) and val.strip() in ("", "nan", "None"):
        return True
    return False


# ---------------------------------------------------------------------------
# Removal tracker
# ---------------------------------------------------------------------------

class RemovalTracker:
    """
    Tracks which TA-Is disappear at each processing step and why.

    Usage:
        tracker = RemovalTracker(input_tai_set)
        tracker.snapshot(df, step_number, step_name, detail_fn)

    detail_fn(tai, rows_before_df) -> str  — optional callable that receives
    the TA-I name and the pre-step slice of the dataframe and returns a
    human-readable explanation string.  Pass None to use a generic message.
    """

    def __init__(self, initial_tai_set: set):
        self._active: set = set(initial_tai_set)          # TA-Is still alive
        self.removals: dict = {}                           # tai -> removal record

    def snapshot(self, df: pd.DataFrame, step_num: int, step_label: str,
                 detail_fn=None, pre_step_df: pd.DataFrame = None):
        """
        Compare current df against _active.  Any TA-I that has disappeared
        since the last snapshot is recorded with step_num, step_label, and
        the output of detail_fn if provided.
        """
        if "TA - I" not in df.columns:
            return
        current = set(df["TA - I"].dropna().unique())
        gone = self._active - current

        for tai in gone:
            detail = ""
            if detail_fn is not None and pre_step_df is not None:
                try:
                    detail = detail_fn(tai, pre_step_df)
                except Exception:
                    detail = ""
            self.removals[tai] = {
                "step_num":   step_num,
                "step_label": step_label,
                "detail":     detail,
            }

        self._active = current

    def record_manual(self, tai: str, step_num: int, step_label: str, detail: str):
        """Directly record a removal for a TA-I (used when TA-I column not yet built)."""
        if tai not in self.removals:
            self.removals[tai] = {
                "step_num":   step_num,
                "step_label": step_label,
                "detail":     detail,
            }
            self._active.discard(tai)


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


def phase_rank_label(rank: int) -> str:
    return {4: "IV / Approved", 3: "III", 2: "II", 1: "I", -1: "Unknown"}.get(rank, str(rank))


# ---------------------------------------------------------------------------
# Region priority ranking  (Step 8)
# ---------------------------------------------------------------------------

_EU_COUNTRY_NAMES = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
    "czechia", "denmark", "estonia", "finland", "france", "germany", "greece",
    "hungary", "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta",
    "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia",
    "spain", "sweden",
}

_TIER2_NAMES = {"canada", "switzerland", "australia", "japan"}


def region_priority(region_val) -> int:
    if is_missing(region_val):
        return 3
    text = str(region_val).strip().lower()
    if re.search(r"\b(us|usa|united states|u\.s\.a?\.?)\b", text):
        return 1
    if re.search(r"\b(uk|u\.k\.|united kingdom|great britain|gb)\b", text):
        return 1
    if re.search(r"\b(europe|eu|european union|e\.u\.)\b", text):
        return 1
    if text in _EU_COUNTRY_NAMES:
        return 1
    if text in _TIER2_NAMES:
        return 2
    if re.search(r"\b(canada|switzerland|australia|japan)\b", text):
        return 2
    return 3


def region_tier_label(priority: int) -> str:
    return {1: "Tier 1 (US/UK/EU)", 2: "Tier 2 (Canada/Switzerland/Australia/Japan)",
            3: "Tier 3 (Other)"}.get(priority, "Unknown")


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
    label_lower = arm_label.lower()
    if any(kw in label_lower for kw in _CONTROL_ARM_KEYWORDS):
        return False
    return arm_type.upper() in ("EXPERIMENTAL", "ACTIVE_COMPARATOR")


def _extract_drug_arm_size(study) -> int | None:
    protocol = study.get("protocolSection", {})
    arms = protocol.get("armsInterventionsModule", {}).get("armGroups", [])

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
        for period in periods[:1]:
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

    enroll_count = (
        protocol.get("designModule", {})
                .get("enrollmentInfo", {})
                .get("count")
    )

    n_arms = len(arms)
    if n_arms <= 1:
        if enroll_count is not None:
            try:
                return int(enroll_count)
            except (ValueError, TypeError):
                pass

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

    returned_nct = protocol.get("identificationModule", {}).get("nctId", "")
    if returned_nct.upper() != nct_id.upper():
        print(f"    CT.gov ID mismatch for {nct_id} (got {returned_nct}), skipping.")
        return None

    drug_arm_size = _extract_drug_arm_size(study)
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})
    primary_region = _infer_region(countries)

    return {
        "primary_region": primary_region,
        "size": drug_arm_size,
        "drug_arm_size_n": drug_arm_size,
    }


def clinicaltrials_lookup(trial_ids, rate_limit_delay=0.5):
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
    models = ["gemini-2.5-flash", "gemini-3.1-flash-lite"]

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
            break
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
# Combined fallback  (returns enriched df + per-trial lookup audit)
# ---------------------------------------------------------------------------

def fill_missing_fields(df, api_key, batch_size):
    """
    Returns (df, lookup_audit) where lookup_audit is a dict:
        trial_id_upper -> {
            "in_bq": bool,
            "ctgov_found": bool,
            "gemini_found": bool,
            "size_resolved": bool,
        }
    """
    target_cols = ["primary_region", "size", "drug_arm_size_n", "dosage"]
    df = df.reset_index(drop=True)

    for col in target_cols:
        if col not in df.columns:
            df[col] = None

    for col in ["size", "drug_arm_size_n", "dosage"]:
        if col in df.columns:
            df[col] = df[col].astype(object)

    if "primary_region" in df.columns:
        df["primary_region"] = df["primary_region"].astype(object)

    df["_trial_id_upper"] = df["trial_id"].astype(str).str.strip().str.upper()

    def _needs_fill(row):
        return any(is_missing(row.get(col)) for col in target_cols)

    print(f"\nStep 6 — Missing field summary (before fallback):")
    print(f"  Total rows : {len(df)}")
    for col in target_cols:
        print(f"  Missing {col:25s}: {df[col].apply(is_missing).sum()} row(s)")

    # Build per-trial audit: start with BQ hit status
    lookup_audit = {}
    for _, row in df.iterrows():
        tid = row["_trial_id_upper"]
        if not tid or tid in ("", "NAN", "NONE"):
            continue
        if tid not in lookup_audit:
            # "in_bq" = had at least one non-missing value from BQ join
            # We approximate: if size is not missing after BQ, BQ supplied it
            lookup_audit[tid] = {
                "in_bq":         not is_missing(row.get("size")),
                "ctgov_found":   False,
                "gemini_found":  False,
                "size_resolved": not is_missing(row.get("size")),
            }

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
        return df, lookup_audit

    # ---- 6a: ClinicalTrials.gov ----
    ctgov_results = clinicaltrials_lookup(unique_trials_needing_fill)

    filled_ctgov = 0
    fill_detail = {}
    for idx in df.index:
        tid = df.at[idx, "_trial_id_upper"]
        entry = ctgov_results.get(tid)
        if not entry:
            continue
        if tid in lookup_audit:
            lookup_audit[tid]["ctgov_found"] = True
        for col in target_cols:
            val = entry.get(col)
            if is_missing(df.at[idx, col]) and val is not None:
                df.at[idx, col] = val
                filled_ctgov += 1
                fill_detail.setdefault(col, 0)
                fill_detail[col] += 1
    print(f"  CT.gov filled {filled_ctgov} cell(s): {fill_detail}")

    print(f"  Verification after CT.gov fill:")
    for col in target_cols:
        still_missing = df[col].apply(is_missing).sum()
        print(f"    Missing {col:25s}: {still_missing} row(s)")

    # ---- 6b: Gemini ----
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

        filled_gemini = 0
        fill_detail_g = {}
        for idx in df.index:
            tid = df.at[idx, "_trial_id_upper"]
            entry = gemini_results.get(tid)
            if not entry:
                continue
            if tid in lookup_audit:
                lookup_audit[tid]["gemini_found"] = True
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

    df = df.drop(columns=["_trial_id_upper"])

    # Update size_resolved status after all fallbacks
    for _, row in df.iterrows():
        tid = str(row.get("trial_id", "")).strip().upper()
        if tid in lookup_audit:
            lookup_audit[tid]["size_resolved"] = not is_missing(row.get("size"))

    print(f"\nStep 6 — Missing field summary (after fallback):")
    print(f"  Total rows : {len(df)}")
    for col in target_cols:
        print(f"  Still missing {col:20s}: {df[col].apply(is_missing).sum()} row(s)")

    def _needs_fill_row(row):
        return any(is_missing(row.get(col)) for col in target_cols)

    still_any_mask = df.apply(_needs_fill_row, axis=1)
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
    return df, lookup_audit


# ---------------------------------------------------------------------------
# Detail functions for the removal tracker
# ---------------------------------------------------------------------------

def _detail_step7(tai: str, pre_df: pd.DataFrame, lookup_audit: dict) -> str:
    """
    Explains why a TA-I was removed in Step 7 (size still empty).
    Looks at each trial_id for that TA-I and reports what each lookup source returned.
    """
    subset = pre_df[pre_df["TA - I"] == tai]
    trial_ids = subset["trial_id"].dropna().unique().tolist()

    lines = [f"{len(trial_ids)} trial(s) had no resolvable 'size' after all sources:"]
    for tid in trial_ids:
        tid_upper = str(tid).strip().upper()
        audit = lookup_audit.get(tid_upper, {})
        in_bq       = audit.get("in_bq", False)
        ctgov_found = audit.get("ctgov_found", False)
        gemini_found= audit.get("gemini_found", False)

        sources = []
        sources.append(f"BigQuery: {'found' if in_bq else 'not found'}")
        if re.match(r"^NCT\d+", tid_upper, re.IGNORECASE):
            sources.append(f"CT.gov: {'found' if ctgov_found else 'not found / no size returned'}")
        else:
            sources.append("CT.gov: skipped (not an NCT ID)")
        sources.append(f"Gemini: {'found' if gemini_found else 'not found / returned null'}")
        lines.append(f"  • {tid}: {'; '.join(sources)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 10 — TA-I Comparison Sheet
# ---------------------------------------------------------------------------

def add_tai_comparison_sheet(
    output_path: Path,
    input_tai_set: set,
    output_tai_set: set,
    removal_tracker: RemovalTracker,
):
    """
    Adds a 'TA-I Comparison' sheet.

    Columns:
      A  TA-I
      B  In Input File?
      C  In Output File?
      D  Status          (Retained / Removed / New in Output)
      E  Removed at Step
      F  Reason for Removal

    Only removed TA-Is populate columns E and F.
    """
    all_tai = sorted(input_tai_set | output_tai_set)

    rows = []
    for tai in all_tai:
        in_input  = tai in input_tai_set
        in_output = tai in output_tai_set
        if in_input and in_output:
            status, step_label, detail = "Retained", "", ""
        elif in_input and not in_output:
            status = "Removed"
            rec = removal_tracker.removals.get(tai, {})
            step_num   = rec.get("step_num", "?")
            step_lbl   = rec.get("step_label", "Unknown")
            step_label = f"Step {step_num}: {step_lbl}"
            detail     = rec.get("detail", "")
        else:
            status, step_label, detail = "New in Output", "", ""
        rows.append((tai, "Yes" if in_input else "No",
                     "Yes" if in_output else "No",
                     status, step_label, detail))

    n_retained = sum(1 for r in rows if r[3] == "Retained")
    n_removed  = sum(1 for r in rows if r[3] == "Removed")
    n_new      = sum(1 for r in rows if r[3] == "New in Output")

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    FN = "Arial"

    hdr_fill = PatternFill("solid", fgColor="2F4F8F")
    hdr_font = Font(name=FN, bold=True, color="FFFFFF", size=11)

    title_font  = Font(name=FN, bold=True, size=13, color="1F3864")
    label_font  = Font(name=FN, bold=True, size=10)
    value_font  = Font(name=FN, size=10)

    fill_retained = PatternFill("solid", fgColor="C6EFCE")
    fill_removed  = PatternFill("solid", fgColor="FFC7CE")
    fill_new      = PatternFill("solid", fgColor="BDD7EE")
    fill_alt      = PatternFill("solid", fgColor="F2F2F2")

    font_retained = Font(name=FN, size=10, color="276221", bold=True)
    font_removed  = Font(name=FN, size=10, color="9C0006", bold=True)
    font_new      = Font(name=FN, size=10, color="1F4E79", bold=True)
    body_font     = Font(name=FN, size=10)
    step_font     = Font(name=FN, size=10, bold=True, color="7F0000")
    detail_font   = Font(name=FN, size=9,  italic=True, color="404040")

    thin  = Side(style="thin",   color="BFBFBF")
    thick = Side(style="medium", color="2F4F8F")
    thin_border  = Border(left=thin,  right=thin,  top=thin,  bottom=thin)
    thick_top    = Border(left=thin,  right=thin,  top=thick, bottom=thin)

    center = Alignment(horizontal="center", vertical="top", wrap_text=True)
    left   = Alignment(horizontal="left",   vertical="top", wrap_text=True)

    # ------------------------------------------------------------------
    # Workbook
    # ------------------------------------------------------------------
    wb = openpyxl.load_workbook(output_path)
    if "TA-I Comparison" in wb.sheetnames:
        del wb["TA-I Comparison"]
    ws = wb.create_sheet("TA-I Comparison")

    # Title (row 1)
    ws.merge_cells("A1:F1")
    ws["A1"] = "TA-I Comparison: Input vs Output"
    ws["A1"].font      = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws["A1"].fill      = PatternFill("solid", fgColor="D9E1F2")
    ws.row_dimensions[1].height = 28

    # Summary block (rows 2–6)
    summary_rows = [
        ("Input TA-I count",  len(input_tai_set), None),
        ("Output TA-I count", len(output_tai_set), None),
        ("Retained",          n_retained,  (fill_retained, font_retained)),
        ("Removed",           n_removed,   (fill_removed,  font_removed)),
        ("New in Output",     n_new,       (fill_new,      font_new)),
    ]
    for i, (lbl, val, style) in enumerate(summary_rows, start=2):
        ws.cell(row=i, column=1, value=lbl).font = label_font
        ws.cell(row=i, column=1).alignment = Alignment(horizontal="left", vertical="center")
        c = ws.cell(row=i, column=2, value=val)
        c.font      = style[1] if style else value_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        if style:
            c.fill = style[0]
        ws.row_dimensions[i].height = 16

    ws.row_dimensions[7].height = 6  # spacer

    # Table header (row 8)
    TABLE_START = 8
    headers = ["TA-I", "In Input File?", "In Output File?",
               "Status", "Removed at Step", "Reason for Removal"]
    col_widths = [52, 15, 15, 16, 28, 80]
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=TABLE_START, column=col_idx, value=h)
        c.font      = hdr_font
        c.fill      = hdr_fill
        c.alignment = center
        c.border    = thick_top
    ws.row_dimensions[TABLE_START].height = 22

    # Data rows
    status_styles = {
        "Retained":      (fill_retained, font_retained),
        "Removed":       (fill_removed,  font_removed),
        "New in Output": (fill_new,      font_new),
    }

    for r_off, (tai, in_inp, in_out, status, step_lbl, detail) in enumerate(rows, start=1):
        row_num = TABLE_START + r_off
        sfill, sfont = status_styles[status]
        use_alt = (r_off % 2 == 0)

        def _cell(col, value, font=body_font, align=left, fill=None, border=thin_border):
            c = ws.cell(row=row_num, column=col, value=value)
            c.font      = font
            c.alignment = align
            c.border    = border
            if fill:
                c.fill = fill
            elif use_alt and status != "Removed":
                c.fill = fill_alt
            return c

        _cell(1, tai)
        _cell(2, in_inp, align=center)
        _cell(3, in_out, align=center)
        _cell(4, status, font=sfont, fill=sfill, align=center)

        if status == "Removed":
            _cell(5, step_lbl,  font=step_font,   fill=PatternFill("solid", fgColor="FFE4E1"))
            _cell(6, detail,    font=detail_font,  fill=PatternFill("solid", fgColor="FFF5F5"))
        else:
            _cell(5, "—", align=center)
            _cell(6, "—", align=center)

        # Row height: taller for removed rows (detail can be multi-line)
        ws.row_dimensions[row_num].height = 60 if status == "Removed" else 18

    # Column widths
    for col_idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[chr(64 + col_idx)].width = width

    ws.freeze_panes = f"A{TABLE_START + 1}"

    wb.save(output_path)

    print(f"\nStep 10 done: 'TA-I Comparison' sheet added.")
    print(f"  Input TA-Is : {len(input_tai_set)}")
    print(f"  Output TA-Is: {len(output_tai_set)}")
    print(f"  Retained    : {n_retained}")
    print(f"  Removed     : {n_removed}")
    print(f"  New         : {n_new}")
    if n_removed:
        print("  Removed TA-Is:")
        for r in rows:
            if r[3] == "Removed":
                print(f"    - {r[0]}  [{r[4]}]")


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

    # -----------------------------------------------------------------------
    # Capture input TA-I set BEFORE any processing
    # -----------------------------------------------------------------------
    input_tai_set: set = set()
    if "therapy_area" in df.columns and "ot_disease_name" in df.columns:
        input_tai_set = set(
            (df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str))
            .dropna().unique()
        )
    elif "TA - I" in df.columns:
        input_tai_set = set(df["TA - I"].dropna().unique())

    tracker = RemovalTracker(input_tai_set)

    # -----------------------------------------------------------------------
    # Step 1: Clean trial_id
    # -----------------------------------------------------------------------
    if "trial_id" not in df.columns:
        print("WARNING: 'trial_id' not found. Skipping step 1.")
    else:
        df["trial_id"] = (
            df["trial_id"].astype(str)
            .str.replace(r"\s*\(.*?\)\s*$", "", regex=True)
            .str.strip()
        )
        print("Step 1 done: trial_id cleaned.")

    # -----------------------------------------------------------------------
    # Step 2: Add TA - I
    # -----------------------------------------------------------------------
    missing_cols = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing_cols:
        print(f"WARNING: {missing_cols} not found. Skipping steps 2-4.")
    else:
        df["TA - I"] = df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        print("Step 2 done: 'TA - I' column added.")

        # -----------------------------------------------------------------------
        # Step 3: Deduplicate by highest phase
        # -----------------------------------------------------------------------
        if "phase" not in df.columns:
            print("WARNING: 'phase' not found. Skipping step 3.")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)
            df["_max_rank"]   = df.groupby("TA - I")["_phase_rank"].transform("max")
            before = len(df)
            pre_step3 = df.copy()
            df = df[df["_phase_rank"] == df["_max_rank"]].sort_index()
            df = df.drop(columns=["_phase_rank", "_max_rank"])
            print(f"Step 3 done: {before - len(df)} lower-phase row(s) removed.")
            # Step 3 cannot fully remove a TA-I (all ranks equal → all kept), but
            # snapshot anyway for safety
            tracker.snapshot(df, 3, "Phase deduplication", pre_step_df=pre_step3)

        # -----------------------------------------------------------------------
        # Step 4: Deduplicate (TA - I, trial_id)
        # -----------------------------------------------------------------------
        if "trial_id" in df.columns:
            before = len(df)
            pre_step4 = df.copy()
            df = df.drop_duplicates(subset=["TA - I", "trial_id"], keep="first").sort_index()
            print(f"Step 4 done: {before - len(df)} duplicate (TA-I, trial_id) row(s) removed.")
            tracker.snapshot(df, 4, "Deduplication on (TA-I, trial_id)", pre_step_df=pre_step4)

    # -----------------------------------------------------------------------
    # Step 5: BQ join
    # -----------------------------------------------------------------------
    lookup_audit = {}   # populated by fill_missing_fields

    if "trial_id" not in df.columns:
        print("WARNING: 'trial_id' not found. Skipping BQ join.")
    else:
        bq_df = fetch_bq_data(project_id, dataset_id, bq_table)
        bq_df["trial_id"] = bq_df["trial_id"].astype(str).str.strip()

        bq_cols = ["trial_id", "primary_region", "secondary_countries",
                   "size", "drug_arm_size_n", "dosage"]

        bq_df = bq_df[bq_cols].copy()
        bq_df["_non_null_count"] = bq_df[
            ["primary_region", "secondary_countries", "size", "drug_arm_size_n", "dosage"]
        ].notna().sum(axis=1)
        bq_df = (
            bq_df.sort_values("_non_null_count", ascending=False)
                 .drop_duplicates(subset=["trial_id"], keep="first")
                 .drop(columns=["_non_null_count"])
        )

        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            df = df.drop(columns=existing)

        df = df.merge(bq_df, on="trial_id", how="left")
        df = df.reset_index(drop=True)

        bq_matched = df["secondary_countries"].notna()
        print("Step 5 done: BQ columns joined.")
        print(f"  Total rows        : {len(df)}")
        print(f"  Matched in BQ     : {bq_matched.sum()}")
        print(f"  Not matched in BQ : {(~bq_matched).sum()}")
        for col in ["primary_region", "size", "drug_arm_size_n", "dosage"]:
            n_missing = df[col].apply(is_missing).sum()
            print(f"  Missing {col:25s}: {n_missing}")

        print("  Detailed missing fields per trial_id after BQ join:")
        for col in ["primary_region", "size", "drug_arm_size_n", "dosage"]:
            missing_tids = df.loc[df[col].apply(is_missing), "trial_id"].unique()
            if len(missing_tids) > 0:
                print(f"    {col}: {len(missing_tids)} unique trial(s) — "
                      f"{list(missing_tids[:10])}{'...' if len(missing_tids) > 10 else ''}")

    # -----------------------------------------------------------------------
    # Step 6: Fill missing fields
    # -----------------------------------------------------------------------
    if "trial_id" in df.columns:
        df, lookup_audit = fill_missing_fields(df, gemini_api_key, batch_size)

    # -----------------------------------------------------------------------
    # Step 7: Set size = 0 where size is still empty (retain rows)
    # -----------------------------------------------------------------------
    if "size" in df.columns:
        empty_size_mask = df["size"].apply(is_missing)
        filled = empty_size_mask.sum()
        df.loc[empty_size_mask, "size"] = 0
        print(f"\nStep 7 done: {filled} row(s) had empty size — set to 0 (rows retained). "
              f"Remaining rows: {len(df)}")
    else:
        print("\nStep 7: 'size' column not found — skipping.")

    # -----------------------------------------------------------------------
    # Step 8: Region-priority filter
    # -----------------------------------------------------------------------
    required_cols_8 = {"TA - I", "phase", "primary_region"}
    if required_cols_8.issubset(df.columns):
        before = len(df)
        pre_step8 = df.copy()

        df["_region_priority"] = df["primary_region"].apply(region_priority)
        df["_best_region_priority"] = df.groupby(
            ["TA - I", "phase"], sort=False
        )["_region_priority"].transform("min")
        df = df[df["_region_priority"] == df["_best_region_priority"]].reset_index(drop=True)
        df = df.drop(columns=["_region_priority", "_best_region_priority"])
        print(f"\nStep 8 done: {before - len(df)} row(s) removed by region-priority filter. "
              f"Remaining rows: {len(df)}")

        # Step 8 cannot fully remove a TA-I (worst case keeps all Tier-3), but snapshot anyway
        tracker.snapshot(df, 8, "Region-priority filter", pre_step_df=pre_step8)
    else:
        missing = required_cols_8 - set(df.columns)
        print(f"\nStep 8 skipped: missing column(s) {missing}.")

    # -----------------------------------------------------------------------
    # Step 9: Max-size filter
    # -----------------------------------------------------------------------
    required_cols_9 = {"TA - I", "phase", "primary_region", "size"}
    if required_cols_9.issubset(df.columns):
        before = len(df)
        pre_step9 = df.copy()

        df["_size_numeric"] = pd.to_numeric(df["size"], errors="coerce").fillna(0)
        df["_max_size"] = df.groupby(
            ["TA - I", "phase", "primary_region"], sort=False
        )["_size_numeric"].transform("max")

        # Rows where the whole group has size 0 — fall back to highest-phase selection
        all_zero_mask = df["_max_size"] == 0
        normal_mask   = ~all_zero_mask

        # Normal path: keep rows matching the max size in their group
        df_normal = df[normal_mask & (df["_size_numeric"] == df["_max_size"])]
        df_normal = df_normal.drop_duplicates(subset=["TA - I", "phase", "primary_region"], keep="first")

        # Zero-size path: keep the row with the highest phase rank per (TA-I, primary_region)
        df_zero = df[all_zero_mask].copy()
        if not df_zero.empty:
            df_zero["_phase_rank_tmp"] = df_zero["phase"].apply(phase_rank)
            df_zero["_max_phase_tmp"] = df_zero.groupby(
                ["TA - I", "primary_region"], sort=False
            )["_phase_rank_tmp"].transform("max")
            df_zero = df_zero[df_zero["_phase_rank_tmp"] == df_zero["_max_phase_tmp"]]
            df_zero = df_zero.drop_duplicates(subset=["TA - I", "primary_region"], keep="first")
            df_zero = df_zero.drop(columns=["_phase_rank_tmp", "_max_phase_tmp"])

        df = pd.concat([df_normal, df_zero], ignore_index=True)
        df = df.drop(columns=["_size_numeric", "_max_size"]).reset_index(drop=True)
        print(f"\nStep 9 done: {before - len(df)} row(s) removed by max-size filter. "
              f"Remaining rows: {len(df)}")
        tracker.snapshot(df, 9, "Max-size deduplication", pre_step_df=pre_step9)
    else:
        missing = required_cols_9 - set(df.columns)
        print(f"\nStep 9 skipped: missing column(s) {missing}.")

    # Clean up pd.NA before saving
    for col in df.columns:
        df[col] = df[col].where(df[col].notna(), other=None)

    df.to_excel(output_path, index=False)
    print(f"\nOutput saved: {output_path}")

    # -----------------------------------------------------------------------
    # Step 10: Add TA-I Comparison sheet with removal reasons
    # -----------------------------------------------------------------------
    output_tai_set: set = set()
    if "TA - I" in df.columns:
        output_tai_set = set(df["TA - I"].dropna().unique())

    add_tai_comparison_sheet(output_path, input_tai_set, output_tai_set, tracker)
    print(f"\nDone. Final output: {output_path}")


if __name__ == "__main__":
    process()
