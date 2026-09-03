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
6. For rows where primary_region, size, or drug_arm_size_n are still missing after the BQ join,
   uses Gemini with Google Search grounding to fill them in.
   Trials are batched per FALLBACK_TRIALS_PER_CALL from .env.

.env variables required:
    OUTPUT_FILE                    - Path to the input Excel file
    GOOGLE_APPLICATION_CREDENTIALS - Path to the GCP service account JSON
    PROJECT_ID                     - GCP project ID
    BQ_DATASET_ID                  - BigQuery dataset ID
    SSTABLE                        - BigQuery table name
    GEMINI_API_KEY                 - Gemini API key
    FALLBACK_TRIALS_PER_CALL       - Number of trials to look up in a single Gemini call

Usage:
    python process_excel.py
"""

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()


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
# Gemini fallback with Google Search grounding
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


def build_prompt(trial_ids: list[str]) -> str:
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

If a value cannot be found after searching, use null. Do not guess.
"""


def gemini_lookup(trial_ids: list[str], api_key: str) -> list[dict]:
    """
    Call Gemini with Google Search grounding for a batch of trial IDs.
    Returns a list of dicts with keys: trial_id, primary_region, size, drug_arm_size_n.
    """
    import urllib.request

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": build_prompt(trial_ids)}]
            }
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0,
        },
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    # Extract text from the response
    try:
        text = raw["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        print(f"  WARNING: Unexpected Gemini response structure: {e}")
        return []

    # Strip any accidental markdown fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        results = json.loads(text)
        if isinstance(results, list):
            return results
        print(f"  WARNING: Gemini returned non-list JSON: {type(results)}")
        return []
    except json.JSONDecodeError as e:
        print(f"  WARNING: Could not parse Gemini JSON response: {e}")
        print(f"  Raw text: {text[:500]}")
        return []


def gemini_fallback_fill(df: pd.DataFrame, api_key: str, batch_size: int) -> pd.DataFrame:
    """
    For rows where primary_region, size, or drug_arm_size_n are missing,
    use Gemini (with Google Search grounding) to fill them in.
    Trials are de-duped before lookup and results applied back to all matching rows.
    """
    target_cols = ["primary_region", "size", "drug_arm_size_n"]

    # Ensure columns exist
    for col in target_cols:
        if col not in df.columns:
            df[col] = None

    # Find rows with at least one missing target column
    needs_fill_mask = df[target_cols].apply(lambda col: col.map(is_missing)).any(axis=1)
    needs_fill_idx  = df.index[needs_fill_mask].tolist()

    if not needs_fill_idx:
        print("Step 6: No rows with missing primary_region / size / drug_arm_size_n. Skipping Gemini fallback.")
        return df

    # Unique trial IDs that need lookup
    unique_trials = df.loc[needs_fill_idx, "trial_id"].dropna().unique().tolist()
    print(f"Step 6: {len(needs_fill_idx)} row(s) have missing fields across {len(unique_trials)} unique trial(s).")
    print(f"        Querying Gemini in batches of {batch_size} trial(s) ...")

    # Batch the unique trial IDs
    batches = [unique_trials[i : i + batch_size] for i in range(0, len(unique_trials), batch_size)]
    all_results: dict[str, dict] = {}  # trial_id -> {primary_region, size, drug_arm_size_n}

    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)}: {batch}")
        try:
            results = gemini_lookup(batch, api_key)
            for entry in results:
                tid = str(entry.get("trial_id", "")).strip()
                if tid:
                    all_results[tid] = entry
        except Exception as e:
            print(f"  WARNING: Gemini call failed for batch {i}: {e}")

        # Polite delay between batches to avoid rate limits
        if i < len(batches):
            time.sleep(2)

    # Apply results back to dataframe — only fill cells that are still missing
    filled_count = 0
    for idx in needs_fill_idx:
        tid = str(df.at[idx, "trial_id"]).strip()
        entry = all_results.get(tid)
        if not entry:
            continue
        for col in target_cols:
            if is_missing(df.at[idx, col]):
                val = entry.get(col)
                if val is not None:
                    df.at[idx, col] = val
                    filled_count += 1

    print(f"Step 6 done: Filled {filled_count} cell(s) via Gemini grounded search.")
    return df


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process():
    # ------------------------------------------------------------------
    # Load and validate .env variables
    # ------------------------------------------------------------------
    input_file       = os.getenv("OUTPUT_FILE")
    credentials      = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id       = os.getenv("PROJECT_ID")
    dataset_id       = os.getenv("BQ_DATASET_ID")
    bq_table         = os.getenv("SSTABLE")
    gemini_api_key   = os.getenv("GEMINI_API_KEY")
    fallback_batch   = os.getenv("FALLBACK_TRIALS_PER_CALL", "5")

    missing_vars = [k for k, v in {
        "OUTPUT_FILE": input_file,
        "GOOGLE_APPLICATION_CREDENTIALS": credentials,
        "PROJECT_ID": project_id,
        "BQ_DATASET_ID": dataset_id,
        "SSTABLE": bq_table,
        "GEMINI_API_KEY": gemini_api_key,
        "FALLBACK_TRIALS_PER_CALL": fallback_batch,
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

    # -----------------------------------------------------------------------
    # 1. Clean trial_id
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 2. Add 'TA - I' column
    # -----------------------------------------------------------------------
    missing_cols = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing_cols:
        print(f"WARNING: Column(s) {missing_cols} not found. Skipping steps 2, 3 & 4.")
    else:
        df["TA - I"] = df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        print("Step 2 done: 'TA - I' column added.")

        # -------------------------------------------------------------------
        # 3. Deduplicate on TA - I by keeping highest-phase row(s)
        # -------------------------------------------------------------------
        if "phase" not in df.columns:
            print("WARNING: Column 'phase' not found. Skipping step 3.")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)
            df["_max_rank"]   = df.groupby("TA - I")["_phase_rank"].transform("max")
            original_count    = len(df)
            df = df[df["_phase_rank"] == df["_max_rank"]]
            df = df.sort_index().drop(columns=["_phase_rank", "_max_rank"])
            print(f"Step 3 done: {original_count - len(df)} lower-phase duplicate TA - I row(s) removed. "
                  f"Rows tied at the highest phase were all kept.")

        # -------------------------------------------------------------------
        # 4. Deduplicate on (TA - I, trial_id)
        # -------------------------------------------------------------------
        if "trial_id" not in df.columns:
            print("WARNING: Column 'trial_id' not found. Skipping step 4.")
        else:
            before = len(df)
            df = df.drop_duplicates(subset=["TA - I", "trial_id"], keep="first").sort_index()
            print(f"Step 4 done: {before - len(df)} duplicate (TA - I, trial_id) combination(s) removed.")

    # -----------------------------------------------------------------------
    # 5. Fetch from BigQuery and left-join on trial_id
    # -----------------------------------------------------------------------
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
        print(f"Step 5 done: BQ columns joined (primary_region, secondary_countries, size, drug_arm_size_n).")

    # -----------------------------------------------------------------------
    # 6. Gemini fallback — fill missing primary_region / size / drug_arm_size_n
    # -----------------------------------------------------------------------
    if "trial_id" not in df.columns:
        print("WARNING: Column 'trial_id' not found. Skipping Gemini fallback (step 6).")
    else:
        df = gemini_fallback_fill(df, gemini_api_key, batch_size)

    # -----------------------------------------------------------------------
    # Write output
    # -----------------------------------------------------------------------
    df.to_excel(output_path, index=False)
    print(f"Output saved: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    process()
