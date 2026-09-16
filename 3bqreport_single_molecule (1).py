C:\Users\P90022569\Downloads\clinical_efficacy\drl-cognito-ai\medical_potential\label_expansion_opportunity\scoring\trial_selector.py:211: FutureWarning: The behavior of DataFrame concatenation with empty or all-NA entries is deprecated. In a future version, this will no longer exclude empty or all-NA columns when determining the result dtypes. To retain the old behavior, exclude the relevant entries before the concat operation.
  df_final = pd.concat([df_trial, df_other], ignore_index=True)
[INFO] [TRIAL_SELECTOR] Computed weights for 730 row(s) (719 trial + 11 non-trial) for 'Tirzepatide'
[INFO] [TRIAL_SELECTOR] Selected 54 TA-I summary row(s)
[INFO] [SCORE_CALC] Running score calculations for 'Tirzepatide' (54 TA-I row(s))
[INFO] [SCORE_CALC] Completed for 'Tirzepatide'. Final Score = 2.5482
[ERROR] [LABEL_EXPANSION] Step 6 failed for 'Tirzepatide'
Traceback (most recent call last):
  File "C:\Users\P90022569\Downloads\clinical_efficacy\drl-cognito-ai\medical_potential\label_expansion_opportunity\label_expansion_opportunity.py", line 174, in label_expansion
    score_rows = run_score_calculation(drug_name=drug_name, push=True)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\Downloads\clinical_efficacy\drl-cognito-ai\medical_potential\label_expansion_opportunity\scoring\score_calculator.py", line 526, in run_score_calculation
    push_score_calculation(result_rows)
  File "C:\Users\P90022569\Downloads\clinical_efficacy\drl-cognito-ai\medical_potential\label_expansion_opportunity\bq_utils.py", line 356, in push_score_calculation
    errors = bq_client.insert_rows_json(table_id, insert_rows)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\cloud\bigquery\client.py", line 4010, in insert_rows_json
    response = self._call_api(
               ^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\cloud\bigquery\client.py", line 861, in _call_api
    return call()
           ^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\api_core\retry\retry_unary.py", line 294, in retry_wrapped_func
    return retry_target(
           ^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\api_core\retry\retry_unary.py", line 156, in retry_target
    next_sleep = _retry_error_helper(
                 ^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\api_core\retry\retry_base.py", line 214, in _retry_error_helper
    raise final_exc from source_exc
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\api_core\retry\retry_unary.py", line 147, in retry_target
    result = target()
             ^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\google\cloud\_http\__init__.py", line 494, in api_request
    raise exceptions.from_http_response(response)
google.api_core.exceptions.BadRequest: 400 POST https://bigquery.googleapis.com/bigquery/v2/projects/cognito-dev-380506/datasets/data_mart/tables/label_expansion_score_calculation/insertAll?prettyPrint=false: Invalid JSON payload received. Unexpected token.
association_score": NaN, "trial_weight":
                    ^
[INFO] [LABEL_EXPANSION] Pipeline complete for 'Tirzepatide': 4 indication row(s), 3 MOA mapping(s), 97 indication mapping(s), 0 score row(s)
