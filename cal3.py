"""
calculations.py
---------------
Takes the output of trial_weight_calculator.py (a *_trial_weights.xlsx file)
and adds the following derived columns, one function per calculation:

    1.  prior                    – based on association_score
    2.  maturity_weight          – based on phase
    3.  effective_indications    – drug-level sum of maturity_weight
        effective_therapy_areas  – sum of per-therapy-area mean of maturity_weight
    4.  w_geo                    – geographic weight from primary_region tier
                                   NOTE: reuses geo_score from trial_weight_calculator
                                   if primary_region is unavailable
    5.  w_dose                   – dosage-rank weight within (TA-I, dosage) groups
                                   NOTE: reuses dosage_score from trial_weight_calculator
                                   if dosage column is unavailable
    6.  w_sample                 – sample-size weight from drug_arm_size_n
                                   NOTE: reuses sample_score from trial_weight_calculator
                                   if drug_arm_size_n is unavailable
    6b. Non-clinical-trial override – forces w_geo, w_dose, w_sample to 1.00
                                   for rows where data_source != 'Clinical Trials'
    7.  Q_i                      – w_geo × w_sample × w_dose
    8.  e_i                      – Q_i × e_phase_i
    8b. e_phase_i                – phase × association bucket lookup
    8c. (override)                e_phase_i forced to 0.05 for non-Clinical-Trials rows
    8d. (override)                e_i forced to 1.00 when phase is Approved / 4
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
    14. Overall Coherence        – weighted coherence score across therapy areas
    15. C                        – 0.1 + 0.9 × (Overall Coherence)^1.75
    16. Final Score              – 1 + 4 × B × C

Input compatibility with trial_weight_calculator.py
------------------------------------------------------
trial_weight_calculator.py outputs a *_trial_weights.xlsx file whose columns
include everything from the original input plus:

    TA - I          therapy_area + " - " + ot_disease_name
    phase_weight    computed by trial_weight_calculator
    geo_score       computed by trial_weight_calculator  (→ used as w_geo fallback)
    sample_score    computed by trial_weight_calculator  (→ used as w_sample fallback)
    dosage_score    computed by trial_weight_calculator  (→ used as w_dose fallback)
    trial_weight    final composite weight from trial_weight_calculator

This script re-derives w_geo, w_dose, w_sample independently from the
underlying columns (primary_region, dosage, drug_arm_size_n) when they are
present, which is the preferred path. If those underlying columns are absent
or fully missing, it falls back to the pre-computed scores from
trial_weight_calculator so that the pipeline still produces valid output.

Column name differences between the two scripts
-------------------------------------------------
    trial_weight_calculator  │  calculations.py
    ─────────────────────────┼──────────────────
    geo_score                │  w_geo
    sample_score             │  w_sample
    dosage_score             │  w_dose
    trial_weight             │  (kept as-is; not overwritten)

e_phase_i lookup table
-----------------------
    Association bucket is determined by association_score:
      > 0.40            → Obvious
      0.10 <= x <= 0.40 → Indirect
      < 0.10            → Novel

    +-----------+---------+----------+-------+
    | Phase     | Obvious | Indirect | Novel |
    +-----------+---------+----------+-------+
    | Phase 1   |  0.10   |  0.10    |  0.10 |
    | Phase 2   |  0.40   |  0.35    |  0.30 |
    | Phase 3   |  0.80   |  0.65    |  0.55 |
    | Approved  |  1.00   |  1.00    |  1.00 |
    +-----------+---------+----------+-------+

    Rows where phase is missing or unrecognised receive NaN.
    Rows where association_score is missing are treated as Novel.

Indication-breadth constants
-----------------------------
    N0   = 9      (inflection point of logistic curve)
    a    = 0.40   (steepness parameter)

    L_ind(x)      = 1 / (1 + exp(-a * (x - N0)))
    B_raw_ind(x)  = (L_ind(x) - L_ind(0)) / (1 - L_ind(0))
    N_eff_ind     = sum of the effective_indications column across all rows
    B_ind         = min(1, B_raw_ind(N_eff_ind) / B_raw_ind(15))

    All three values are scalars computed once and stored identically in
    every row of the output.

Non-clinical-trial override
-----------------------------
    Column: data_source
    If data_source != "Clinical Trials" (case-insensitive, trimmed; also
    applies to missing/blank data_source), then for that row:
      - w_geo, w_dose, and w_sample are all forced to 1.00
      - e_phase_i is forced to 0.05

Usage:
    python calculations.py

    The input file path is read from the OUTPUT_FILE variable in the .env
    file located in the working directory.  The script appends
    '_trial_weights' to the stem automatically, so you can point OUTPUT_FILE
    at either the original input or the *_trial_weights.xlsx output.

Output:
    <stem>_calculated.xlsx  written alongside the input file.

.env variables:
    OUTPUT_FILE  – Path to the Excel file produced by trial_weight_calculator.py
                   (i.e. the *_trial_weights.xlsx file), OR the original input
                   file path (the script will resolve to the _trial_weights file).
    FILE         – Alternative .env key accepted for backwards-compatibility.
                   OUTPUT_FILE takes precedence if both are set.

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


def _resolve_input_path(raw_path: str) -> Path:
    """
    Accept either:
      - a *_trial_weights.xlsx path (direct output of trial_weight_calculator.py)
      - the original input path — the script will look for the corresponding
        *_trial_weights.xlsx sibling file automatically.

    Raises FileNotFoundError if neither resolves to an existing file.
    """
    p = Path(raw_path)

    # If the path already points at the _trial_weights file, use it directly.
    if p.exists():
        if p.stem.endswith("_trial_weights"):
            return p
        # The user gave the original file; derive the expected output path.
        candidate = p.with_name(p.stem + "_trial_weights.xlsx")
        if candidate.exists():
            print(
                f"  Note: INPUT_FILE resolved to trial_weights output: {candidate}"
            )
            return candidate
        # Fall back to the path as given (may be a _processed.xlsx from old workflow).
        return p

    # Path doesn't exist; try appending _trial_weights.
    candidate = p.with_name(p.stem + "_trial_weights.xlsx")
    if candidate.exists():
        print(f"  Note: INPUT_FILE resolved to trial_weights output: {candidate}")
        return candidate

    raise FileNotFoundError(
        f"Could not find input file at '{p}' or '{candidate}'. "
        "Ensure trial_weight_calculator.py has been run first."
    )


# ---------------------------------------------------------------------------
# Region-priority logic — mirrors trial_weight_calculator.py exactly
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
        if score >= 0.10:
            return 0.4
        return 0.0

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

    Note: trial_weight_calculator.py already normalises phase values
    (e.g. 'Phase IIIb' → 'Phase 3', 'Marketed' → 'Approved'), so the
    regexes here will match cleanly against those normalised labels.
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
        if re.search(r"\biv\b", text) or re.search(r"\b4\b", text):
            return 1.00
        if re.search(r"\biii\b", text) or re.search(r"\b3\b", text):
            return 0.60
        if re.search(r"\bii\b", text) or re.search(r"\b2\b", text):
            return 0.30
        if re.search(r"\bi\b", text) or re.search(r"\b1\b", text):
            return 0.10
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

    effective_indications:
        Sum of maturity_weight across ALL rows that share the same drug
        (drug_col). Drug-level aggregate broadcast back to every row of
        that drug.

    effective_therapy_areas:
        Sum of the mean maturity_weight across all therapy areas.
        Formula:
            effective_therapy_areas = sum over each TA of mean(maturity_weight within TA)

    Requires 'maturity_weight' and 'therapy_area' to already exist.
    """
    if "maturity_weight" not in df.columns:
        raise ValueError("'maturity_weight' column missing — run add_maturity_weight() first.")
    if drug_col not in df.columns:
        raise ValueError(f"Drug column '{drug_col}' not found in dataframe.")

    # effective_indications: drug-level sum of maturity_weight
    drug_sum = (
        df.groupby(drug_col, sort=False)["maturity_weight"]
        .sum()
        .rename("_drug_maturity_sum")
    )
    df = df.join(drug_sum, on=drug_col)
    df["effective_indications"] = df["_drug_maturity_sum"]
    df = df.drop(columns=["_drug_maturity_sum"])

    # effective_therapy_areas: sum of per-TA mean of maturity_weight
    if "therapy_area" not in df.columns:
        print(
            "WARNING: 'therapy_area' column not found. "
            "'effective_therapy_areas' will be NaN."
        )
        df["effective_therapy_areas"] = float("nan")
    else:
        eff_ta = (
            df.groupby("therapy_area", sort=False)["maturity_weight"]
            .mean()
            .sum()
        )
        df["effective_therapy_areas"] = eff_ta

    print(
        f"  [3] 'effective_indications' and 'effective_therapy_areas' added:\n"
        f"       effective_indications   = {df['effective_indications'].iloc[0]:.4f}\n"
        f"       effective_therapy_areas = {df['effective_therapy_areas'].iloc[0]:.4f}"
    )
    return df


