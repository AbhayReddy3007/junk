"""
Trial Weight Calculator
-----------------------
Processes Clinical Trials data to compute a trial_weight score for each trial.

Steps performed:
  1. Cleans trial_id (removes parenthetical suffixes).
  2. Adds 'TA - I' column (therapy_area + ot_disease_name).
  3. Enrichment (Step 6): Fills missing primary_region, size, drug_arm_size_n, dosage
     via ClinicalTrials.gov API and Gemini fallback.
  4. Computes trial_weight = phase_weight * geo_score * sample_score * dosage_score

Weight components
-----------------
phase_weight:
  Phase 3 (or Approved) → 1.00
  Phase 2               → 0.75
  Phase 1               → 0.50
  Phase NA / unknown    → 0.05

geo_score:
  US / UK / EU (Tier 1) → 1.00
  Canada / Switzerland / Australia / Japan (Tier 2) → 0.85
  Any other             → 0.65

sample_score  (based on drug_arm_size_n; falls back to size):
  ≥ 500  → 1.00
  300–499 → 0.85
  50–199  → 0.65
  < 50    → 0.40
  (200–299 treated as 50–199 band, i.e. 0.65)

dosage_score  (ranked within each TA-I by phase, then by drug_arm_size_n / size):
  Highest priority dosage  → 1.00
  Next                     → 0.75
  All remaining            → 0.50

.env variables required (same as the reference script):
  OUTPUT_FILE                    - Path to the input Excel file
  GOOGLE_APPLICATION_CREDENTIALS - Path to the GCP service account JSON
  GEMINI_API_KEY                 - Gemini API key
  FALLBACK_TRIALS_PER_CALL       - Trials per Gemini call (default: 5)

BQ variables (PROJECT_ID, BQ_DATASET_ID, SSTABLE) are optional;
if absent the BQ join is skipped and enrichment falls straight through
to CT.gov + Gemini.
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
# Helpers (verbatim from reference script)
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
# Phase helpers
# ---------------------------------------------------------------------------

def normalize_phase(phase_value):
    if pd.isna(phase_value):
        return phase_value
    text = str(phase_value).strip()
    lower = text.lower()
    if ("approved" in lower or "approv" in lower or "market" in lower
            or "submitted" in lower):
        return "Approved"
    if re.search(r"3b", lower) or re.search(r"iiib", lower):
        return "Phase 3"
    return text


def phase_rank(phase_value) -> int:
    if pd.isna(phase_value):
        return -1
    text = str(phase_value).strip().lower()
    if ("approved" in text or "approv" in text or "market" in text
            or "submitted" in text):
        return 4
    if re.search(r"3b", text) or re.search(r"iiib", text):
        return 3
    roman = {"iii": 3, "ii": 2, "i": 1, "iv": 4}
    for numeral, val in roman.items():
        if re.search(rf"\b{numeral}\b", text):
            return val
    m = re.search(r"\b([1-4])\b", text)
    if m:
        return int(m.group(1))
    return -1


# ---------------------------------------------------------------------------
# Weight computation
# ---------------------------------------------------------------------------

def compute_phase_weight(phase_value) -> float:
    rank = phase_rank(phase_value)
    if rank >= 3:   # Phase 3 or Approved/Phase 4
        return 1.00
    if rank == 2:
        return 0.75
    if rank == 1:
        return 0.50
    return 0.05     # unknown / NA


def compute_geo_score(primary_region) -> float:
    if is_missing(primary_region):
        return 0.65

    _EU_COUNTRY_NAMES = {
        "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
        "czechia", "denmark", "estonia", "finland", "france", "germany", "greece",
        "hungary", "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta",
        "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia",
        "spain", "sweden",
    }
    _TIER2 = {"canada", "switzerland", "australia", "japan"}

    text = str(primary_region).strip().lower()
    if re.search(r"\b(us|usa|united states|u\.s\.a?\.?)\b", text):
        return 1.00
    if re.search(r"\b(uk|u\.k\.|united kingdom|great britain|gb)\b", text):
        return 1.00
    if re.search(r"\b(europe|eu|european union|e\.u\.)\b", text):
        return 1.00
    if text in _EU_COUNTRY_NAMES:
        return 1.00
    if text in _TIER2 or re.search(r"\b(canada|switzerland|australia|japan)\b", text):
        return 0.85
    return 0.65


def compute_sample_score(drug_arm_size_n, size_fallback) -> float:
    """
    Use drug_arm_size_n preferentially; fall back to size if missing.
    """
    n = None
    for candidate in (drug_arm_size_n, size_fallback):
        if not is_missing(candidate):
            try:
                n = float(candidate)
                break
            except (ValueError, TypeError):
                pass
    if n is None:
        return 0.40   # treat as < 50 (worst band)
    if n >= 500:
        return 1.00
    if n >= 300:
        return 0.85
    if n >= 50:
        return 0.65
    return 0.40


def assign_dosage_scores(df: pd.DataFrame) -> pd.Series:
    """
    Assign dosage_score within each TA-I group.

    Priority ordering of dosages:
      1. Highest phase_rank
      2. Within same phase: highest drug_arm_size_n (fallback: size)
      3. Within same phase + arm size: original row order

    Scores:
      Rank 1  → 1.00
      Rank 2  → 0.75
      Rank 3+ → 0.50
    """
    scores = pd.Series(0.50, index=df.index, dtype=float)

    df = df.copy()
    df["_phase_rank_tmp"] = df["phase"].apply(phase_rank)
    df["_arm_size_tmp"] = (
        df["drug_arm_size_n"]
        .combine_first(df["size"] if "size" in df.columns else pd.Series(dtype=float))
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    for tai, group in df.groupby("TA - I", sort=False):
        # Sort: highest phase first, then highest arm size (both descending).
        sorted_idx = group.sort_values(
            ["_phase_rank_tmp", "_arm_size_tmp"],
            ascending=[False, False],
        ).index

        for rank_pos, idx in enumerate(sorted_idx):
            if rank_pos == 0:
                scores.at[idx] = 1.00
            elif rank_pos == 1:
                scores.at[idx] = 0.75
            else:
                scores.at[idx] = 0.50

    return scores


# ---------------------------------------------------------------------------
# Lookup cache
# ---------------------------------------------------------------------------

def _load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                print(f"  Loaded {len(data)} cached trial(s) from {cache_path}")
                return data
        except Exception as e:
            print(f"  WARNING: Could not read cache {cache_path}: {e}")
    return {}


def _save_cache(cache_path: Path, cache: dict):
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, default=str)
    except Exception as e:
        print(f"  WARNING: Could not write cache {cache_path}: {e}")


# ---------------------------------------------------------------------------
# ClinicalTrials.gov API (Step 6a — verbatim from reference)
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
                  f"per-arm counts unavailable")
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
# Gemini fallback (Step 6b — verbatim from reference)
# ---------------------------------------------------------------------------

def _build_gemini_prompt(trial_ids):
    trials_list = "\n".join(f"- {t}" for t in trial_ids)
    return f"""You are a clinical trial data expert. Use Google Search to look up each trial ID below.

