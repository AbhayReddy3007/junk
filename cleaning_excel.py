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

.env variables required:
    OUTPUT_FILE                  - Path to the input Excel file
    GOOGLE_APPLICATION_CREDENTIALS - Path to the GCP service account JSON
    PROJECT_ID                   - GCP project ID
    BQ_DATASET_ID                - BigQuery dataset ID
    SSTABLE                      - BigQuery table name

Usage:
    python process_excel.py
"""

import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os

# Load variables from .env file (looks for .env in the current working directory)
load_dotenv()


# ---------------------------------------------------------------------------
# Phase ranking logic
# ---------------------------------------------------------------------------

def phase_rank(phase_value) -> int:
    """
    Return an integer rank for a phase value (higher = more advanced).
    Priority: Approved > Phase 3 > Phase 2 > Phase 1 > unknown
    """
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
    """
    Fetch trial_id, primary_region, secondary_countries, size, drug_arm_size_n
    from the specified BigQuery table using the service account credentials
    set in GOOGLE_APPLICATION_CREDENTIALS.
    """
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
# Main processing
# ---------------------------------------------------------------------------

def process():
    # ------------------------------------------------------------------
    # Load and validate .env variables
    # ------------------------------------------------------------------
    input_file   = os.getenv("OUTPUT_FILE")
    credentials  = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id   = os.getenv("PROJECT_ID")
    dataset_id   = os.getenv("BQ_DATASET_ID")
    bq_table     = os.getenv("SSTABLE")

    missing_vars = [k for k, v in {
        "OUTPUT_FILE": input_file,
        "GOOGLE_APPLICATION_CREDENTIALS": credentials,
        "PROJECT_ID": project_id,
        "BQ_DATASET_ID": dataset_id,
        "SSTABLE": bq_table,
    }.items() if not v]

    if missing_vars:
        print(f"ERROR: Missing required .env variable(s): {', '.join(missing_vars)}")
        sys.exit(1)

    # Point the GCP client library to the service account file
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
    # 1. Clean trial_id — remove trailing parenthetical e.g. " (ABCDEF)"
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
        # 3. Deduplicate on TA - I by keeping highest-phase row(s).
        #    Rows tied at the highest phase are all kept.
        # -------------------------------------------------------------------
        if "phase" not in df.columns:
            print("WARNING: Column 'phase' not found. Skipping step 3.")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)
            df["_max_rank"]   = df.groupby("TA - I")["_phase_rank"].transform("max")

            original_count = len(df)
            df = df[df["_phase_rank"] == df["_max_rank"]]
            df = df.sort_index().drop(columns=["_phase_rank", "_max_rank"])

            print(f"Step 3 done: {original_count - len(df)} lower-phase duplicate TA - I row(s) removed. "
                  f"Rows tied at the highest phase were all kept.")

        # -------------------------------------------------------------------
        # 4. Deduplicate on (TA - I, trial_id) — each combination must be unique.
        # -------------------------------------------------------------------
        if "trial_id" not in df.columns:
            print("WARNING: Column 'trial_id' not found. Skipping step 4.")
        else:
            before = len(df)
            df = df.drop_duplicates(subset=["TA - I", "trial_id"], keep="first").sort_index()
            print(f"Step 4 done: {before - len(df)} duplicate (TA - I, trial_id) combination(s) removed.")

    # -----------------------------------------------------------------------
    # 5. Fetch from BigQuery and left-join onto the Excel data on trial_id
    # -----------------------------------------------------------------------
    if "trial_id" not in df.columns:
        print("WARNING: Column 'trial_id' not found. Skipping BQ join (step 5).")
    else:
        bq_df = fetch_bq_data(project_id, dataset_id, bq_table)

        # Ensure trial_id types match for the join
        bq_df["trial_id"] = bq_df["trial_id"].astype(str).str.strip()

        # Drop BQ columns that already exist in df (except the join key) to avoid conflicts
        bq_cols = ["trial_id", "primary_region", "secondary_countries", "size", "drug_arm_size_n"]
        existing = [c for c in bq_cols if c != "trial_id" and c in df.columns]
        if existing:
            print(f"  Note: Overwriting existing column(s) from BQ data: {existing}")
            df = df.drop(columns=existing)

        df = df.merge(bq_df[bq_cols], on="trial_id", how="left")
        print(f"Step 5 done: BQ columns joined (primary_region, secondary_countries, size, drug_arm_size_n).")

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