# ===========================================================================
# 4. w_geo
# ===========================================================================

def add_w_geo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'w_geo' based on the geographic tier of primary_region.

      Tier 1 (US / UK / EU / EU member states)                    → 1.00
      Tier 2 (Canada / Switzerland / Australia / Japan)           → 0.85
      Tier 3 (everything else, including missing)                  → 0.65

    Fallback: if 'primary_region' is absent but 'geo_score' was already
    computed by trial_weight_calculator.py, that column is renamed to
    'w_geo' directly (values are identical).  This avoids silent 0.65
    defaults when the underlying region data was only captured at the
    earlier enrichment stage.
    """
    if "primary_region" in df.columns:
        _tier_to_weight = {1: 1.00, 2: 0.85, 3: 0.65}
        df["w_geo"] = df["primary_region"].apply(
            lambda r: _tier_to_weight[_region_tier(r)]
        )
        print(f"  [4] 'w_geo' added from primary_region.  Value counts:\n{df['w_geo'].value_counts().to_string()}")
        return df

    if "geo_score" in df.columns:
        print(
            "  [4] 'primary_region' not found; using pre-computed 'geo_score' "
            "from trial_weight_calculator.py as 'w_geo'."
        )
        df["w_geo"] = df["geo_score"]
        return df

    print("WARNING: Neither 'primary_region' nor 'geo_score' found. 'w_geo' will be 0.65 for all rows.")
    df["w_geo"] = 0.65
    return df


# ===========================================================================
# 5. w_dose
# ===========================================================================

def add_w_dose(df: pd.DataFrame, drug_col: str) -> pd.DataFrame:
    """
    Add column 'w_dose'.

    Logic:
      - Group rows by (TA-I, dosage).
      - Within each group, dense-rank rows by phase descending.
      - Rank 1 → w_dose = 1.00; rank 2+ → w_dose = 0.75.
      - Rows with missing dosage are isolated per TA-I and get w_dose = 1.00.

    The grouping key 'TA - I' is produced by trial_weight_calculator.py
    (therapy_area + " - " + ot_disease_name).  If it is absent, the script
    falls back to constructing it inline or, if neither source column exists,
    uses drug_col as the grouping key.

    Fallback: if 'dosage' is absent but 'dosage_score' was pre-computed by
    trial_weight_calculator.py, that column is used as 'w_dose' directly.
    """
    # Ensure we have a TA-I grouping column, mirroring what
    # trial_weight_calculator.py produces.
    tai_col = "TA - I"
    if tai_col not in df.columns:
        if "therapy_area" in df.columns and "ot_disease_name" in df.columns:
            df[tai_col] = (
                df["therapy_area"].astype(str) + " - " + df["ot_disease_name"].astype(str)
            )
            print(f"  [5] Constructed '{tai_col}' column from therapy_area + ot_disease_name.")
        else:
            print(
                f"  [5] WARNING: '{tai_col}' column not found and cannot be constructed. "
                f"Using '{drug_col}' as grouping key for w_dose."
            )
            tai_col = drug_col

    required_for_ranking = {"dosage", "phase", tai_col}
    missing_cols = required_for_ranking - set(df.columns)

    if missing_cols:
        if "dosage_score" in df.columns:
            print(
                f"  [5] 'dosage' or 'phase' not found (missing: {missing_cols}); "
                "using pre-computed 'dosage_score' from trial_weight_calculator.py as 'w_dose'."
            )
            df["w_dose"] = df["dosage_score"]
        else:
            print(
                f"WARNING: w_dose requires {required_for_ranking}. "
                f"Missing: {missing_cols} and no 'dosage_score' fallback found. "
                "'w_dose' will be 1.0 for all rows."
            )
            df["w_dose"] = 1.0
        return df

    _MISSING_DOSE_SENTINEL = "__missing__"

    def _norm_dose(val):
        if _is_missing(val):
            return _MISSING_DOSE_SENTINEL
        return str(val).strip().lower()

    df["_dose_key"] = df["dosage"].apply(_norm_dose)
    df["_phase_rank_num"] = df["phase"].apply(_phase_rank)

    df["_dose_rank"] = (
        df.groupby([tai_col, "_dose_key"], sort=False, dropna=False)["_phase_rank_num"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    def _dose_rank_to_weight(rank: int) -> float:
        return 1.00 if rank == 1 else 0.75

    df["w_dose"] = df["_dose_rank"].apply(_dose_rank_to_weight)
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

    Fallback: if 'drug_arm_size_n' is absent but 'sample_score' was
    pre-computed by trial_weight_calculator.py, that column is used as
    'w_sample' directly.

    Note: trial_weight_calculator uses thresholds of 50/300/500 while this
    script uses 50/200/500. When deriving from drug_arm_size_n directly the
    thresholds here (calculations.py) take precedence; the fallback to
    sample_score preserves the trial_weight_calculator thresholds unchanged.
    """
    if "drug_arm_size_n" in df.columns:
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
        print(f"  [6] 'w_sample' added from drug_arm_size_n.  Value counts:\n{df['w_sample'].value_counts().to_string()}")
        return df

    if "sample_score" in df.columns:
        print(
            "  [6] 'drug_arm_size_n' not found; using pre-computed 'sample_score' "
            "from trial_weight_calculator.py as 'w_sample'."
        )
        df["w_sample"] = df["sample_score"]
        return df

    print(
        "WARNING: Neither 'drug_arm_size_n' nor 'sample_score' found. "
        "'w_sample' will be 0.40 for all rows."
    )
    df["w_sample"] = 0.40
    return df


