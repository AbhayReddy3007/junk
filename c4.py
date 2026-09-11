Step 1 done: trial_id cleaned.
Phase values normalised.
Step 2 done: 'TA - I' column added.
  Cached 2 new non-Clinical-Trials TA-I(s).
  2 non-Clinical-Trials TA-I(s) (2 row(s)) split out — fields set to NA, skipping Steps 3-6.
Step 3 done: 30 explicitly lower-phase row(s) removed.
Step 4 done: 16 duplicate (TA-I, trial_id) row(s) removed.
  Rejoined non-CT rows. Total rows: 48
Fetching BQ data from `cognito-dev-380506.data_mart.clinical_trials_serious_safety_data` ...
  Fetched 2539 rows from BigQuery.
Step 5 done: BQ columns joined.
  Total rows        : 48
  Matched in BQ     : 19
  Not matched in BQ : 29
  Missing primary_region           : 29
  Missing size                     : 30
  Missing drug_arm_size_n          : 30
  Missing dosage                   : 29
  Detailed missing fields per trial_id after BQ join:
    primary_region: 18 unique trial(s) — ['NCT04595292', 'NCT04262973', 'NCT05531656', 'NCT05412862', 'NCT05041088', 'NCT03415178', 'NCT06050187', 'NCT05353933', 'NCT03134872', 'NCT04411342']...
    size: 19 unique trial(s) — ['NCT04595292', 'NCT04262973', 'NCT05531656', 'NCT05412862', 'NCT05041088', 'NCT03415178', 'NCT06050187', 'NCT05353933', 'NCT03134872', 'NCT04411342']...
    drug_arm_size_n: 19 unique trial(s) — ['NCT04595292', 'NCT04262973', 'NCT05531656', 'NCT05412862', 'NCT05041088', 'NCT03415178', 'NCT06050187', 'NCT05353933', 'NCT07218445', 'NCT03134872']...
    dosage: 18 unique trial(s) — ['NCT04595292', 'NCT04262973', 'NCT05531656', 'NCT05412862', 'NCT05041088', 'NCT03415178', 'NCT06050187', 'NCT05353933', 'NCT03134872', 'NCT04411342']...
  Loaded 1 cached trial(s) from C:\Users\P90022569\Downloads\BOOK3_OUTPUT_lookup_cache.json

Step 6 — Missing field summary (before fallback):
  Total rows : 48
  Missing primary_region           : 29 row(s)
  Missing size                     : 30 row(s)
  Missing drug_arm_size_n          : 30 row(s)
  Missing dosage                   : 29 row(s)

  31 row(s) across 19 unique trial ID(s) need fallback.
  Fields missing per trial:
    ACTRN12624001278527: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    ACTRN12625000071426: ['size']
    CHICTR2500105880: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    CHICTR2600122379: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT03134872: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT03415178: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04262973: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04411342: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04509674: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04537598: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04595292: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT05041088: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT05353933: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT05412862: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT05531656: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT06050187: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT06109311: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT07218445: ['drug_arm_size_n']
    TIRZEPATIDE: ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
  Querying ClinicalTrials.gov for 14 NCT ID(s) ...
    [1/14] NCT04595292 ... primary_region=Turkey (Türkiye), size=80, drug_arm_size_n=80
    [2/14] NCT04262973 ...       [size fallback] NCT04262973: using total enrollment (428) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=428, drug_arm_size_n=428
    [3/14] NCT05531656 ...       [size fallback] NCT05531656: using total enrollment (540) — per-arm counts unavailable (arms=3, drug_arms=True)
primary_region=United States, size=540, drug_arm_size_n=540
    [4/14] NCT05412862 ...       [size fallback] NCT05412862: using total enrollment (280) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=United States, size=280, drug_arm_size_n=280
    [5/14] NCT05041088 ... primary_region=None, size=40, drug_arm_size_n=40
    [6/14] NCT03415178 ... primary_region=United States, size=69, drug_arm_size_n=69
    [7/14] NCT06050187 ...       [size fallback] NCT06050187: using total enrollment (20) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Middle East, size=20, drug_arm_size_n=20
    [8/14] NCT05353933 ...       [size fallback] NCT05353933: using total enrollment (66) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=66, drug_arm_size_n=66
    [9/14] NCT07218445 ...       [size fallback] NCT07218445: using total enrollment (40) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=United States, size=40, drug_arm_size_n=40
    [10/14] NCT03134872 ...       [size fallback] NCT03134872: using total enrollment (419) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=419, drug_arm_size_n=419
    [11/14] NCT04411342 ... primary_region=None, size=200, drug_arm_size_n=200
    [12/14] NCT04509674 ... primary_region=Global, size=3260, drug_arm_size_n=3260
    [13/14] NCT06109311 ...       [size fallback] NCT06109311: using total enrollment (546) — per-arm counts unavailable (arms=4, drug_arms=True)
