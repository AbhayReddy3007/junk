"""
Excel Processing Script
-----------------------
1. Cleans the trial_id column by removing parenthetical suffixes like (ABCDEF).
2. Adds a 'TA - I' column combining therapy_area and ot_disease_name.
3. Deduplicates TA - I rows, keeping the highest-phase row per combination.
   Phase priority: Approved > 3 > 2 > 1 (fuzzy-matched).

Input path is read from OUTPUT_FILE in .env.
Output is saved alongside the input file as <input_stem>_processed.xlsx.

Usage:
    python process_excel.py

.env example:
    OUTPUT_FILE=path/to/your/input.xlsx
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

    # Check for "approved" first (most advanced)
    if "approved" in text or "approv" in text or "market" in text:
        return 4

    # Roman numeral support (e.g. "Phase III", "III")
    roman = {"iii": 3, "ii": 2, "i": 1, "iv": 4}
    for numeral, val in roman.items():
        if re.search(rf"\b{numeral}\b", text):
            return val

    # Arabic digit (e.g. "Phase 3", "P3", "3")
    m = re.search(r"\b([1-4])\b", text)
    if m:
        return int(m.group(1))

    return -1  # unknown / unrecognised


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process():
    # Read input path from OUTPUT_FILE in .env
    input_file = os.getenv("OUTPUT_FILE")
    if not input_file:
        print("ERROR: OUTPUT_FILE is not set in .env")
        sys.exit(1)

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    # Output saved next to the input file
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
    missing = [c for c in ("therapy_area", "ot_disease_name") if c not in df.columns]
    if missing:
        print(f"WARNING: Column(s) {missing} not found. Skipping steps 2 & 3.")
    else:
        df["TA - I"] = df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
        print("Step 2 done: 'TA - I' column added.")

        # -------------------------------------------------------------------
        # 3. Deduplicate TA - I by keeping highest-phase row
        # -------------------------------------------------------------------
        if "phase" not in df.columns:
            print("WARNING: Column 'phase' not found. Skipping deduplication (step 3).")
        else:
            df["_phase_rank"] = df["phase"].apply(phase_rank)

            df_sorted = df.sort_values("_phase_rank", ascending=False)
            df = df_sorted.drop_duplicates(subset=["TA - I"], keep="first")
            df = df.sort_index()
            df = df.drop(columns=["_phase_rank"])

            rows_removed = len(df_sorted) - len(df)
            print(f"Step 3 done: {rows_removed} duplicate TA - I row(s) removed (lower-phase kept out).")

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
