(cognito) C:\Users\P90022569\Downloads\LE>python cleaning_excel.py
Input file  : C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
Output file : C:\Users\P90022569\Downloads\BOOK3_OUTPUT_processed.xlsx
Step 1 done: trial_id cleaned.
Step 2 done: 'TA - I' column added.
Step 3 done: 30 lower-phase duplicate TA - I row(s) removed. Rows tied at the highest phase were all kept.
Step 4 done: 17 duplicate (TA - I, trial_id) combination(s) removed.
Fetching BQ data from `cognito-dev-380506.data_mart.clinical_trials_serious_safety_data` ...
  Fetched 2539 rows from BigQuery.
Step 5 done: BQ columns joined (primary_region, secondary_countries, size, drug_arm_size_n).
Step 6: 32 row(s) have missing fields across 19 unique trial(s).
        Querying Gemini in batches of 2 trial(s) ...
  Batch 1/10: ['NCT04595292', 'NCT04262973']
  WARNING: Unexpected Gemini response structure: 'parts'
  Full raw response:
{
  "candidates": [
    {
      "content": {
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "groundingMetadata": {
        "searchEntryPoint": {
          "renderedContent": "<style>\n.container {\n  align-items: center;\n  border-radius: 8px;\n  display: flex;\n  font-family: Google Sans, Roboto, sans-serif;\n  font-size: 14px;\n  line-height: 20px;\n  padding: 8px 12px;\n}\n.chip {\n  display: inline-block;\n  border: solid 1px;\n  border-radius: 16px;\n  min-width: 14px;\n  padding: 5px 16px;\n  text-align: center;\n  user-select: none;\n  margin: 0 8px;\n  -webkit-tap-highlight-color: transparent;\n}\n.carousel {\n  overflow: auto;\n  scrollbar-width: none;\n  white-space: nowrap;\n  margin-right: -12px;\n}\n.headline {\n  display: flex;\n  margin-right: 4px;\n}\n.gradient-container {\n  position: relative;\n}\n.gradient {\n  position: absolute;\n  transform: translate(3px, -9px);\n  height: 36px;\n  width: 9px;\n}\n@media (prefers-color-scheme: light) {\n  .container {\n    background-color: #fafafa;\n    box-shadow: 0 0 0 1px #0000000f;\n  }\n  .headline-label {\n    color: #1f1f1f;\n  }\n  .chip {\n    background-color: #ffffff;\n    border-color: #d2d2d2;\n    color: #5e5e5e;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #f2f2f2;\n  }\n  .chip:focus {\n    background-color: #f2f2f2;\n  }\n  .chip:active {\n    background-color: #d8d8d8;\n    border-color: #b6b6b6;\n  }\n  .logo-dark {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #fafafa 15%, #fafafa00 100%);\n  }\n}\n@media (prefers-color-scheme: dark) {\n  .container {\n    background-color: #1f1f1f;\n    box-shadow: 0 0 0 1px #ffffff26;\n  }\n  .headline-label {\n    color: #fff;\n  }\n  .chip {\n    background-color: #2c2c2c;\n    border-color: #3c4043;\n    color: #fff;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #353536;\n  }\n  .chip:focus {\n    background-color: #353536;\n  }\n  .chip:active {\n    background-color: #464849;\n    border-color: #53575b;\n  }\n  .logo-light {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #1f1f1f 15%, #1f1f1f00 100%);\n  }\n}\n</style>\n<div class=\"container\">\n  <div class=\"headline\">\n    <svg class=\"logo-light\" width=\"18\" height=\"18\" viewBox=\"9 9 35 35\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M42.8622 27.0064C42.8622 25.7839 42.7525 24.6084 42.5487 23.4799H26.3109V30.1568H35.5897C35.1821 32.3041 33.9596 34.1222 32.1258 35.3448V39.6864H37.7213C40.9814 36.677 42.8622 32.2571 42.8622 27.0064V27.0064Z\" fill=\"#4285F4\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 43.8555C30.9659 43.8555 34.8687 42.3195 37.7213 39.6863L32.1258 35.3447C30.5898 36.3792 28.6306 37.0061 26.3109 37.0061C21.8282 37.0061 18.0195 33.9811 16.6559 29.906H10.9194V34.3573C13.7563 39.9841 19.5712 43.8555 26.3109 43.8555V43.8555Z\" fill=\"#34A853\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M16.6559 29.8904C16.3111 28.8559 16.1074 27.7588 16.1074 26.6146C16.1074 25.4704 16.3111 24.3733 16.6559 23.3388V18.8875H10.9194C9.74388 21.2072 9.06992 23.8247 9.06992 26.6146C9.06992 29.4045 9.74388 32.022 10.9194 34.3417L15.3864 30.8621L16.6559 29.8904V29.8904Z\" fill=\"#FBBC05\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 16.2386C28.85 16.2386 31.107 17.1164 32.9095 18.8091L37.8466 13.8719C34.853 11.082 30.9659 9.3736 26.3109 9.3736C19.5712 9.3736 13.7563 13.245 10.9194 18.8875L16.6559 23.3388C18.0195 19.2636 21.8282 16.2386 26.3109 16.2386V16.2386Z\" fill=\"#EA4335\"/>\n    </svg>\n    <svg class=\"logo-dark\" width=\"18\" height=\"18\" viewBox=\"0 0 48 48\" xmlns=\"http://www.w3.org/2000/svg\">\n      <circle cx=\"24\" cy=\"23\" fill=\"#FFF\" r=\"22\"/>\n      <path d=\"M33.76 34.26c2.75-2.56 4.49-6.37 4.49-11.26 0-.89-.08-1.84-.29-3H24.01v5.99h8.03c-.4 2.02-1.5 3.56-3.07 4.56v.75l3.91 2.97h.88z\" fill=\"#4285F4\"/>\n      <path d=\"M15.58 25.77A8.845 8.845 0 0 0 24 31.86c1.92 0 3.62-.46 4.97-1.31l4.79 3.71C31.14 36.7 27.65 38 24 38c-5.93 0-11.01-3.4-13.45-8.36l.17-1.01 4.06-2.85h.8z\" fill=\"#34A853\"/>\n      <path d=\"M15.59 20.21a8.864 8.864 0 0 0 0 5.58l-5.03 3.86c-.98-2-1.53-4.25-1.53-6.64 0-2.39.55-4.64 1.53-6.64l1-.22 3.81 2.98.22 1.08z\" fill=\"#FBBC05\"/>\n      <path d=\"M24 14.14c2.11 0 4.02.75 5.52 1.98l4.36-4.36C31.22 9.43 27.81 8 24 8c-5.93 0-11.01 3.4-13.45 8.36l5.03 3.85A8.86 8.86 0 0 1 24 14.14z\" fill=\"#EA4335\"/>\n    </svg>\n    <div class=\"gradient-container\"><div class=\"gradient\"></div></div>\n  </div>\n  <div class=\"carousel\">\n    <a class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEr6p_LlswOmUvheVw9E6VSCrFeYSbQy5_eEnDdGVCjQmuweFl2taCdI9fYr2ZPu9lbx8UvXBTDXYnP_pHBXooMy5bJ9N_2HcY6zp-3IpOCpd7NxLcFGrCcGzmPy01blua9M3KbWvKRj3htVejWTAddJCvNLavDQmSLmzLrnYCB7665TPFU0F8nQ5sWmQAr_aftaMEc7lF59Nc=\">NCT04262973 enrollment</a>\n    <a class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQElfX9XLzbvd2SbKEsRSxya5XNP4UYkQ579W2tW8IhuKYZunEpNKZqNTDYMpga457Ge_iM-f0-_oUI0vvlb0ESlLCoiTVZa3BzWKMdJdUoIQkbA6ZiQV1kXZbI35uQYV17thXPSbKgjGLCrhGWK0_-SPZMlmZeUnR-O3ySYGHs3-WIjoh28z_KaV6DLyHjipb_kikHosjMMBB4=\">NCT04595292 enrollment</a>\n    <a class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFp83TKdnCGK_FLgt32cq2RUmY6XewaAsBnh4LMb9_8uCAUx3g2JwZDLLnw_IYrXgr2oyCnsOa7adoMJIc08GB9opZjkTMSEtJntRatQVxR14pm5IILBDevtCgDbtcWJi1bbBegT9TCGGPnVqkqN9f8GG2lUkv00niWPqE3GMYfMzCcowPOCiCseexZUOMwvsxeAkKOpwTiCQJKEL8=\">NCT04595292 drug arm size</a>\n    <a class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEusoNwkgJlTKRxats38p7qqUK_HQVW4HonMMeqzNToL5UnpGg4nLIPQzYhdZSGBkDqIpttcbJeSKUtoJCQdSVzjHAs-g3u3qJS6tYrfZDtnVpivIm9NV7COmG6KQp5mT1UI9ZnhwmK-oW_EcH4ifaiNVwPDov07izn8QTKf4cnzF61rlPyo7wc-2tvpB-otREWHPTGHZd9Od7XOnk=\">NCT04262973 drug arm size</a>\n  </div>\n</div>\n"
        },
        "webSearchQueries": [
          "NCT04595292 clinical trial details",
          "NCT04595292 locations",
          "NCT04595292 enrollment",
          "NCT04595292 arms",
          "NCT04262973 clinical trial details",
          "NCT04262973 locations",
          "NCT04262973 enrollment",
          "NCT04262973 arms",
          "NCT04595292 enrollment",
          "NCT04595292 drug arm size",
          "NCT04262973 enrollment",
          "NCT04262973 drug arm size"
        ]
      }
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 309,
    "candidatesTokenCount": 182,
    "totalTokenCount": 3999,
    "cachedContentTokenCount": 2508,
    "promptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 309
      }
    ],
    "cacheTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 2508
      }
    ],
    "toolUsePromptTokenCount": 2407,
    "toolUsePromptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 2407
      }
    ],
    "thoughtsTokenCount": 1101,
    "serviceTier": "standard"
  },
  "modelVersion": "gemini-2.5-flash",
  "responseId": "yE6ZauCdM4TFg8UP5ujFcA"
}
  Batch 2/10: ['NCT03987919', 'NCT05531656']
  Batch 3/10: ['NCT05412862', 'NCT05041088']
  Batch 4/10: ['NCT03415178', 'NCT06050187']
  Batch 5/10: ['NCT05353933', 'NCT03134872']
  Batch 6/10: ['NCT04411342', 'ChiCTR2500105880']
  Batch 7/10: ['ChiCTR2600122379', 'NCT06109311']
  Batch 8/10: ['ACTRN12624001278527', 'ACTRN12625000071426']
  Batch 9/10: ['NCT04537598', 'Tirzepatide']
  WARNING: Unexpected Gemini response structure: 'parts'
  Full raw response:
{
  "candidates": [
    {
      "content": {
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "groundingMetadata": {
        "searchEntryPoint": {
          "renderedContent": "<style>\n.container {\n  align-items: center;\n  border-radius: 8px;\n  display: flex;\n  font-family: Google Sans, Roboto, sans-serif;\n  font-size: 14px;\n  line-height: 20px;\n  padding: 8px 12px;\n}\n.chip {\n  display: inline-block;\n  border: solid 1px;\n  border-radius: 16px;\n  min-width: 14px;\n  padding: 5px 16px;\n  text-align: center;\n  user-select: none;\n  margin: 0 8px;\n  -webkit-tap-highlight-color: transparent;\n}\n.carousel {\n  overflow: auto;\n  scrollbar-width: none;\n  white-space: nowrap;\n  margin-right: -12px;\n}\n.headline {\n  display: flex;\n  margin-right: 4px;\n}\n.gradient-container {\n  position: relative;\n}\n.gradient {\n  position: absolute;\n  transform: translate(3px, -9px);\n  height: 36px;\n  width: 9px;\n}\n@media (prefers-color-scheme: light) {\n  .container {\n    background-color: #fafafa;\n    box-shadow: 0 0 0 1px #0000000f;\n  }\n  .headline-label {\n    color: #1f1f1f;\n  }\n  .chip {\n    background-color: #ffffff;\n    border-color: #d2d2d2;\n    color: #5e5e5e;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #f2f2f2;\n  }\n  .chip:focus {\n    background-color: #f2f2f2;\n  }\n  .chip:active {\n    background-color: #d8d8d8;\n    border-color: #b6b6b6;\n  }\n  .logo-dark {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #fafafa 15%, #fafafa00 100%);\n  }\n}\n@media (prefers-color-scheme: dark) {\n  .container {\n    background-color: #1f1f1f;\n    box-shadow: 0 0 0 1px #ffffff26;\n  }\n  .headline-label {\n    color: #fff;\n  }\n  .chip {\n    background-color: #2c2c2c;\n    border-color: #3c4043;\n    color: #fff;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #353536;\n  }\n  .chip:focus {\n    background-color: #353536;\n  }\n  .chip:active {\n    background-color: #464849;\n    border-color: #53575b;\n  }\n  .logo-light {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #1f1f1f 15%, #1f1f1f00 100%);\n  }\n}\n</style>\n<div class=\"container\">\n  <div class=\"headline\">\n    <svg class=\"logo-light\" width=\"18\" height=\"18\" viewBox=\"9 9 35 35\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M42.8622 27.0064C42.8622 25.7839 42.7525 24.6084 42.5487 23.4799H26.3109V30.1568H35.5897C35.1821 32.3041 33.9596 34.1222 32.1258 35.3448V39.6864H37.7213C40.9814 36.677 42.8622 32.2571 42.8622 27.0064V27.0064Z\" fill=\"#4285F4\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 43.8555C30.9659 43.8555 34.8687 42.3195 37.7213 39.6863L32.1258 35.3447C30.5898 36.3792 28.6306 37.0061 26.3109 37.0061C21.8282 37.0061 18.0195 33.9811 16.6559 29.906H10.9194V34.3573C13.7563 39.9841 19.5712 43.8555 26.3109 43.8555V43.8555Z\" fill=\"#34A853\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M16.6559 29.8904C16.3111 28.8559 16.1074 27.7588 16.1074 26.6146C16.1074 25.4704 16.3111 24.3733 16.6559 23.3388V18.8875H10.9194C9.74388 21.2072 9.06992 23.8247 9.06992 26.6146C9.06992 29.4045 9.74388 32.022 10.9194 34.3417L15.3864 30.8621L16.6559 29.8904V29.8904Z\" fill=\"#FBBC05\"/>\n      <path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 16.2386C28.85 16.2386 31.107 17.1164 32.9095 18.8091L37.8466 13.8719C34.853 11.082 30.9659 9.3736 26.3109 9.3736C19.5712 9.3736 13.7563 13.245 10.9194 18.8875L16.6559 23.3388C18.0195 19.2636 21.8282 16.2386 26.3109 16.2386V16.2386Z\" fill=\"#EA4335\"/>\n    </svg>\n    <svg class=\"logo-dark\" width=\"18\" height=\"18\" viewBox=\"0 0 48 48\" xmlns=\"http://www.w3.org/2000/svg\">\n      <circle cx=\"24\" cy=\"23\" fill=\"#FFF\" r=\"22\"/>\n      <path d=\"M33.76 34.26c2.75-2.56 4.49-6.37 4.49-11.26 0-.89-.08-1.84-.29-3H24.01v5.99h8.03c-.4 2.02-1.5 3.56-3.07 4.56v.75l3.91 2.97h.88z\" fill=\"#4285F4\"/>\n      <path d=\"M15.58 25.77A8.845 8.845 0 0 0 24 31.86c1.92 0 3.62-.46 4.97-1.31l4.79 3.71C31.14 36.7 27.65 38 24 38c-5.93 0-11.01-3.4-13.45-8.36l.17-1.01 4.06-2.85h.8z\" fill=\"#34A853\"/>\n      <path d=\"M15.59 20.21a8.864 8.864 0 0 0 0 5.58l-5.03 3.86c-.98-2-1.53-4.25-1.53-6.64 0-2.39.55-4.64 1.53-6.64l1-.22 3.81 2.98.22 1.08z\" fill=\"#FBBC05\"/>\n      <path d=\"M24 14.14c2.11 0 4.02.75 5.52 1.98l4.36-4.36C31.22 9.43 27.81 8 24 8c-5.93 0-11.01 3.4-13.45 8.36l5.03 3.85A8.86 8.86 0 0 1 24 14.14z\" fill=\"#EA4335\"/>\n    </svg>\n    <div class=\"gradient-container\"><div class=\"gradient\"></div></div>\n  </div>\n  <div class=\"carousel\">\n    <a class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEGFnpB_QO88Cm6vm7SwdelMwbSGxVvgjTQGyA0yN9vzQ-HhjgZCmW62tYPMS2bTXUgBH1AZrJrgtEZLalRpg3B9Xy0JtRjog5ltsxhsJr5YuupwsV4lcA7aWAem6XdtrQGXMVyvGxiVZ0YmRq55k9tgn-6QoEKTMf0D27WLvTm9uR6OGSoKPa2sNm9Olb7UK79YtcYpcl6Sg==\"> NCT04537598 location</a>\n  </div>\n</div>\n"
        },
        "webSearchQueries": [
          "NCT04537598 clinical trial details",
          "NCT04537598 enrollment",
          "NCT04537598 drug arm size",
          "NCT04537598 clinicaltrials.gov location",
          "NCT04537598 country",
          "NCT04537598 site locations",
          "NCT04537598 ClinicalTrials.gov",
          "NCT04537598 ClinicalTrials.gov study location",
          "NCT04537598 ClinicalTrials.gov page",
          " NCT04537598 location"
        ]
      }
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 304,
    "candidatesTokenCount": 210,
    "totalTokenCount": 14344,
    "promptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 304
      }
    ],
    "toolUsePromptTokenCount": 11769,
    "toolUsePromptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 11769
      }
    ],
    "thoughtsTokenCount": 2061,
    "serviceTier": "standard"
  },
  "modelVersion": "gemini-2.5-flash",
  "responseId": "TE-Zau3zO4mtg8UP_-uT8Aw"
}
  Batch 10/10: ['nan']
Step 6 done: Filled 14 cell(s) via Gemini grounded search.
Output saved: C:\Users\P90022569\Downloads\BOOK3_OUTPUT_processed.xlsx