Trial IDs:
{trials_list}

For each trial find:

- primary_region: The primary geographic region of the trial sites.
- size: Patients enrolled in the DRUG/TREATMENT arm(s) only (total enrollment if arm-level unavailable).
- drug_arm_size_n: Same as size.
- dosage: Dose and regimen of the investigational drug arm (e.g. "10 mg once daily").

Return ONLY a valid JSON array, no explanation, no markdown fences:
[
  {{"trial_id": "NCT12345678", "primary_region": "United States", "size": 250, "drug_arm_size_n": 250, "dosage": "10 mg once daily"}}
]

Use null only if genuinely not findable after searching. Do not guess.
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
                return []
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
        text_parts = [p["text"] for p in parts if "text" in p and not p.get("thought", False)]
        if not text_parts:
            raise ValueError("No text part in Gemini response")
        text = " ".join(text_parts)
    except (KeyError, IndexError, ValueError) as e:
        print(f"  WARNING: Unexpected Gemini response structure: {e}")
        return []

    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        print(f"  WARNING: No JSON array in Gemini response. Raw: {text[:500]}")
        return []
    text = match.group(0)

    try:
        results = json.loads(text)
        return results if isinstance(results, list) else []
    except json.JSONDecodeError as e:
        print(f"  WARNING: Could not parse Gemini JSON: {e}")
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
# Enrichment: fill missing fields via CT.gov → Gemini
# ---------------------------------------------------------------------------