primary_region=Global, size=546, drug_arm_size_n=546
    [14/14] NCT04537598 ...       [size fallback] NCT04537598: using total enrollment (60) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Middle East, size=60, drug_arm_size_n=60
  CT.gov filled 65 cell(s): {'primary_region': 18, 'size': 23, 'drug_arm_size_n': 24}
  Verification after CT.gov fill:
    Missing primary_region           : 11 row(s)
    Missing size                     : 7 row(s)
    Missing drug_arm_size_n          : 6 row(s)
    Missing dosage                   : 29 row(s)
  18 trial(s) still missing fields → Gemini ...
    NCT04595292: missing ['dosage']
    NCT04262973: missing ['dosage']
    NCT05531656: missing ['dosage']
    NCT05412862: missing ['dosage']
    NCT05041088: missing ['dosage', 'primary_region']
    NCT03415178: missing ['dosage']
    NCT06050187: missing ['dosage']
    NCT05353933: missing ['dosage']
    NCT03134872: missing ['dosage']
    NCT04411342: missing ['dosage', 'primary_region']
    CHICTR2500105880: missing ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    CHICTR2600122379: missing ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    NCT04509674: missing ['dosage']
    NCT06109311: missing ['dosage']
    ACTRN12624001278527: missing ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
    ACTRN12625000071426: missing ['size']
    NCT04537598: missing ['dosage']
    TIRZEPATIDE: missing ['dosage', 'drug_arm_size_n', 'primary_region', 'size']
  Sending 18 trial(s) to Gemini (batch size 5) ...
    Gemini batch 1/4: ['NCT04595292', 'NCT04262973', 'NCT05531656', 'NCT05412862', 'NCT05041088']
  WARNING: Gemini model gemini-2.5-flash error: The read operation timed out
    Gemini batch 2/4: ['NCT03415178', 'NCT06050187', 'NCT05353933', 'NCT03134872', 'NCT04411342']
  WARNING: Unexpected Gemini response structure: 'parts'
  Raw response keys: []
    Gemini batch 3/4: ['CHICTR2500105880', 'CHICTR2600122379', 'NCT04509674', 'NCT06109311', 'ACTRN12624001278527']
    Gemini batch 4/4: ['ACTRN12625000071426', 'NCT04537598', 'TIRZEPATIDE']
  Gemini filled 4 cell(s): {'dosage': 4}

Step 6 — Missing field summary (after fallback):
  Total rows : 48
  Still missing primary_region      : 11 row(s)
  Still missing size                : 7 row(s)
  Still missing drug_arm_size_n     : 6 row(s)
  Still missing dosage              : 25 row(s)
  Unresolved trial IDs (still have missing fields):
    NCT04595292 — still missing: ['dosage']
    NCT04262973 — still missing: ['dosage']
    NCT05412862 — still missing: ['dosage']
    NCT05041088 — still missing: ['primary_region', 'dosage']
    NCT03415178 — still missing: ['dosage']
    NCT06050187 — still missing: ['dosage']
    NCT05353933 — still missing: ['dosage']
    NCT03134872 — still missing: ['dosage']
    NCT04411342 — still missing: ['primary_region', 'dosage']
    ChiCTR2500105880 — still missing: ['primary_region', 'size', 'drug_arm_size_n', 'dosage']
    ChiCTR2600122379 — still missing: ['primary_region', 'size', 'drug_arm_size_n', 'dosage']
    ACTRN12624001278527 — still missing: ['primary_region', 'size', 'drug_arm_size_n', 'dosage']
    ACTRN12625000071426 — still missing: ['size']
    NCT04537598 — still missing: ['dosage']
    Tirzepatide — still missing: ['primary_region', 'size', 'drug_arm_size_n', 'dosage']
    nan — still missing: ['primary_region', 'size', 'drug_arm_size_n', 'dosage']
Step 6 done.

Step 7 done: 7 row(s) had empty size — set to 0 (rows retained). Remaining rows: 48

Step 8 done: 24 row(s) removed by region-priority filter. Remaining rows: 24

Step 9 done: 18 row(s) removed by max-size filter. Remaining rows: 6

Output saved: C:\Users\P90022569\Downloads\BOOK3_OUTPUT_processed.xlsx

Step 10 done: 'TA-I Comparison' sheet added.
  Input TA-Is : 8
  Output TA-Is: 6
  Retained    : 6
  Removed     : 2
  New         : 0
  Removed TA-Is:
    - Cardiovascular - heart failure  [Step 3: Phase deduplication]
    - Immunology - psoriatic arthritis  [Step 3: Phase deduplication]