# ---------------------------------------------------------------------------
# Shared helper: identifies which rows are NOT from 'Clinical Trials'
# ---------------------------------------------------------------------------

def _non_clinical_trial_mask(df: pd.DataFrame):
    """
    Return a boolean Series that is True for rows where data_source is not
    'Clinical Trials' (case-insensitive, trimmed). Missing/blank data_source
    is also treated as NOT 'Clinical Trials'.

    Returns None if the 'data_source' column doesn't exist.
    """
    if "data_source" not in df.columns:
        return None

    def _is_clinical_trials(val) -> bool:
        if _is_missing(val):
            return False
        return str(val).strip().lower() == "clinical trials"

    is_ct = df["data_source"].apply(_is_clinical_trials)
    return ~is_ct


# ===========================================================================
# 6b. Non-clinical-trial overrides for w_geo, w_dose, w_sample
# ===========================================================================

def add_non_ct_overrides(df: pd.DataFrame) -> pd.DataFrame:
    """
    Override w_geo, w_dose, and w_sample to 1.00 for any row where
    data_source is not 'Clinical Trials'.

    Consistent with the behaviour of trial_weight_calculator.py, which
    also assigns fixed weights for non-CT rows.

    Requires 'w_geo', 'w_dose', 'w_sample' to already exist (steps 4-6).
    """
    required = {"w_geo", "w_dose", "w_sample"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'add_non_ct_overrides' requires {required}. Missing: {missing_cols}. "
            "Ensure steps 4, 5, and 6 have run."
        )

    non_ct_mask = _non_clinical_trial_mask(df)
    if non_ct_mask is None:
        print(
            "WARNING: 'data_source' column not found. "
            "No non-clinical-trial overrides applied."
        )
        return df

    df.loc[non_ct_mask, ["w_geo", "w_dose", "w_sample"]] = 1.00

    print(
        f"  [6b] Non-clinical-trial overrides applied (w_geo/w_dose/w_sample = 1.00).  "
        f"Rows overridden (data_source != 'Clinical Trials'): {non_ct_mask.sum()} / {len(df)}"
    )
    return df