def fill_missing_fields(df: pd.DataFrame, api_key: str, batch_size: int,
                        cache_path: Path = None) -> pd.DataFrame:
    target_cols = ["primary_region", "size", "drug_arm_size_n", "dosage"]
    df = df.reset_index(drop=True)

    for col in target_cols:
        if col not in df.columns:
            df[col] = None
    for col in ["size", "drug_arm_size_n", "dosage"]:
        df[col] = df[col].astype(object)
    df["primary_region"] = df["primary_region"].astype(object)

    cache = _load_cache(cache_path) if cache_path else {}
    df["_trial_id_upper"] = df["trial_id"].astype(str).str.strip().str.upper()

    def _needs_fill(row):
        return any(is_missing(row.get(col)) for col in target_cols)

    print(f"\nEnrichment — Missing field summary (before fallback):")
    for col in target_cols:
        print(f"  Missing {col:25s}: {df[col].apply(is_missing).sum()} row(s)")

    # Determine which unique trial IDs need enrichment
    missing_per_trial = {}
    for _, row in df.iterrows():
        if not _needs_fill(row):
            continue
        tid = row["_trial_id_upper"]
        if not tid or tid in ("", "NAN", "NONE"):
            continue
        missing_per_trial.setdefault(tid, set()).update(
            col for col in target_cols if is_missing(row.get(col))
        )

    unique_trials_needing_fill = list(missing_per_trial.keys())
    if not unique_trials_needing_fill:
        print("Enrichment: No rows with missing fields. Skipping API calls.")
        return df.drop(columns=["_trial_id_upper"])

    # Apply cache
    cache_filled = 0
    still_needing_fill = []
    for tid in unique_trials_needing_fill:
        cached = cache.get(tid)
        if cached:
            for idx in df.index[df["_trial_id_upper"] == tid]:
                for col in target_cols:
                    val = cached.get(col)
                    if is_missing(df.at[idx, col]) and val is not None:
                        df.at[idx, col] = val
                        cache_filled += 1
        else:
            still_needing_fill.append(tid)

    if cache_filled:
        print(f"  Cache filled {cache_filled} cell(s).")
    unique_trials_needing_fill = still_needing_fill

    if not unique_trials_needing_fill:
        print("Enrichment: All missing fields resolved from cache.")
        return df.drop(columns=["_trial_id_upper"])

    # CT.gov
    ctgov_results = clinicaltrials_lookup(unique_trials_needing_fill)
    filled_ctgov = 0
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
    print(f"  CT.gov filled {filled_ctgov} cell(s).")
    for tid, entry in ctgov_results.items():
        cache.setdefault(tid, {}).update(entry)
        cache[tid]["_ctgov_found"] = True
    _save_cache(cache_path, cache)

    # Gemini
    still_missing_trials = [
        tid for tid in unique_trials_needing_fill
        if any(is_missing(df.loc[df["_trial_id_upper"] == tid, col].values[0])
               for col in target_cols
               if len(df.loc[df["_trial_id_upper"] == tid]) > 0)
    ]
    if still_missing_trials:
        print(f"  {len(still_missing_trials)} trial(s) still missing → Gemini ...")
        gemini_results = gemini_fallback(still_missing_trials, api_key, batch_size)
        filled_gemini = 0
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
        print(f"  Gemini filled {filled_gemini} cell(s).")
        for tid, entry in gemini_results.items():
            cache.setdefault(tid, {}).update(entry)
            cache[tid]["_gemini_found"] = True
        _save_cache(cache_path, cache)
    else:
        print("  All fields resolved by CT.gov. Gemini not needed.")

    df = df.drop(columns=["_trial_id_upper"])

    print(f"\nEnrichment — Missing field summary (after fallback):")
    for col in target_cols:
        print(f"  Still missing {col:20s}: {df[col].apply(is_missing).sum()} row(s)")

    return df


