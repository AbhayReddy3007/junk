"""
Excel Processing Script
-----------------------
1. Cleans the trial_id column by removing parenthetical suffixes like (ABCDEF).
2. Adds a 'TA - I' column combining therapy_area and ot_disease_name.
3. Deduplicates TA - I rows, keeping the highest-phase row per combination.
   Phase priority: Approved > 3 > 2 > 1 (fuzzy-matched).

Output path is read from OUTPUT_FILE in .env (falls back to input_processed.xlsx).

Usage:
    python process_excel.py input.xlsx
"""

import sys
import re
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

    # Extract numeric portion (e.g. "Phase 3", "3", "P3", "Phase III", "III")
    # Roman numeral support
    roman = {"iii": 3, "ii": 2, "i": 1, "iv": 4}
    for numeral, val in roman.items():
        # Match standalone roman numeral (word boundary)
        if re.search(rf"\b{numeral}\b", text):
            return val

    # Arabic digit
    m = re.search(r"\b([1-4])\b", text)
    if m:
        return int(m.group(1))

    return -1  # unknown / unrecognised


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process(input_path: str, output_path: str | None = None):
    input_path = Path(input_path)

    # Resolve output path: argument > OUTPUT_FILE in .env > default
    if output_path is not None:
        output_path = Path(output_path)
    elif os.getenv("OUTPUT_FILE"):
        output_path = Path(os.getenv("OUTPUT_FILE"))
        print(f"Output path loaded from .env OUTPUT_FILE: {output_path}")
    else:
        output_path = input_path.with_name(input_path.stem + "_processed.xlsx")
        print(f"OUTPUT_FILE not set in .env. Defaulting to: {output_path}")

    print(f"Reading: {input_path}")
    df = pd.read_excel(input_path)

    # -----------------------------------------------------------------------
    # 1. Clean trial_id — remove trailing parenthetical e.g. " (ABCDEF)"
    # -----------------------------------------------------------------------
    if "trial_id" not in df.columns:
        print("WARNING: Column 'trial_id' not found. Skipping step 1.")
    else:
        # Remove any content within parentheses that comes AFTER the main ID
        # Pattern: optional whitespace + opening paren + anything + closing paren
        # anchored to the end (one or more such groups)
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
            # Compute numeric rank for sorting
            df["_phase_rank"] = df["phase"].apply(phase_rank)

            # Sort so that highest rank comes first within each TA - I group
            df_sorted = df.sort_values("_phase_rank", ascending=False)

            # Keep the first (highest-ranked) row per TA - I
            df = df_sorted.drop_duplicates(subset=["TA - I"], keep="first")

            # Restore original row order (by original index)
            df = df.sort_index()

            # Drop helper column
            df = df.drop(columns=["_phase_rank"])

            rows_removed = len(df_sorted) - len(df)
            print(f"Step 3 done: {rows_removed} duplicate TA - I row(s) removed (lower-phase kept out).")

    # -----------------------------------------------------------------------
    # Write output
    # -----------------------------------------------------------------------
    df.to_excel(output_path, index=False)
    print(f"Output saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_excel.py input.xlsx")
        print("       Output path is read from OUTPUT_FILE in .env")
        sys.exit(1)

    input_file = sys.argv[1]
    process(input_file)
