Step 1 done: trial_id cleaned.
Step 2 done: 'TA - I' column added.
Step 3 done: 30 lower-phase row(s) removed.
Step 4 done: 17 duplicate (TA-I, trial_id) row(s) removed.
Fetching BQ data from `cognito-dev-380506.data_mart.clinical_trials_serious_safety_data` ...
  Fetched 2539 rows from BigQuery.
Step 5 done: BQ columns joined.
  Total rows        : 47
  Matched in BQ     : 18
  Not matched in BQ : 29
  Missing primary_region           : 29
  Missing size                     : 30
  Missing drug_arm_size_n          : 29

Step 6 — Missing field summary (before fallback):
  Total rows : 47
  Missing primary_region           : 29 row(s)
  Missing size                     : 30 row(s)
  Missing drug_arm_size_n          : 29 row(s)

  29 row(s) across 16 unique trial ID(s) need fallback.
  Querying ClinicalTrials.gov for 12 NCT ID(s) ...
    [1/12] NCT04595292 ... primary_region=Turkey (Türkiye), size=80, drug_arm_size_n=80
    [2/12] NCT04262973 ...       [size fallback] NCT04262973: using total enrollment (428) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=428, drug_arm_size_n=428
    [3/12] NCT05531656 ...       [size fallback] NCT05531656: using total enrollment (540) — per-arm counts unavailable (arms=3, drug_arms=True)
primary_region=United States, size=540, drug_arm_size_n=540
    [4/12] NCT05412862 ...       [size fallback] NCT05412862: using total enrollment (280) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=United States, size=280, drug_arm_size_n=280
    [5/12] NCT05041088 ... primary_region=None, size=40, drug_arm_size_n=40
    [6/12] NCT03415178 ... primary_region=United States, size=69, drug_arm_size_n=69
    [7/12] NCT06050187 ...       [size fallback] NCT06050187: using total enrollment (20) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Middle East, size=20, drug_arm_size_n=20
    [8/12] NCT05353933 ...       [size fallback] NCT05353933: using total enrollment (66) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=66, drug_arm_size_n=66
    [9/12] NCT03134872 ...       [size fallback] NCT03134872: using total enrollment (419) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Asia-Pacific, size=419, drug_arm_size_n=419
    [10/12] NCT04411342 ... primary_region=None, size=200, drug_arm_size_n=200
    [11/12] NCT06109311 ...       [size fallback] NCT06109311: using total enrollment (546) — per-arm counts unavailable (arms=4, drug_arms=True)
primary_region=Global, size=546, drug_arm_size_n=546
    [12/12] NCT04537598 ...       [size fallback] NCT04537598: using total enrollment (60) — per-arm counts unavailable (arms=2, drug_arms=True)
primary_region=Middle East, size=60, drug_arm_size_n=60
  CT.gov filled 18 cell(s).
  6 trial(s) still missing fields → Gemini ...
    NCT05041088: missing ['primary_region']
    NCT04411342: missing ['primary_region']
    CHICTR2500105880: missing ['primary_region']
    CHICTR2600122379: missing ['primary_region']
    ACTRN12624001278527: missing ['primary_region']
    TIRZEPATIDE: missing ['primary_region']
  Sending 6 trial(s) to Gemini (batch size 5) ...
    Gemini batch 1/2: ['NCT05041088', 'NCT04411342', 'CHICTR2500105880', 'CHICTR2600122379', 'ACTRN12624001278527']
  WARNING: Gemini call failed for batch 1: HTTP Error 404: Not Found
    Gemini batch 2/2: ['TIRZEPATIDE']
  WARNING: Gemini call failed for batch 2: HTTP Error 404: Not Found
  Gemini filled 0 cell(s).

Step 6 — Missing field summary (after fallback):
  Total rows : 47
  Still missing primary_region      : 11 row(s)
  Still missing size                : 30 row(s)
  Still missing drug_arm_size_n     : 29 row(s)
  Unresolved trial IDs (still have missing fields):
    NCT05041088 — still missing: ['primary_region']
    NCT04411342 — still missing: ['primary_region']
    ChiCTR2500105880 — still missing: ['primary_region']
    ChiCTR2600122379 — still missing: ['primary_region']
    ACTRN12624001278527 — still missing: ['primary_region']
    Tirzepatide — still missing: ['primary_region']
    nan — still missing: ['primary_region']
Step 6 done.