# ---------------------------------------------------------------------------
# Optional BigQuery join
# ---------------------------------------------------------------------------

def try_bq_join(df: pd.DataFrame, project_id: str, dataset_id: str, bq_table: str) -> pd.DataFrame:
    try:
        from google.cloud import bigquery
    except ImportError:
        print("  google-cloud-bigquery not installed — skipping BQ join.")
        return df

    try:
        client = bigquery.Client(project=project_id)
        query = f"""
            SELECT trial_id, primary_region, secondary_countries, size, drug_arm_size_n, dosage
            FROM `{project_id}.{dataset_id}.{bq_table}`
        """
        print(f"BQ join: querying `{project_id}.{dataset_id}.{bq_table}` ...")
        bq_df = client.query(query).to_dataframe()
        print(f"  Fetched {len(bq_df)} rows from BigQuery.")

        bq_cols = ["trial_id", "primary_region", "secondary_countries",
                   "size", "drug_arm_size_n", "dosage"]
        bq_df = bq_df[[c for c in bq_cols if c in bq_df.columns]].copy()
        bq_df["trial_id"] = bq_df["trial_id"].astype(str).str.strip()
        bq_df["_non_null_count"] = bq_df.drop(columns=["trial_id"]).notna().sum(axis=1)
        bq_df = (
            bq_df.sort_values("_non_null_count", ascending=False)
                 .drop_duplicates(subset=["trial_id"], keep="first")
                 .drop(columns=["_non_null_count"])
        )

        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            df = df.drop(columns=existing)
        df = df.merge(bq_df, on="trial_id", how="left").reset_index(drop=True)
        print(f"  BQ join done. Rows: {len(df)}")
    except Exception as e:
        print(f"  WARNING: BQ join failed: {e}")

    return df


# ---------------------------------------------------------------------------
# Excel output with formatting
# ---------------------------------------------------------------------------