# ===========================================================================
# 8c. Non-clinical-trial override for e_phase_i
# ===========================================================================

def add_non_ct_e_phase_override(df: pd.DataFrame) -> pd.DataFrame:
    """
    Override e_phase_i to 0.05 for any row where data_source is not
    'Clinical Trials'. Runs AFTER add_e_phase_i and BEFORE add_e_i.
    """
    if "e_phase_i" not in df.columns:
        raise ValueError(
            "'add_non_ct_e_phase_override' requires 'e_phase_i'. "
            "Ensure step 8b (add_e_phase_i) has run."
        )

    non_ct_mask = _non_clinical_trial_mask(df)
    if non_ct_mask is None:
        print(
            "WARNING: 'data_source' column not found. "
            "No non-clinical-trial e_phase_i override applied."
        )
        return df

    df.loc[non_ct_mask, "e_phase_i"] = 0.05

    print(
        f"  [8c] Non-clinical-trial override applied (e_phase_i = 0.05).  "
        f"Rows overridden (data_source != 'Clinical Trials'): {non_ct_mask.sum()} / {len(df)}"
    )
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
# 8b. e_phase_i
# ===========================================================================

_E_PHASE_TABLE = {
    ("phase1",   "obvious"):  0.10,
    ("phase1",   "indirect"): 0.10,
    ("phase1",   "novel"):    0.10,
    ("phase2",   "obvious"):  0.40,
    ("phase2",   "indirect"): 0.35,
    ("phase2",   "novel"):    0.30,
    ("phase3",   "obvious"):  0.80,
    ("phase3",   "indirect"): 0.65,
    ("phase3",   "novel"):    0.55,
    ("approved", "obvious"):  1.00,
    ("approved", "indirect"): 1.00,
    ("approved", "novel"):    1.00,
}


