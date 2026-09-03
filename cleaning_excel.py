Step 6: 29 row(s) need fallback across 16 unique trial ID(s).
  Querying ClinicalTrials.gov for 12 NCT ID(s) ...
    [1/12] NCT04595292 ... primary_region=Turkey (Türkiye), size=80, drug_arm_size_n=None
    [2/12] NCT04262973 ... primary_region=Asia-Pacific, size=428, drug_arm_size_n=None
    [3/12] NCT05531656 ... primary_region=United States, size=540, drug_arm_size_n=None
    [4/12] NCT05412862 ... primary_region=United States, size=280, drug_arm_size_n=None
    [5/12] NCT05041088 ... primary_region=None, size=40, drug_arm_size_n=None
    [6/12] NCT03415178 ... primary_region=United States, size=69, drug_arm_size_n=None
    [7/12] NCT06050187 ... primary_region=Middle East / Africa, size=20, drug_arm_size_n=None
    [8/12] NCT05353933 ... primary_region=Asia-Pacific, size=66, drug_arm_size_n=None
    [9/12] NCT03134872 ... primary_region=Asia-Pacific, size=419, drug_arm_size_n=None
    [10/12] NCT04411342 ... primary_region=None, size=200, drug_arm_size_n=None
    [11/12] NCT06109311 ... primary_region=Global, size=546, drug_arm_size_n=None
    [12/12] NCT04537598 ... primary_region=Middle East / Africa, size=60, drug_arm_size_n=None
  CT.gov filled 18 cell(s).
  6 trial(s) still have missing fields → sending to Gemini ...
  Sending 6 trial(s) to Gemini (batch size 5) ...
    Gemini batch 1/2: ['NCT05041088', 'NCT04411342', 'ChiCTR2500105880', 'ChiCTR2600122379', 'ACTRN12624001278527']
  WARNING: Gemini call failed for batch 1: HTTP Error 400: Bad Request
    Gemini batch 2/2: ['Tirzepatide']
  WARNING: Gemini call failed for batch 2: HTTP Error 400: Bad Request
  Gemini filled 0 cell(s).
Traceback (most recent call last):
  File "C:\Users\P90022569\Downloads\LE\cleaning_excel.py", line 622, in <module>
    process()
  File "C:\Users\P90022569\Downloads\LE\cleaning_excel.py", line 608, in process
    df = fill_missing_fields(df, gemini_api_key, batch_size)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\Downloads\LE\cleaning_excel.py", line 477, in fill_missing_fields
    missing_ids = df.loc[needs_fill_idx[df.loc[needs_fill_idx].apply(_needs_fill, axis=1).values], "trial_id"].unique()
                         ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: only integer scalar arrays can be converted to a scalar index
