"""
calculations.py
---------------
Takes the output of excel_processing_script.py (a *_processed.xlsx file) and
adds the following derived columns, one function per calculation:

    1.  prior                    – based on association_score
    2.  maturity_weight          – based on phase
    3.  effective_indications    – drug-level sum of maturity_weight (same value
        effective_therapy_areas    for both columns)
    4.  w_geo                    – geographic weight from primary_region tier
    5.  w_dose                   – dosage-rank weight within (drug, dosage) groups
    6.  w_sample                 – sample-size weight from drug_arm_size_n
    7.  Q_i                      – w_geo × w_sample × w_dose
    8.  e_i                      – Q_i × maturity_weight
    9.  Link                     – 1 - (1 - prior) × (1 - e_i)
    10. Link_TA                  – average of Link across all rows sharing the
                                   same therapy_area
    11. L_ind                    – logistic transformation of N_eff_ind
        B_raw_ind                  raw normalised indication breadth
        B_ind                      final normalised indication breadth score
                                   (all three are dataset-level constants
                                    broadcast to every row)
    12. L_TA                     – logistic transformation of unique therapy_area count
        B_raw_TA                   raw normalised therapy-area breadth
        B_TA                       final normalised therapy-area breadth score
                                   (all three are dataset-level constants
                                    broadcast to every row)
    13. B                        – B_ind × B_TA
        B_raw_TA                   raw normalised therapy-area breadth
        B_TA                       final normalised therapy-area breadth score
                                   (all three are dataset-level constants
                                    broadcast to every row)

Indication-breadth constants
-----------------------------
    N0   = 9      (inflection point of logistic curve)
    a    = 0.40   (steepness parameter)

    L_ind(x)      = 1 / (1 + exp(-a * (x - N0)))
    B_raw_ind(x)  = (L_ind(x) - L_ind(0)) / (1 - L_ind(0))
    N_eff_ind     = sum of the effective_indications column across all rows
    B_ind         = min(1, B_raw_ind(N_eff_ind) / B_raw_ind(1))

    All three values are scalars computed once and stored identically in
    every row of the output.

Usage:
    python calculations.py

    The input file path is read from the FILE variable in the .env file
    located in the working directory.

Output:
    <stem>_calculated.xlsx  written alongside the input file.

.env variable required:
    FILE  - Path to the *_processed.xlsx file produced by excel_processing_script.py

The script identifies the "drug" column automatically, trying these names in
order: drug_name, drug, compound_name, molecule_name, generic_name.
If none match, the first column of the file is used as a fallback and a
warning is printed.
"""

import math
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Helpers shared across calculations
# ---------------------------------------------------------------------------

def _is_missing(val) -> bool:
    """Return True for None, NaN, pd.NA, empty / whitespace strings."""
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


def _find_drug_column(df: pd.DataFrame) -> str:
    """
    Return the name of the column that identifies the drug/compound.
    Tries a priority list of common names; falls back to the first column.
    """
    candidates = ["drug_name", "drug", "compound_name", "molecule_name", "generic_name"]
    for name in candidates:
        if name in df.columns:
            return name
    fallback = df.columns[0]
    print(
        f"WARNING: No recognised drug-name column found "
        f"({candidates}). Using '{fallback}' as the drug identifier."
    )
    return fallback


# ---------------------------------------------------------------------------
# Region-priority logic — mirrors excel_processing_script.py exactly
# so that tier assignments are consistent between the two files.
# ---------------------------------------------------------------------------

_EU_COUNTRY_NAMES = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
    "czechia", "denmark", "estonia", "finland", "france", "germany", "greece",
    "hungary", "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta",
    "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia",
    "spain", "sweden",
}

_TIER2_NAMES = {"canada", "switzerland", "australia", "japan"}