def _phase_bucket(val) -> "str | None":
    """
    Map a phase label to one of the four lookup-table buckets:
    'phase1', 'phase2', 'phase3', 'approved'.
    Returns None for missing or unrecognised values.

    Handles labels already normalised by trial_weight_calculator.py
    (e.g. 'Phase 3', 'Approved') as well as raw labels.
    """
    if _is_missing(val):
        return None
    text = str(val).strip().lower()
    if re.search(r"\b(approved|approv|marketed|market)\b", text):
        return "approved"
    if re.search(r"\biv\b", text) or re.search(r"\b4\b", text):
        return "approved"
    if re.search(r"\biii\b", text) or re.search(r"\b3\b", text):
        return "phase3"
    if re.search(r"\bii\b", text) or re.search(r"\b2\b", text):
        return "phase2"
    if re.search(r"\bi\b", text) or re.search(r"\b1\b", text):
        return "phase1"
    return None


def _assoc_bucket(val) -> str:
    """
    Map an association_score to one of three buckets:
      > 0.40            → 'obvious'
      0.10 <= x <= 0.40 → 'indirect'
      < 0.10 or missing → 'novel'
    """
    if _is_missing(val):
        return "novel"
    try:
        score = float(val)
    except (ValueError, TypeError):
        return "novel"
    if score > 0.40:
        return "obvious"
    if score >= 0.10:
        return "indirect"
    return "novel"


def add_e_phase_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'e_phase_i' via the phase × association bucket lookup table.

    +-----------+---------+----------+-------+
    | Phase     | Obvious | Indirect | Novel |
    +-----------+---------+----------+-------+
    | Phase 1   |  0.10   |  0.10    |  0.10 |
    | Phase 2   |  0.40   |  0.35    |  0.30 |
    | Phase 3   |  0.80   |  0.65    |  0.55 |
    | Approved  |  1.00   |  1.00    |  1.00 |
    +-----------+---------+----------+-------+

    Requires 'phase'. 'association_score' optional (missing → treated as novel).
    """
    if "phase" not in df.columns:
        print(
            "WARNING: 'phase' column not found. "
            "'e_phase_i' will be NaN for all rows."
        )
        df["e_phase_i"] = float("nan")
        return df

    if "association_score" not in df.columns:
        print(
            "WARNING: 'association_score' column not found. "
            "All rows will be treated as 'novel' for 'e_phase_i'."
        )

    def _lookup(row):
        pb = _phase_bucket(row["phase"])
        ab = _assoc_bucket(row.get("association_score"))
        if pb is None:
            return float("nan")
        return _E_PHASE_TABLE[(pb, ab)]

    df["e_phase_i"] = df.apply(_lookup, axis=1)

    print(
        f"  [8b] 'e_phase_i' added (phase × association bucket lookup).  "
        f"Value counts:\n{df['e_phase_i'].value_counts().sort_index().to_string()}"
    )
    return df


# ===========================================================================
# 8. e_i
# ===========================================================================

def add_e_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'e_i'.

      e_i = Q_i × e_phase_i

    Requires Q_i and e_phase_i to already exist.
    """
    required = {"Q_i", "e_phase_i"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'e_i' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 7 and 8b have run."
        )

    df["e_i"] = df["Q_i"] * df["e_phase_i"]
    print(
        f"  [8] 'e_i' added (Q_i × e_phase_i).  "
        f"Range: {df['e_i'].min():.4f} – {df['e_i'].max():.4f}"
    )
    return df


