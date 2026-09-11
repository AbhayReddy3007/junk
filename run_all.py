Loaded 8 rows × 22 columns.
  Drug identifier column: 'molecule_name'

Running calculations ...
  [1] 'prior' added.  Value counts:
prior
0.8    4
0.4    4
  [2] 'maturity_weight' added.  Value counts:
maturity_weight
0.60    5
1.00    2
0.05    1
  [3] 'effective_indications' and 'effective_therapy_areas' added:
       effective_indications   = 5.0500 (drug-level sum of maturity_weight)
       effective_therapy_areas = 2.1833 (sum of per-TA mean of maturity_weight)
  [4] 'w_geo' added.  Value counts:
w_geo
0.65    4
1.00    3
0.85    1
Traceback (most recent call last):
  File "C:\Users\P90022569\Downloads\LE\calculations.py", line 1166, in <module>
    run_calculations(Path(file_path))
  File "C:\Users\P90022569\Downloads\LE\calculations.py", line 1131, in run_calculations
    df = add_w_dose(df, drug_col)                # 5
         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\Downloads\LE\calculations.py", line 428, in add_w_dose
    .astype(int)
     ^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\generic.py", line 6665, in astype
    new_data = self._mgr.astype(dtype=dtype, copy=copy, errors=errors)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\internals\managers.py", line 449, in astype
    return self.apply(
           ^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\internals\managers.py", line 363, in apply
    applied = getattr(b, f)(**kwargs)
              ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\internals\blocks.py", line 784, in astype
    new_values = astype_array_safe(values, dtype, copy=copy, errors=errors)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\dtypes\astype.py", line 237, in astype_array_safe
    new_values = astype_array(values, dtype, copy=copy)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\dtypes\astype.py", line 182, in astype_array
    values = _astype_nansafe(values, dtype, copy=copy)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\dtypes\astype.py", line 101, in _astype_nansafe
    return _astype_float_to_int_nansafe(arr, dtype, copy)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\P90022569\.conda\envs\cognito\Lib\site-packages\pandas\core\dtypes\astype.py", line 145, in _astype_float_to_int_nansafe
    raise IntCastingNaNError(
pandas.errors.IntCastingNaNError: Cannot convert non-finite values (NA or inf) to integer