def _region_tier(region_val) -> int:
    """
    Return the geographic tier (1 / 2 / 3) for a primary_region value.

    Tier 1: United States / US / UK / Europe / EU / any EU member-state name
    Tier 2: Canada, Switzerland, Australia, Japan
    Tier 3: everything else (including missing)
    """
    if _is_missing(region_val):
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


# ---------------------------------------------------------------------------
# Phase-rank helper (used by w_dose to rank phases within a dosage group)
# ---------------------------------------------------------------------------

def _phase_rank(phase_val) -> int:
    """
    Map a phase label to a comparable integer.
    Higher = more advanced phase.

    approved / marketed → 4
    Phase IV / 4        → 4
    Phase III / 3       → 3
    Phase II / 2        → 2
    Phase I / 1         → 1
    Preclinical / None  → 0
    """
    if _is_missing(phase_val):
        return 0
    text = str(phase_val).strip().lower()
    if re.search(r"\b(approved|approv|marketed|market)\b", text):
        return 4
    roman_map = {"iv": 4, "iii": 3, "ii": 2, "i": 1}
    for roman, val in roman_map.items():
        if re.search(rf"\b{roman}\b", text):
            return val
    m = re.search(r"\b([1-4])\b", text)
    if m:
        return int(m.group(1))
    if re.search(r"\bpreclinical\b", text):
        return 0
    return 0


# ===========================================================================
# 1. prior
# ===========================================================================