# ===========================================================================
# 8d. Approved-phase override for e_i
# ===========================================================================

def add_approved_e_i_override(df: pd.DataFrame) -> pd.DataFrame:
    """
    Override e_i to 1.00 for any row where phase is Approved / Phase IV / 4.
    Runs AFTER add_e_i and BEFORE add_link.
    """
    if "e_i" not in df.columns:
        raise ValueError(
            "'add_approved_e_i_override' requires 'e_i'. "
            "Ensure step 8 (add_e_i) has run."
        )
    if "phase" not in df.columns:
        print(
            "WARNING: 'phase' column not found. "
            "No approved-phase e_i override applied."
        )
        return df

    approved_mask = df["phase"].apply(_phase_bucket) == "approved"
    df.loc[approved_mask, "e_i"] = 1.00

    print(
        f"  [8d] Approved-phase override applied (e_i = 1.00).  "
        f"Rows overridden (phase == Approved/4): {approved_mask.sum()} / {len(df)}"
    )
    return df


# ===========================================================================
# 9. Link
# ===========================================================================

def add_link(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Link'.

      Link = 1 - (1 - prior) × (1 - e_i)

    Probabilistic union of prior belief and trial evidence.
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

      Link_TA = mean of Link across all rows sharing the same therapy_area.

    Therapy-area-level aggregate broadcast back to every row in that TA.
    Requires 'Link' to already exist and 'therapy_area' to be present.
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

_N0 = 9
_A  = 0.40


def _l_ind(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-_A * (x - _N0)))


def _b_raw_ind(x: float, l_ind_0: float) -> float:
    return (_l_ind(x) - l_ind_0) / (1.0 - l_ind_0)


def add_indication_breadth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add three dataset-level constant columns: L_ind, B_raw_ind, B_ind.

    Uses effective_indications (drug-level sum of maturity_weight) as the
    x parameter for the logistic curve, consistent with step 3.

    Requires 'effective_indications' and 'ot_disease_name'.
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

    x         = df["effective_indications"].iloc[0]
    n_eff_ind = df["effective_indications"].iloc[0]

    l_ind_0      = _l_ind(0)
    l_ind_x      = _l_ind(x)
    b_raw_ind_x  = _b_raw_ind(x, l_ind_0)
    b_raw_ind_n  = _b_raw_ind(n_eff_ind, l_ind_0)
    b_raw_ind_15 = _b_raw_ind(15, l_ind_0)

    if abs(b_raw_ind_15) < 1e-12:
        print("WARNING: B_raw_ind(15) is effectively zero; 'B_ind' will be set to NaN.")
        b_ind = float("nan")
    else:
        b_ind = min(1.0, b_raw_ind_n / b_raw_ind_15)

    df["L_ind"]     = l_ind_x
    df["B_raw_ind"] = b_raw_ind_x
    df["B_ind"]     = b_ind

    print(
        f"  [11] Indication-breadth columns added (dataset-level constants):\n"
        f"       N_eff_ind    = {n_eff_ind:.4f}\n"
        f"       L_ind        = {l_ind_x:.6f}\n"
        f"       B_raw_ind    = {b_raw_ind_x:.6f}\n"
        f"       B_ind        = {b_ind:.6f}"
    )
    return df


# ===========================================================================
# 12. L_TA, B_raw_TA, B_TA
# ===========================================================================

_N0_TA = 3
_A_TA  = 0.9


def _l_ta(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-_A_TA * (x - _N0_TA)))


def _b_raw_ta(x: float, l_ta_0: float) -> float:
    return (_l_ta(x) - l_ta_0) / (1.0 - l_ta_0)