def write_output(df: pd.DataFrame, output_path: Path):
    """Write the result to an Excel file with colour-coded trial_weight column."""

    df.to_excel(output_path, index=False, sheet_name="Trial Weights")

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    ws.title = "Trial Weights"

    FN = "Arial"
    hdr_fill = PatternFill("solid", fgColor="1F4E79")
    hdr_font = Font(name=FN, bold=True, color="FFFFFF", size=11)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align   = Alignment(horizontal="left",   vertical="center")

    thin = Side(style="thin", color="BFBFBF")
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Header row
    for cell in ws[1]:
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = center_align
        cell.border    = thin_border
    ws.row_dimensions[1].height = 22

    # Find trial_weight column
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    tw_col = headers.index("trial_weight") + 1 if "trial_weight" in headers else None

    # Colour bands for trial_weight
    def _tw_fill(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return None
        if v >= 0.75:
            return PatternFill("solid", fgColor="C6EFCE")   # green
        if v >= 0.50:
            return PatternFill("solid", fgColor="FFEB9C")   # amber
        return PatternFill("solid", fgColor="FFC7CE")        # red

    alt_fill = PatternFill("solid", fgColor="F2F2F2")

    for row_num in range(2, ws.max_row + 1):
        is_alt = (row_num % 2 == 0)
        for col_num in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.font   = Font(name=FN, size=10)
            cell.border = thin_border
            cell.alignment = center_align if col_num == tw_col else left_align
            if col_num == tw_col:
                tw_fill = _tw_fill(cell.value)
                if tw_fill:
                    cell.fill = tw_fill
                    cell.font = Font(name=FN, size=10, bold=True)
            elif is_alt:
                cell.fill = alt_fill
        ws.row_dimensions[row_num].height = 16

    # Column widths
    col_widths = {
        "trial_id": 18, "TA - I": 45, "therapy_area": 22, "ot_disease_name": 30,
        "phase": 12, "primary_region": 22, "drug_arm_size_n": 18, "size": 10,
        "dosage": 35, "data_source": 18,
        "phase_weight": 14, "geo_score": 12, "sample_score": 14,
        "dosage_score": 14, "trial_weight": 14,
    }
    for col_num, header in enumerate(headers, start=1):
        width = col_widths.get(str(header), 18)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = width

    ws.freeze_panes = "A2"

    # Legend sheet
    ls = wb.create_sheet("Legend")
    legend_rows = [
        ("Component", "Condition", "Score"),
        ("phase_weight", "Phase 3 / Approved", "1.00"),
        ("phase_weight", "Phase 2", "0.75"),
        ("phase_weight", "Phase 1", "0.50"),
        ("phase_weight", "Unknown / NA", "0.05"),
        ("", "", ""),
        ("geo_score", "US / UK / EU (Tier 1)", "1.00"),
        ("geo_score", "Canada / Switzerland / Australia / Japan (Tier 2)", "0.85"),
        ("geo_score", "Any other region (Tier 3)", "0.65"),
        ("", "", ""),
        ("sample_score", "drug_arm_size_n ≥ 500", "1.00"),
        ("sample_score", "300–499", "0.85"),
        ("sample_score", "50–299", "0.65"),
        ("sample_score", "< 50 (or unknown)", "0.40"),
        ("", "", ""),
        ("dosage_score", "Highest-priority dosage (by phase then arm size)", "1.00"),
        ("dosage_score", "Second-priority dosage", "0.75"),
        ("dosage_score", "All other dosages", "0.50"),
        ("", "", ""),
        ("trial_weight", "= phase_weight × geo_score × sample_score × dosage_score", ""),
    ]
    for r, row in enumerate(legend_rows, start=1):
        for c, val in enumerate(row, start=1):
            cell = ls.cell(row=r, column=c, value=val)
            cell.font = Font(name=FN, bold=(r == 1), size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if r == 1:
                cell.fill = PatternFill("solid", fgColor="1F4E79")
                cell.font = Font(name=FN, bold=True, color="FFFFFF", size=11)
    for col_letter, width in zip(["A", "B", "C"], [16, 55, 10]):
        ls.column_dimensions[col_letter].width = width

    wb.save(output_path)
    print(f"\nFormatted output saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process():
    input_file     = os.getenv("OUTPUT_FILE")
    credentials    = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    fallback_batch = os.getenv("FALLBACK_TRIALS_PER_CALL", "5")

    # BQ vars are optional
    project_id  = os.getenv("PROJECT_ID")
    dataset_id  = os.getenv("BQ_DATASET_ID")
    bq_table    = os.getenv("SSTABLE")

    missing_required = [k for k, v in {
        "OUTPUT_FILE":   input_file,
        "GEMINI_API_KEY": gemini_api_key,
    }.items() if not v]
    if missing_required:
        print(f"ERROR: Missing required .env variable(s): {', '.join(missing_required)}")
        sys.exit(1)

    if credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials

    try:
        batch_size = int(fallback_batch)
        if batch_size < 1:
            raise ValueError
    except ValueError:
        print("ERROR: FALLBACK_TRIALS_PER_CALL must be a positive integer.")
        sys.exit(1)

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    output_path = input_path.with_name(input_path.stem + "_trial_weights.xlsx")
    cache_path  = input_path.with_name(input_path.stem + "_lookup_cache.json")

    print(f"Input file  : {input_path}")
    print(f"Output file : {output_path}")
    print(f"Cache file  : {cache_path}")

    # -----------------------------------------------------------------------
    # Load
    # -----------------------------------------------------------------------
    df = pd.read_excel(input_path)
    print(f"\nLoaded {len(df)} rows, {len(df.columns)} columns.")

    # -----------------------------------------------------------------------
    # Filter: Clinical Trials only
    # -----------------------------------------------------------------------
    if "data_source" in df.columns:
        before = len(df)
        df = df[df["data_source"].astype(str).str.strip().str.lower() == "clinical trials"].copy()
        print(f"\nFiltered to Clinical Trials rows: {len(df)} / {before} rows retained.")
    else:
        print("\nWARNING: 'data_source' column not found — processing all rows as Clinical Trials.")

    if df.empty:
        print("No Clinical Trials rows found. Nothing to process.")
        sys.exit(0)

    df = df.reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Step 1: Clean trial_id
    # -----------------------------------------------------------------------
    if "trial_id" not in df.columns:
        print("WARNING: 'trial_id' column not found. Skipping Step 1.")
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
    missing_ta_cols = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing_ta_cols:
        print(f"WARNING: Columns {missing_ta_cols} not found. 'TA - I' will not be created.")
    else:
        df["TA - I"] = (
            df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        )
        print("Step 2 done: 'TA - I' column added.")

    # Normalise phase
    if "phase" in df.columns:
        df["phase"] = df["phase"].apply(normalize_phase)
        print("Phase values normalised.")

    # -----------------------------------------------------------------------
    # Optional BQ join (Step 5 equivalent)
    # -----------------------------------------------------------------------
    if all([project_id, dataset_id, bq_table]) and "trial_id" in df.columns:
        print("\nBQ credentials found — attempting join ...")
        df = try_bq_join(df, project_id, dataset_id, bq_table)
    else:
        print("\nBQ variables not fully set — skipping BQ join.")

    # -----------------------------------------------------------------------
    # Step 6: Enrichment (CT.gov + Gemini)
    # -----------------------------------------------------------------------
    if "trial_id" in df.columns:
        print("\nStep 6: Enrichment ...")
        df = fill_missing_fields(df, gemini_api_key, batch_size, cache_path=cache_path)
    else:
        print("\nStep 6 skipped: no trial_id column.")

    # Ensure numeric types for size columns
    for col in ["size", "drug_arm_size_n"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------------------------------------------------------
    # Weight calculation
    # -----------------------------------------------------------------------
    print("\nCalculating weight components ...")

    # phase_weight
    df["phase_weight"] = df["phase"].apply(compute_phase_weight)

    # geo_score
    df["geo_score"] = df["primary_region"].apply(compute_geo_score)

    # sample_score
    df["sample_score"] = df.apply(
        lambda r: compute_sample_score(
            r.get("drug_arm_size_n"), r.get("size")
        ), axis=1
    )

    # dosage_score (within TA-I, ordered by phase then arm size)
    if "TA - I" in df.columns:
        df["dosage_score"] = assign_dosage_scores(df)
    else:
        # No grouping possible — every row gets top score
        df["dosage_score"] = 1.00

    # trial_weight
    df["trial_weight"] = (
        df["phase_weight"] * df["geo_score"] * df["sample_score"] * df["dosage_score"]
    ).round(4)

    print("Weight calculation done.")
    print(f"\nSummary statistics for trial_weight:")
    desc = df["trial_weight"].describe()
    for stat in ["count", "mean", "min", "25%", "50%", "75%", "max"]:
        print(f"  {stat:6s}: {desc[stat]:.4f}")

    # -----------------------------------------------------------------------
    # Reorder columns: put weight cols at the end
    # -----------------------------------------------------------------------
    weight_cols = ["phase_weight", "geo_score", "sample_score", "dosage_score", "trial_weight"]
    other_cols  = [c for c in df.columns if c not in weight_cols]
    df = df[other_cols + weight_cols]

    # Clean pd.NA before saving
    for col in df.columns:
        df[col] = df[col].where(df[col].notna(), other=None)

    # -----------------------------------------------------------------------
    # Write output
    # -----------------------------------------------------------------------
    write_output(df, output_path)
    print(f"\nDone. Output: {output_path}")


if __name__ == "__main__":
    process()