def add_prior(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'prior' based on association_score.

      association_score > 0.40          → prior = 0.8
      0.10 <= association_score <= 0.40 → prior = 0.4
      association_score < 0.10          → prior = 0.0
      missing / no data                 → prior = 0.0
    """
    if "association_score" not in df.columns:
        print("WARNING: 'association_score' column not found. 'prior' will be 0 for all rows.")
        df["prior"] = 0.0
        return df

    def _prior(val):
        if _is_missing(val):
            return 0.0
        try:
            score = float(val)
        except (ValueError, TypeError):
            return 0.0
        if score > 0.40:
            return 0.8
        if score >= 0.10:          # 0.10 <= score <= 0.40
            return 0.4
        return 0.0                 # score < 0.10

    df["prior"] = df["association_score"].apply(_prior)
    print(f"  [1] 'prior' added.  Value counts:\n{df['prior'].value_counts().to_string()}")
    return df


# ===========================================================================
# 2. maturity_weight
# ===========================================================================

def add_maturity_weight(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'maturity_weight' based on phase.

      None / unavailable / Preclinical → 0.05
      Phase 1 / 1                      → 0.10
      Phase 2 / 2                      → 0.30
      Phase 3 / 3                      → 0.60
      Phase 4 / 4 / Approved           → 1.00
    """
    if "phase" not in df.columns:
        print("WARNING: 'phase' column not found. 'maturity_weight' will be 0.05 for all rows.")
        df["maturity_weight"] = 0.05
        return df

    def _maturity(val):
        if _is_missing(val):
            return 0.05
        text = str(val).strip().lower()
        if re.search(r"\b(approved|approv|marketed|market)\b", text):
            return 1.00
        if re.search(r"\bpreclinical\b", text):
            return 0.05
        # Roman numerals checked longest-first so "iii" is caught before "i"
        if re.search(r"\biv\b", text) or re.search(r"\b4\b", text):
            return 1.00
        if re.search(r"\biii\b", text) or re.search(r"\b3\b", text):
            return 0.60
        if re.search(r"\bii\b", text) or re.search(r"\b2\b", text):
            return 0.30
        if re.search(r"\bi\b", text) or re.search(r"\b1\b", text):
            return 0.10
        # Anything unrecognised treated as unavailable
        return 0.05

    df["maturity_weight"] = df["phase"].apply(_maturity)
    print(f"  [2] 'maturity_weight' added.  Value counts:\n{df['maturity_weight'].value_counts().to_string()}")
    return df


# ===========================================================================
# 3. effective_indications  &  effective_therapy_areas
# ===========================================================================

def add_effective_indications(df: pd.DataFrame, drug_col: str) -> pd.DataFrame:
    """
    Add columns 'effective_indications' and 'effective_therapy_areas'.

    Both columns hold the same value: the sum of maturity_weight across ALL
    rows that share the same drug (drug_col).  This is a drug-level aggregate
    broadcast back to every row of that drug.

    Requires 'maturity_weight' to already exist (add_maturity_weight first).
    """
    if "maturity_weight" not in df.columns:
        raise ValueError("'maturity_weight' column missing — run add_maturity_weight() first.")
    if drug_col not in df.columns:
        raise ValueError(f"Drug column '{drug_col}' not found in dataframe.")

    drug_sum = (
        df.groupby(drug_col, sort=False)["maturity_weight"]
        .sum()
        .rename("_drug_maturity_sum")
    )
    df = df.join(drug_sum, on=drug_col)
    df["effective_indications"]   = df["_drug_maturity_sum"]
    df["effective_therapy_areas"] = df["_drug_maturity_sum"]
    df = df.drop(columns=["_drug_maturity_sum"])

    print(
        f"  [3] 'effective_indications' and 'effective_therapy_areas' added "
        f"(drug-level sum of maturity_weight)."
    )
    return df


# ===========================================================================
# 4. w_geo
# ===========================================================================

def add_w_geo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'w_geo' based on the geographic tier of primary_region.

      Tier 1 (US / UK / EU / EU member states) → 1.00
      Tier 2 (Canada / Switzerland / Australia / Japan) → 0.85
      Tier 3 (everything else, including missing)       → 0.65
    """
    if "primary_region" not in df.columns:
        print("WARNING: 'primary_region' column not found. 'w_geo' will be 0.65 for all rows.")
        df["w_geo"] = 0.65
        return df

    _tier_to_weight = {1: 1.00, 2: 0.85, 3: 0.65}

    df["w_geo"] = df["primary_region"].apply(
        lambda r: _tier_to_weight[_region_tier(r)]
    )
    print(f"  [4] 'w_geo' added.  Value counts:\n{df['w_geo'].value_counts().to_string()}")
    return df


# ===========================================================================
# 5. w_dose
# ===========================================================================

def add_w_dose(df: pd.DataFrame, drug_col: str) -> pd.DataFrame:
    """
    Add column 'w_dose'.

    Logic:
      - Group rows by (TA-I, dosage).
      - Within each such group, rank the rows by their phase (descending).
      - The row with the highest phase in the group gets w_dose = 1.00.
      - The row with the next-highest phase gets w_dose = 0.75.
      - If a TA-I has only one dosage, or all rows in the group share the
        same phase, all rows in that group receive w_dose = 1.00.
      - Rows with missing dosage are isolated into their own per-TA-I group
        and all receive w_dose = 1.00 (no relative ranking is possible).

    "Highest phase" for a row is determined by _phase_rank applied to its
    phase value. Ties within a group receive the same rank and therefore the
    same w_dose (dense ranking).
    """
    required = {"TA - I", "dosage", "phase"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        print(
            f"WARNING: w_dose requires columns {required}. "
            f"Missing: {missing_cols}.  'w_dose' will be 1.0 for all rows."
        )
        df["w_dose"] = 1.0
        return df

    # Normalise dosage: strip whitespace, lowercase, sentinel for missing
    _MISSING_DOSE_SENTINEL = "__missing__"

    def _norm_dose(val):
        if _is_missing(val):
            return _MISSING_DOSE_SENTINEL
        return str(val).strip().lower()

    df["_dose_key"] = df["dosage"].apply(_norm_dose)
    df["_phase_rank_num"] = df["phase"].apply(_phase_rank)

    # Within each (TA-I, dosage) group, dense-rank rows by phase DESC.
    # Ties share the same rank → same w_dose.
    df["_dose_rank"] = (
        df.groupby(["TA - I", "_dose_key"], sort=False)["_phase_rank_num"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    def _dose_rank_to_weight(rank: int) -> float:
        if rank == 1:
            return 1.00
        return 0.75   # rank 2 and beyond

    df["w_dose"] = df["_dose_rank"].apply(_dose_rank_to_weight)

    # Rows with missing dosage always get w_dose = 1.0 regardless of rank
    df.loc[df["_dose_key"] == _MISSING_DOSE_SENTINEL, "w_dose"] = 1.0

    df = df.drop(columns=["_dose_key", "_phase_rank_num", "_dose_rank"])

    print(f"  [5] 'w_dose' added.  Value counts:\n{df['w_dose'].value_counts().to_string()}")
    return df


# ===========================================================================
# 6. w_sample
# ===========================================================================

def add_w_sample(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'w_sample' based on drug_arm_size_n.

      >= 500          → 1.00
      >= 200, < 500   → 0.85
      >= 50,  < 200   → 0.65
      < 50            → 0.40
      missing         → 0.40  (conservative default)
    """
    if "drug_arm_size_n" not in df.columns:
        print(
            "WARNING: 'drug_arm_size_n' column not found. "
            "'w_sample' will be 0.40 for all rows."
        )
        df["w_sample"] = 0.40
        return df

    def _w_sample(val):
        if _is_missing(val):
            return 0.40
        try:
            n = float(val)
        except (ValueError, TypeError):
            return 0.40
        if n >= 500:
            return 1.00
        if n >= 200:
            return 0.85
        if n >= 50:
            return 0.65
        return 0.40

    df["w_sample"] = df["drug_arm_size_n"].apply(_w_sample)
    print(f"  [6] 'w_sample' added.  Value counts:\n{df['w_sample'].value_counts().to_string()}")
    return df


# ===========================================================================
# 7. Q_i
# ===========================================================================

def add_Q_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Q_i'.

      Q_i = w_geo × w_sample × w_dose

    Requires w_geo, w_sample, and w_dose to already exist.
    """
    required = {"w_geo", "w_sample", "w_dose"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'Q_i' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 4, 5, and 6 have run."
        )

    df["Q_i"] = df["w_geo"] * df["w_sample"] * df["w_dose"]
    print(
        f"  [7] 'Q_i' added (w_geo × w_sample × w_dose).  "
        f"Range: {df['Q_i'].min():.4f} – {df['Q_i'].max():.4f}"
    )
    return df


# ===========================================================================
# 8. e_i
# ===========================================================================

def add_e_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'e_i'.

      e_i = Q_i × maturity_weight

    Requires Q_i and maturity_weight to already exist.
    """
    required = {"Q_i", "maturity_weight"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'e_i' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 2 and 7 have run."
        )

    df["e_i"] = df["Q_i"] * df["maturity_weight"]
    print(
        f"  [8] 'e_i' added (Q_i × maturity_weight).  "
        f"Range: {df['e_i'].min():.4f} – {df['e_i'].max():.4f}"
    )
    return df


# ===========================================================================
# 9. Link
# ===========================================================================

def add_link(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Link'.

      Link = 1 - (1 - prior) × (1 - e_i)

    This is a probabilistic union: it combines prior belief (prior) with
    trial evidence (e_i) such that either alone can drive Link toward 1,
    and neither can push it below 0.

    Requires prior and e_i to already exist.
    """
    required = {"prior", "e_i"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'Link' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 1 and 8 have run."
        )

    df["Link"] = 1 - (1 - df["prior"]) * (1 - df["e_i"])
    print(
        f"  [9] 'Link' added (1 - (1 - prior) × (1 - e_i)).  "
        f"Range: {df['Link'].min():.4f} – {df['Link'].max():.4f}"
    )
    return df


# ===========================================================================
# 10. Link_TA
# ===========================================================================

def add_link_ta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Link_TA'.

      Link_TA = mean of Link across all rows that share the same therapy_area.

    This is a therapy-area-level aggregate broadcast back to every row
    belonging to that therapy area.

    Requires 'Link' to already exist (add_link first) and 'therapy_area'
    to be present in the dataframe.

    Rows whose therapy_area is missing are grouped together under a single
    NaN key; their Link_TA will be the mean of Link for all such rows.
    """
    if "Link" not in df.columns:
        raise ValueError(
            "'Link_TA' calculation requires 'Link'. "
            "Ensure step 9 (add_link) has run."
        )
    if "therapy_area" not in df.columns:
        print(
            "WARNING: 'therapy_area' column not found. "
            "'Link_TA' will be NaN for all rows."
        )
        df["Link_TA"] = float("nan")
        return df

    ta_mean = (
        df.groupby("therapy_area", sort=False, dropna=False)["Link"]
        .mean()
        .rename("Link_TA")
    )
    df = df.join(ta_mean, on="therapy_area")

    print(
        f"  [10] 'Link_TA' added (mean of Link per therapy_area).  "
        f"Range: {df['Link_TA'].min():.4f} – {df['Link_TA'].max():.4f}"
    )
    return df


# ===========================================================================
# 11. L_ind, B_raw_ind, B_ind
# ===========================================================================

# Logistic-curve constants (fixed for the entire model)
_N0 = 9       # inflection point
_A  = 0.40    # steepness parameter


def _l_ind(x: float) -> float:
    """
    Logistic transformation of x.

      L_ind(x) = 1 / (1 + exp(-a * (x - N0)))
               = 1 / (1 + exp(-0.40 * (x - 9)))
    """
    return 1.0 / (1.0 + math.exp(-_A * (x - _N0)))


def _b_raw_ind(x: float, l_ind_0: float) -> float:
    """
    Raw normalised indication breadth at x.

      B_raw_ind(x) = (L_ind(x) * L_ind(0)) / (1 - L_ind(0))
    """
    return (_l_ind(x) * l_ind_0) / (1.0 - l_ind_0)


def add_indication_breadth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add three dataset-level constant columns:

      L_ind     = L_ind(x)
                  where x = number of unique values in ot_disease_name

      B_raw_ind = B_raw_ind(x)
                = (L_ind(x) * L_ind(0)) / (1 - L_ind(0))

      B_ind     = min(1, B_raw_ind(N_eff_ind) / B_raw_ind(15))
                  where N_eff_ind is read from effective_indications (single
                  repeated value across all rows)

    All three are scalars derived once from the dataset and then broadcast
    identically to every row.

    Requires 'effective_indications' and 'ot_disease_name' to already exist.
    """
    if "effective_indications" not in df.columns:
        raise ValueError(
            "'L_ind'/'B_raw_ind'/'B_ind' require 'effective_indications'. "
            "Ensure step 3 (add_effective_indications) has run."
        )
    if "ot_disease_name" not in df.columns:
        print(
            "WARNING: 'ot_disease_name' column not found. "
            "'L_ind', 'B_raw_ind', 'B_ind' will be set to NaN."
        )
        df["L_ind"] = df["B_raw_ind"] = df["B_ind"] = float("nan")
        return df

    # x = unique disease count; N_eff_ind = single repeated value
    x         = df["ot_disease_name"].nunique()
    n_eff_ind = df["effective_indications"].iloc[0]

    # Anchor and derived values
    l_ind_0      = _l_ind(0)               # L_ind(0)
    l_ind_x      = _l_ind(x)               # L_ind(x) → stored as L_ind column
    b_raw_ind_x  = _b_raw_ind(x, l_ind_0)  # B_raw_ind(x) → stored as B_raw_ind column
    b_raw_ind_n  = _b_raw_ind(n_eff_ind, l_ind_0)  # B_raw_ind(N_eff_ind) — numerator of B_ind
    b_raw_ind_15 = _b_raw_ind(15, l_ind_0)          # B_raw_ind(15) — normaliser

    # Guard: if B_raw_ind(15) is effectively zero, B_ind cannot be normalised
    if abs(b_raw_ind_15) < 1e-12:
        print(
            "WARNING: B_raw_ind(15) is effectively zero; "
            "'B_ind' will be set to NaN."
        )
        b_ind = float("nan")
    else:
        b_ind = min(1.0, b_raw_ind_n / b_raw_ind_15)

    # Broadcast constant scalars to every row
    df["L_ind"]     = l_ind_x
    df["B_raw_ind"] = b_raw_ind_x
    df["B_ind"]     = b_ind

    print(
        f"  [11] Indication-breadth columns added (dataset-level constants):\n"
        f"       x (unique ot_disease_name) = {x}\n"
        f"       N_eff_ind                  = {n_eff_ind:.4f}\n"
        f"       L_ind(0)                   = {l_ind_0:.6f}\n"
        f"       L_ind  = L_ind(x)          = {l_ind_x:.6f}\n"
        f"       B_raw_ind = B_raw_ind(x)   = {b_raw_ind_x:.6f}\n"
        f"       B_raw_ind(N_eff_ind)        = {b_raw_ind_n:.6f}\n"
        f"       B_raw_ind(15)               = {b_raw_ind_15:.6f}\n"
        f"       B_ind                       = {b_ind:.6f}"
    )
    return df


# ===========================================================================
# 12. L_TA, B_raw_TA, B_TA
# ===========================================================================

# Logistic-curve constant for therapy-area breadth (inflection point and steepness differ)
_N0_TA = 3    # inflection point for TA curve (vs 9 for indication curve)
_A_TA  = 0.9  # steepness for TA curve (vs 0.40 for indication curve)


def _l_ta(x: float) -> float:
    """
    Logistic transformation of x for the therapy-area curve.

      L_TA(x) = 1 / (1 + exp(-0.9 * (x - 3)))
    """
    return 1.0 / (1.0 + math.exp(-_A_TA * (x - _N0_TA)))


def _b_raw_ta(x: float, l_ta_0: float) -> float:
    """
    Raw normalised therapy-area breadth at x.

      B_raw_TA(x) = (L_TA(x) * L_TA(0)) / (1 - L_TA(0))
    """
    return (_l_ta(x) * l_ta_0) / (1.0 - l_ta_0)


def add_therapy_area_breadth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add three dataset-level constant columns:

      L_TA     = L_TA(x)
                 where x = number of unique values in therapy_area

      B_raw_TA = B_raw_TA(x)
               = (L_TA(x) * L_TA(0)) / (1 - L_TA(0))

      B_TA     = min(1, B_raw_TA(N_eff_ind) / B_raw_TA(5))
                 where N_eff_ind is read from effective_indications (single
                 repeated value across all rows)

    All three are scalars derived once from the dataset and then broadcast
    identically to every row.

    Requires 'effective_indications' and 'therapy_area' to already exist.
    """
    if "effective_indications" not in df.columns:
        raise ValueError(
            "'L_TA'/'B_raw_TA'/'B_TA' require 'effective_indications'. "
            "Ensure step 3 (add_effective_indications) has run."
        )
    if "therapy_area" not in df.columns:
        print(
            "WARNING: 'therapy_area' column not found. "
            "'L_TA', 'B_raw_TA', 'B_TA' will be set to NaN."
        )
        df["L_TA"] = df["B_raw_TA"] = df["B_TA"] = float("nan")
        return df

    # x = unique therapy area count; N_eff_ind = single repeated value
    x         = df["therapy_area"].nunique()
    n_eff_ind = df["effective_indications"].iloc[0]

    # Anchor and derived values
    l_ta_0      = _l_ta(0)                # L_TA(0)
    l_ta_x      = _l_ta(x)               # L_TA(x) → stored as L_TA column
    b_raw_ta_x  = _b_raw_ta(x, l_ta_0)   # B_raw_TA(x) → stored as B_raw_TA column
    b_raw_ta_n  = _b_raw_ta(n_eff_ind, l_ta_0)  # B_raw_TA(N_eff_ind) — numerator of B_TA
    b_raw_ta_5  = _b_raw_ta(5, l_ta_0)           # B_raw_TA(5) — normaliser

    # Guard: if B_raw_TA(5) is effectively zero, B_TA cannot be normalised
    if abs(b_raw_ta_5) < 1e-12:
        print(
            "WARNING: B_raw_TA(5) is effectively zero; "
            "'B_TA' will be set to NaN."
        )
        b_ta = float("nan")
    else:
        b_ta = min(1.0, b_raw_ta_n / b_raw_ta_5)

    # Broadcast constant scalars to every row
    df["L_TA"]     = l_ta_x
    df["B_raw_TA"] = b_raw_ta_x
    df["B_TA"]     = b_ta

    print(
        f"  [12] Therapy-area breadth columns added (dataset-level constants):\n"
        f"       x (unique therapy_area)    = {x}\n"
        f"       N_eff_ind                  = {n_eff_ind:.4f}\n"
        f"       L_TA(0)                    = {l_ta_0:.6f}\n"
        f"       L_TA   = L_TA(x)           = {l_ta_x:.6f}\n"
        f"       B_raw_TA = B_raw_TA(x)     = {b_raw_ta_x:.6f}\n"
        f"       B_raw_TA(N_eff_ind)         = {b_raw_ta_n:.6f}\n"
        f"       B_raw_TA(5)                 = {b_raw_ta_5:.6f}\n"
        f"       B_TA                        = {b_ta:.6f}"
    )
    return df


# ===========================================================================
# 13. B
# ===========================================================================

def add_B(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'B'.

      B = B_ind * B_TA

    Requires 'B_ind' and 'B_TA' to already exist (steps 11 and 12).
    """
    required = {"B_ind", "B_TA"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'B' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 11 and 12 have run."
        )

    df["B"] = df["B_ind"] * df["B_TA"]
    print(
        f"  [13] 'B' added (B_ind × B_TA).  "
        f"Value: {df['B'].iloc[0]:.6f}"
    )
    return df


# ===========================================================================
# Main pipeline
# ===========================================================================

def run_calculations(input_path: Path) -> Path:
    """
    Load the processed Excel file, apply all calculations in order,
    and write the result to <stem>_calculated.xlsx.

    Returns the output path.
    """
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    print(f"\nLoading: {input_path}")
    df = pd.read_excel(input_path)
    print(f"  Loaded {len(df)} rows × {len(df.columns)} columns.")

    # Identify the drug column once; pass it to functions that need it
    drug_col = _find_drug_column(df)
    print(f"  Drug identifier column: '{drug_col}'")

    print("\nRunning calculations ...")

    df = add_prior(df)                           # 1
    df = add_maturity_weight(df)                 # 2
    df = add_effective_indications(df, drug_col) # 3
    df = add_w_geo(df)                           # 4
    df = add_w_dose(df, drug_col)                # 5
    df = add_w_sample(df)                        # 6
    df = add_Q_i(df)                             # 7
    df = add_e_i(df)                             # 8
    df = add_link(df)                            # 9
    df = add_link_ta(df)                         # 10
    df = add_indication_breadth(df)              # 11
    df = add_therapy_area_breadth(df)            # 12
    df = add_B(df)                               # 13

    # Write output
    output_path = input_path.with_name(input_path.stem + "_calculated.xlsx")
    df.to_excel(output_path, index=False)
    print(f"\nOutput saved: {output_path}")
    print(f"  Rows: {len(df)}  |  Columns: {len(df.columns)}")

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_dotenv()

    file_path = os.getenv("FILE")
    if not file_path:
        print("ERROR: 'FILE' variable not set in .env (or .env not found).")
        sys.exit(1)

    run_calculations(Path(file_path))