def add_therapy_area_breadth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add three dataset-level constant columns: L_TA, B_raw_TA, B_TA.

    Uses effective_therapy_areas (sum of per-TA mean of maturity_weight)
    as the x parameter for the logistic curve.

    Requires 'effective_therapy_areas' and 'therapy_area'.
    """
    if "effective_therapy_areas" not in df.columns:
        raise ValueError(
            "'L_TA'/'B_raw_TA'/'B_TA' require 'effective_therapy_areas'. "
            "Ensure step 3 (add_effective_indications) has run."
        )
    if "therapy_area" not in df.columns:
        print(
            "WARNING: 'therapy_area' column not found. "
            "'L_TA', 'B_raw_TA', 'B_TA' will be set to NaN."
        )
        df["L_TA"] = df["B_raw_TA"] = df["B_TA"] = float("nan")
        return df

    x        = df["effective_therapy_areas"].iloc[0]
    n_eff_ta = df["effective_therapy_areas"].iloc[0]

    l_ta_0      = _l_ta(0)
    l_ta_x      = _l_ta(x)
    b_raw_ta_x  = _b_raw_ta(x, l_ta_0)
    b_raw_ta_n  = _b_raw_ta(n_eff_ta, l_ta_0)
    b_raw_ta_5  = _b_raw_ta(5, l_ta_0)

    if abs(b_raw_ta_5) < 1e-12:
        print("WARNING: B_raw_TA(5) is effectively zero; 'B_TA' will be set to NaN.")
        b_ta = float("nan")
    else:
        b_ta = min(1.0, b_raw_ta_n / b_raw_ta_5)

    df["L_TA"]     = l_ta_x
    df["B_raw_TA"] = b_raw_ta_x
    df["B_TA"]     = b_ta

    print(
        f"  [12] Therapy-area breadth columns added (dataset-level constants):\n"
        f"       N_eff_ta     = {n_eff_ta:.4f}\n"
        f"       L_TA         = {l_ta_x:.6f}\n"
        f"       B_raw_TA     = {b_raw_ta_x:.6f}\n"
        f"       B_TA         = {b_ta:.6f}"
    )
    return df


# ===========================================================================
# 13. B
# ===========================================================================

def add_B(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'B'.

      B = B_ind × B_TA

    Requires 'B_ind' and 'B_TA' (steps 11 and 12).
    """
    required = {"B_ind", "B_TA"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'B' calculation requires {required}. Missing: {missing_cols}. "
            "Ensure steps 11 and 12 have run."
        )

    df["B"] = df["B_ind"] * df["B_TA"]
    print(f"  [13] 'B' added (B_ind × B_TA).  Value: {df['B'].iloc[0]:.6f}")
    return df


# ===========================================================================
# 14. Overall Coherence
# ===========================================================================

def add_overall_coherence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Overall Coherence'.

      Overall Coherence = ( Σ(Wᵢ × √Lᵢ) / Σ(Wᵢ) )²

    Wᵢ = unique ot_disease_name count within therapy area i
    Lᵢ = Link_TA for therapy area i

    Dataset-level constant broadcast to every row.
    Requires 'Link_TA', 'therapy_area', 'ot_disease_name'.
    """
    required = {"Link_TA", "therapy_area", "ot_disease_name"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'Overall Coherence' requires {required}. Missing: {missing_cols}."
        )

    ta_summary = (
        df.groupby("therapy_area", sort=False)
        .agg(
            W=("ot_disease_name", "nunique"),
            L=("Link_TA", "first")
        )
        .reset_index()
    )

    ta_summary["W_sqrt_L"] = ta_summary["W"] * ta_summary["L"].clip(lower=0).pow(0.5)
    sum_w_sqrt_l = ta_summary["W_sqrt_L"].sum()
    sum_w        = ta_summary["W"].sum()

    if sum_w == 0:
        print("WARNING: Σ(Wᵢ) is zero; 'Overall Coherence' will be NaN.")
        overall_coherence = float("nan")
    else:
        overall_coherence = (sum_w_sqrt_l / sum_w) ** 2

    df["Overall Coherence"] = overall_coherence

    print(
        f"  [14] 'Overall Coherence' added (dataset-level constant):\n"
        f"       Therapy areas : {len(ta_summary)}\n"
        f"       Σ(Wᵢ)         = {sum_w}\n"
        f"       Σ(Wᵢ × √Lᵢ)  = {sum_w_sqrt_l:.6f}\n"
        f"       Overall Coherence = {overall_coherence:.6f}"
    )
    return df


# ===========================================================================
# 15. C
# ===========================================================================

def add_C(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'C'.

      C = 0.1 + 0.9 × (Overall Coherence)^1.75

    Dataset-level constant. Requires 'Overall Coherence' (step 14).
    """
    if "Overall Coherence" not in df.columns:
        raise ValueError(
            "'C' requires 'Overall Coherence'. "
            "Ensure step 14 (add_overall_coherence) has run."
        )

    overall_coherence = df["Overall Coherence"].iloc[0]
    c = 0.1 + 0.9 * (overall_coherence ** 1.75)
    df["C"] = c

    print(
        f"  [15] 'C' added:\n"
        f"       Overall Coherence = {overall_coherence:.6f}\n"
        f"       C = {c:.6f}"
    )
    return df


# ===========================================================================
# 16. Final Score
# ===========================================================================

def add_final_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add column 'Final Score'.

      Final Score = 1 + 4 × B × C

    Dataset-level constant. Requires 'B' and 'C' (steps 13 and 15).
    """
    required = {"B", "C"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"'Final Score' requires {required}. Missing: {missing_cols}. "
            "Ensure steps 13 and 15 have run."
        )

    b = df["B"].iloc[0]
    c = df["C"].iloc[0]
    final_score = 1 + 4 * b * c
    df["Final Score"] = final_score

    print(
        f"  [16] 'Final Score' added:\n"
        f"       B           = {b:.6f}\n"
        f"       C           = {c:.6f}\n"
        f"       Final Score = {final_score:.6f}"
    )
    return df


# ===========================================================================
# Main pipeline
# ===========================================================================

def run_calculations(input_path: Path) -> Path:
    """
    Load the *_trial_weights.xlsx produced by trial_weight_calculator.py,
    apply all derived-column calculations in order, and write the result to
    <stem>_calculated.xlsx alongside the input file.

    Returns the output path.
    """
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    print(f"\nLoading: {input_path}")
    df = pd.read_excel(input_path)
    print(f"  Loaded {len(df)} rows × {len(df.columns)} columns.")

    # Report which columns we inherited from trial_weight_calculator.py
    inherited = [c for c in ("geo_score", "sample_score", "dosage_score", "trial_weight", "TA - I")
                 if c in df.columns]
    if inherited:
        print(f"  Columns inherited from trial_weight_calculator: {inherited}")

    drug_col = _find_drug_column(df)
    print(f"  Drug identifier column: '{drug_col}'")

    print("\nRunning calculations ...")

    df = add_prior(df)                           # 1
    df = add_maturity_weight(df)                 # 2
    df = add_effective_indications(df, drug_col) # 3
    df = add_w_geo(df)                           # 4
    df = add_w_dose(df, drug_col)                # 5
    df = add_w_sample(df)                        # 6
    df = add_non_ct_overrides(df)                # 6b
    df = add_Q_i(df)                             # 7
    df = add_e_phase_i(df)                       # 8b
    df = add_non_ct_e_phase_override(df)         # 8c
    df = add_e_i(df)                             # 8
    df = add_approved_e_i_override(df)           # 8d
    df = add_link(df)                            # 9
    df = add_link_ta(df)                         # 10
    df = add_indication_breadth(df)              # 11
    df = add_therapy_area_breadth(df)            # 12
    df = add_B(df)                               # 13
    df = add_overall_coherence(df)               # 14
    df = add_C(df)                               # 15
    df = add_final_score(df)                     # 16

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

    # Accept OUTPUT_FILE (trial_weight_calculator convention) or FILE (legacy).
    raw_path = os.getenv("OUTPUT_FILE") or os.getenv("FILE")
    if not raw_path:
        print(
            "ERROR: No input file specified. "
            "Set OUTPUT_FILE (or FILE) in your .env to the path of the "
            "*_trial_weights.xlsx file produced by trial_weight_calculator.py."
        )
        sys.exit(1)

    try:
        input_path = _resolve_input_path(raw_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    run_calculations(input_path)
