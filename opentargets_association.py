12:23:10  INFO      [MainThread]  📂 Reading: C:\Users\P90022569\Downloads\Book1.xlsx
12:23:11  INFO      [MainThread]  🧬 MoAs (5): ['Calcitonin Receptor (CALCR) Agonist', 'Glucagon Like Peptide 1 Receptor Agonist', 'Receptor Activity Modifying Protein 1 Activator', 'Receptor Activity Modifying Protein 2 Activator', 'Receptor Activity Modifying Protein 3 Activator']
12:23:11  INFO      [MainThread]  🦠 Indications (24): ['Cardiometabolic Risk', 'Subclinical Atherosclerosis', 'Hypertension', 'Dyslipidemia', 'Alcohol-Associated Liver Disease (ALD)', 'Liver Injury', 'Alcohol Use Disorder (AUD)', 'Liver Fibrosis', 'chronic kidney disease', 'Metabolic Bone Disease', 'cardiovascular disorder', 'Heart Disease', 'Prediabetes', 'Cardiovascular Risk Reduction', 'Dysbiosis', 'Type 2 Diabetes Mellitus (Prevention)', 'hypertriglyceridemia', 'Painful Diabetic Peripheral Neuropathy (PDPN)', 'Metabolic Dysfunction-associated Steatohepatitis (MASH)', 'Postmenopause', 'Non-Alcoholic Fatty Liver Disease (NAFLD)', 'Hepatic Impairment', 'Renal Impairment', 'Diabetic Peripheral Neuropathy (DPN)']
12:23:11  INFO      [MainThread]  🔧 Workers: 3  |  Batch size: 3  |  Cache: C:\Users\P90022569\Downloads\Book1_cache.json
12:23:11  INFO      [MainThread]  📦 Loaded cache from C:\Users\P90022569\Downloads\Book1_cache.json  (moas=5, indications=24)
12:23:11  INFO      [MainThread]  
── Step 1: Loading MoA targets from cache ────────────────────────
12:23:11  INFO      [MainThread]    💾 Cache hit MoA 'Calcitonin Receptor (CALCR) Agonist' → ENSG00000004948 (CALCR)
12:23:11  INFO      [MainThread]    💾 Cache hit MoA 'Glucagon Like Peptide 1 Receptor Agonist' → ENSG00000112164 (GLP1R)
12:23:11  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 1 Activator' → ENSG00000132329 (RAMP1)
12:23:11  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 2 Activator' → ENSG00000131477 (RAMP2)
12:23:11  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 3 Activator' → ENSG00000122679 (RAMP3)
12:23:11  INFO      [MainThread]  
── Step 2: Loading indications from cache ────────────────────────
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Cardiometabolic Risk' → EFO_0000195 (metabolic syndrome)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Subclinical Atherosclerosis' → None (None)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Hypertension' → MONDO_0005430 (early onset hypertension)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Dyslipidemia' → MONDO_0002525 (inherited lipid metabolism disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Alcohol-Associated Liver Disease (ALD)' → MONDO_0043693 (alcoholic liver diseases)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Liver Injury' → MONDO_0005154 (liver disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Alcohol Use Disorder (AUD)' → MONDO_0007079 (alcohol dependence)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Liver Fibrosis' → HP_0001395 (Hepatic fibrosis)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'chronic kidney disease' → MONDO_0005300 (chronic kidney disease)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Metabolic Bone Disease' → MONDO_0800486 (metabolic bone disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'cardiovascular disorder' → MONDO_0004995 (cardiovascular disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Heart Disease' → MONDO_0004995 (cardiovascular disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Prediabetes' → MONDO_0006920 (prediabetes syndrome)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Cardiovascular Risk Reduction' → MONDO_0004995 (cardiovascular disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Dysbiosis' → None (None)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Type 2 Diabetes Mellitus (Prevention)' → MONDO_0005148 (type 2 diabetes mellitus)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'hypertriglyceridemia' → MONDO_0005347 (hypertriglyceridemia)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Painful Diabetic Peripheral Neuropathy (PDPN)' → None (None)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Postmenopause' → None (None)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Non-Alcoholic Fatty Liver Disease (NAFLD)' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Hepatic Impairment' → MONDO_0005154 (liver disorder)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Renal Impairment' → HP_0012211 (Abnormal renal physiology)
12:23:11  INFO      [MainThread]    💾 Cache hit indication 'Diabetic Peripheral Neuropathy (DPN)' → MONDO_0006626 (diabetic neuropathy)
12:23:11  INFO      [MainThread]  
── Step 3: Fetching association scores ───────────────────────────
12:23:11  INFO      [MainThread]    Queuing 'Cardiometabolic Risk' (EFO_0000195) × 5 targets
12:23:11  WARNING   [MainThread]    Skipping 'Subclinical Atherosclerosis' — no disease ID
12:23:11  INFO      [MainThread]    Queuing 'Hypertension' (MONDO_0005430) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Dyslipidemia' (MONDO_0002525) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Alcohol-Associated Liver Disease (ALD)' (MONDO_0043693) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Liver Injury' (MONDO_0005154) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Alcohol Use Disorder (AUD)' (MONDO_0007079) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Liver Fibrosis' (HP_0001395) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'chronic kidney disease' (MONDO_0005300) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Metabolic Bone Disease' (MONDO_0800486) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'cardiovascular disorder' (MONDO_0004995) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Heart Disease' (MONDO_0004995) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Prediabetes' (MONDO_0006920) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Cardiovascular Risk Reduction' (MONDO_0004995) × 5 targets
12:23:11  WARNING   [MainThread]    Skipping 'Dysbiosis' — no disease ID
12:23:11  INFO      [MainThread]    Queuing 'Type 2 Diabetes Mellitus (Prevention)' (MONDO_0005148) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'hypertriglyceridemia' (MONDO_0005347) × 5 targets
12:23:11  WARNING   [MainThread]    Skipping 'Painful Diabetic Peripheral Neuropathy (PDPN)' — no disease ID
12:23:11  INFO      [MainThread]    Queuing 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' (MONDO_0007027) × 5 targets
12:23:11  WARNING   [MainThread]    Skipping 'Postmenopause' — no disease ID
12:23:11  INFO      [MainThread]    Queuing 'Non-Alcoholic Fatty Liver Disease (NAFLD)' (MONDO_0013209) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Hepatic Impairment' (MONDO_0005154) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Renal Impairment' (HP_0012211) × 5 targets
12:23:11  INFO      [MainThread]    Queuing 'Diabetic Peripheral Neuropathy (DPN)' (MONDO_0006626) × 5 targets
12:23:11  INFO      [score_1]      CALCR (ENSG00000004948) x 'Hypertension' -> N/A
12:23:11  INFO      [score_0]      CALCR (ENSG00000004948) x 'Cardiometabolic Risk' -> 0.0101
12:23:11  INFO      [score_2]      CALCR (ENSG00000004948) x 'Dyslipidemia' -> 0.0138
12:23:12  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Hypertension' -> N/A
12:23:12  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Cardiometabolic Risk' -> 0.2314
12:23:12  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Dyslipidemia' -> 0.0413
12:23:12  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Hypertension' -> N/A
12:23:12  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Cardiometabolic Risk' -> N/A
12:23:12  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Dyslipidemia' -> N/A
12:23:13  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Hypertension' -> N/A
12:23:13  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Cardiometabolic Risk' -> N/A
12:23:13  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Dyslipidemia' -> 0.0441
12:23:13  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Hypertension' -> N/A
12:23:13  INFO      [score_1]    -> Max score for 'Hypertension': None
12:23:13  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Cardiometabolic Risk' -> N/A
12:23:13  INFO      [score_0]    -> Max score for 'Cardiometabolic Risk': 0.2314
12:23:13  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Dyslipidemia' -> N/A
12:23:13  INFO      [score_2]    -> Max score for 'Dyslipidemia': 0.0441
12:23:14  INFO      [score_1]      CALCR (ENSG00000004948) x 'Alcohol-Associated Liver Disease (ALD)' -> 0.0037
12:23:14  INFO      [score_0]      CALCR (ENSG00000004948) x 'Liver Injury' -> 0.0242
12:23:14  INFO      [score_2]      CALCR (ENSG00000004948) x 'Alcohol Use Disorder (AUD)' -> N/A
12:23:14  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Alcohol-Associated Liver Disease (ALD)' -> 0.0113
12:23:14  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Liver Injury' -> 0.5865
12:23:14  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Alcohol Use Disorder (AUD)' -> 0.1204
12:23:15  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:23:15  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Alcohol Use Disorder (AUD)' -> N/A
12:23:15  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Liver Injury' -> 0.0608
12:23:15  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:23:15  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Alcohol Use Disorder (AUD)' -> N/A
12:23:15  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Liver Injury' -> 0.0216
12:23:16  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:23:16  INFO      [score_1]    -> Max score for 'Alcohol-Associated Liver Disease (ALD)': 0.0113
12:23:16  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Alcohol Use Disorder (AUD)' -> N/A
12:23:16  INFO      [score_2]    -> Max score for 'Alcohol Use Disorder (AUD)': 0.1204
12:23:16  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Liver Injury' -> 0.0605
12:23:16  INFO      [score_0]    -> Max score for 'Liver Injury': 0.5865
12:23:16  INFO      [score_1]      CALCR (ENSG00000004948) x 'Liver Fibrosis' -> 0.0037
12:23:16  INFO      [score_2]      CALCR (ENSG00000004948) x 'chronic kidney disease' -> 0.0048
12:23:17  INFO      [score_0]      CALCR (ENSG00000004948) x 'Metabolic Bone Disease' -> 0.6390
12:23:17  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Liver Fibrosis' -> 0.3033
12:23:17  INFO      [score_2]      GLP1R (ENSG00000112164) x 'chronic kidney disease' -> 0.4221
12:23:17  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Metabolic Bone Disease' -> 0.0903
12:23:17  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Liver Fibrosis' -> 0.0105
12:23:17  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'chronic kidney disease' -> N/A
12:23:18  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Metabolic Bone Disease' -> N/A
12:23:18  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Liver Fibrosis' -> 0.0074
12:23:18  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'chronic kidney disease' -> 0.0069
12:23:18  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Liver Fibrosis' -> N/A
12:23:18  INFO      [score_1]    -> Max score for 'Liver Fibrosis': 0.3033
12:23:18  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Metabolic Bone Disease' -> 0.0015
12:23:18  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'chronic kidney disease' -> 0.0094
12:23:18  INFO      [score_2]    -> Max score for 'chronic kidney disease': 0.4221
12:23:19  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Metabolic Bone Disease' -> N/A
12:23:19  INFO      [score_0]    -> Max score for 'Metabolic Bone Disease': 0.6390
12:23:19  INFO      [score_1]      CALCR (ENSG00000004948) x 'cardiovascular disorder' -> 0.2125
12:23:19  INFO      [score_2]      CALCR (ENSG00000004948) x 'Heart Disease' -> 0.2125
12:23:19  INFO      [score_0]      CALCR (ENSG00000004948) x 'Prediabetes' -> 0.1853
12:23:19  INFO      [score_1]      GLP1R (ENSG00000112164) x 'cardiovascular disorder' -> 0.5114
12:23:20  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Prediabetes' -> 0.3851
12:23:20  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Heart Disease' -> 0.5114
12:23:20  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Prediabetes' -> 0.1848
12:23:20  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'cardiovascular disorder' -> 0.5781
12:23:20  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Heart Disease' -> 0.5781
12:23:21  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Prediabetes' -> 0.1848
12:23:21  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'cardiovascular disorder' -> 0.0809
12:23:21  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Heart Disease' -> 0.0809
12:23:21  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Prediabetes' -> 0.1848
12:23:21  INFO      [score_0]    -> Max score for 'Prediabetes': 0.3851
12:23:21  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'cardiovascular disorder' -> 0.1060
12:23:21  INFO      [score_1]    -> Max score for 'cardiovascular disorder': 0.5781
12:23:22  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Heart Disease' -> 0.1060
12:23:22  INFO      [score_2]    -> Max score for 'Heart Disease': 0.5781
12:23:22  INFO      [score_0]      CALCR (ENSG00000004948) x 'Cardiovascular Risk Reduction' -> 0.2125
12:23:22  INFO      [score_1]      CALCR (ENSG00000004948) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.4917
12:23:22  INFO      [score_2]      CALCR (ENSG00000004948) x 'hypertriglyceridemia' -> N/A
12:23:22  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Cardiovascular Risk Reduction' -> 0.5114
12:23:22  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.7607
12:23:23  INFO      [score_2]      GLP1R (ENSG00000112164) x 'hypertriglyceridemia' -> 0.0486
12:23:23  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Cardiovascular Risk Reduction' -> 0.5781
12:23:23  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3320
12:23:23  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'hypertriglyceridemia' -> N/A
12:23:23  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Cardiovascular Risk Reduction' -> 0.0809
12:23:23  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3402
12:23:24  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'hypertriglyceridemia' -> N/A
12:23:24  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Cardiovascular Risk Reduction' -> 0.1060
12:23:24  INFO      [score_0]    -> Max score for 'Cardiovascular Risk Reduction': 0.5781
12:23:24  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3500
12:23:24  INFO      [score_1]    -> Max score for 'Type 2 Diabetes Mellitus (Prevention)': 0.7607
12:23:24  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'hypertriglyceridemia' -> N/A
12:23:24  INFO      [score_2]    -> Max score for 'hypertriglyceridemia': 0.0486
12:23:24  INFO      [score_0]      CALCR (ENSG00000004948) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.0103
12:23:24  INFO      [score_1]      CALCR (ENSG00000004948) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0109
12:23:25  INFO      [score_2]      CALCR (ENSG00000004948) x 'Hepatic Impairment' -> 0.0242
12:23:25  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.4140
12:23:25  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.5700
12:23:25  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Hepatic Impairment' -> 0.5865
12:23:25  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> N/A
12:23:25  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> N/A
12:23:26  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Hepatic Impairment' -> 0.0608
12:23:26  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.0015
12:23:26  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0015
12:23:26  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Hepatic Impairment' -> 0.0216
12:23:26  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> N/A
12:23:26  INFO      [score_0]    -> Max score for 'Metabolic Dysfunction-associated Steatohepatitis (MASH)': 0.4140
12:23:26  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0092
12:23:26  INFO      [score_1]    -> Max score for 'Non-Alcoholic Fatty Liver Disease (NAFLD)': 0.5700
12:23:27  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Hepatic Impairment' -> 0.0605
12:23:27  INFO      [score_2]    -> Max score for 'Hepatic Impairment': 0.5865
12:23:27  INFO      [score_0]      CALCR (ENSG00000004948) x 'Renal Impairment' -> 0.0106
12:23:27  INFO      [score_1]      CALCR (ENSG00000004948) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:23:27  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Renal Impairment' -> 0.0542
12:23:27  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Diabetic Peripheral Neuropathy (DPN)' -> 0.3187
12:23:28  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Renal Impairment' -> N/A
12:23:28  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:23:28  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Renal Impairment' -> 0.0050
12:23:28  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:23:29  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Renal Impairment' -> N/A
12:23:29  INFO      [score_0]    -> Max score for 'Renal Impairment': 0.0542
12:23:29  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:23:29  INFO      [score_1]    -> Max score for 'Diabetic Peripheral Neuropathy (DPN)': 0.3187
12:23:29  INFO      [MainThread]  
── Step 4: Saving to C:\Users\P90022569\Downloads\cagrilintide+semaglutide_label_expansion_OUTPUT.xlsx
12:23:29  INFO      [MainThread]  ✅ Saved: C:\Users\P90022569\Downloads\cagrilintide+semaglutide_label_expansion_OUTPUT.xlsx
12:23:29  INFO      [MainThread]  
── Summary ───────────────────────────────────────────────────────
12:23:29  INFO      [MainThread]    MoA targets resolved : 5 / 5
12:23:29  INFO      [MainThread]    Indications resolved : 20 / 24
12:23:29  INFO      [MainThread]    Scores found         : 19 / 24
12:23:29  INFO      [MainThread]    Cache saved to       : C:\Users\P90022569\Downloads\Book1_cache.json

📊 Score results:
  Cardiometabolic Risk                          0.2314      (metabolic syndrome)
  Subclinical Atherosclerosis                   N/A         (unresolved)
  Hypertension                                  N/A         (early onset hypertension)
  Dyslipidemia                                  0.0441      (inherited lipid metabolism disorder)
  Alcohol-Associated Liver Disease (ALD)        0.0113      (alcoholic liver diseases)
  Liver Injury                                  0.5865      (liver disorder)
  Alcohol Use Disorder (AUD)                    0.1204      (alcohol dependence)
  Liver Fibrosis                                0.3033      (Hepatic fibrosis)
  chronic kidney disease                        0.4221      (chronic kidney disease)
  Metabolic Bone Disease                        0.6390      (metabolic bone disorder)
  cardiovascular disorder                       0.5781      (cardiovascular disorder)
  Heart Disease                                 0.5781      (cardiovascular disorder)
  Prediabetes                                   0.3851      (prediabetes syndrome)
  Cardiovascular Risk Reduction                 0.5781      (cardiovascular disorder)
  Dysbiosis                                     N/A         (unresolved)
  Type 2 Diabetes Mellitus (Prevention)         0.7607      (type 2 diabetes mellitus)
  hypertriglyceridemia                          0.0486      (hypertriglyceridemia)
  Painful Diabetic Peripheral Neuropathy (PDPN) N/A         (unresolved)
  Metabolic Dysfunction-associated Steatohepatitis (MASH) 0.4140      (metabolic dysfunction-associated steatohepatitis)
  Postmenopause                                 N/A         (unresolved)
  Non-Alcoholic Fatty Liver Disease (NAFLD)     0.5700      (metabolic dysfunction-associated steatotic liver disease)
  Hepatic Impairment                            0.5865      (liver disorder)
  Renal Impairment                              0.0542      (Abnormal renal physiology)
  Diabetic Peripheral Neuropathy (DPN)          0.3187      (diabetic neuropathy)

(cognito) C:\Users\P90022569\Downloads\LE>python opentargets.py
12:32:14  INFO      [MainThread]  📂 Reading: C:\Users\P90022569\Downloads\Book1.xlsx
12:32:14  INFO      [MainThread]  🧬 MoAs (5): ['Calcitonin Receptor (CALCR) Agonist', 'Glucagon Like Peptide 1 Receptor Agonist', 'Receptor Activity Modifying Protein 1 Activator', 'Receptor Activity Modifying Protein 2 Activator', 'Receptor Activity Modifying Protein 3 Activator']
12:32:14  INFO      [MainThread]  🦠 Indications (24): ['Cardiometabolic Risk', 'Subclinical Atherosclerosis', 'Hypertension', 'Dyslipidemia', 'Alcohol-Associated Liver Disease (ALD)', 'Liver Injury', 'Alcohol Use Disorder (AUD)', 'Liver Fibrosis', 'chronic kidney disease', 'Metabolic Bone Disease', 'cardiovascular disorder', 'Heart Disease', 'Prediabetes', 'Cardiovascular Risk Reduction', 'Dysbiosis', 'Type 2 Diabetes Mellitus (Prevention)', 'hypertriglyceridemia', 'Painful Diabetic Peripheral Neuropathy (PDPN)', 'Metabolic Dysfunction-associated Steatohepatitis (MASH)', 'Postmenopause', 'Non-Alcoholic Fatty Liver Disease (NAFLD)', 'Hepatic Impairment', 'Renal Impairment', 'Diabetic Peripheral Neuropathy (DPN)']
12:32:14  INFO      [MainThread]  🔧 Workers: 3  |  Batch size: 3  |  Cache: C:\Users\P90022569\Downloads\Book1_cache.json
12:32:14  INFO      [MainThread]  📦 Loaded cache from C:\Users\P90022569\Downloads\Book1_cache.json  (moas=5, indications=24)
12:32:14  INFO      [MainThread]  
── Step 1: Loading MoA targets from cache ────────────────────────
12:32:14  INFO      [MainThread]    💾 Cache hit MoA 'Calcitonin Receptor (CALCR) Agonist' → ENSG00000004948 (CALCR)
12:32:14  INFO      [MainThread]    💾 Cache hit MoA 'Glucagon Like Peptide 1 Receptor Agonist' → ENSG00000112164 (GLP1R)
12:32:14  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 1 Activator' → ENSG00000132329 (RAMP1)
12:32:14  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 2 Activator' → ENSG00000131477 (RAMP2)
12:32:14  INFO      [MainThread]    💾 Cache hit MoA 'Receptor Activity Modifying Protein 3 Activator' → ENSG00000122679 (RAMP3)
12:32:14  INFO      [MainThread]  
── Step 2: Loading indications from cache ────────────────────────
12:32:14  INFO      [MainThread]    💾 Cache hit 'Cardiometabolic Risk' → EFO_0000195 (metabolic syndrome)
12:32:14  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Subclinical Atherosclerosis' — querying OT search API
12:32:15  WARNING   [MainThread]      ❌ OT search could not resolve 'Subclinical Atherosclerosis'
12:32:15  INFO      [MainThread]    💾 Cache hit 'Hypertension' → MONDO_0005430 (early onset hypertension)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Dyslipidemia' → MONDO_0002525 (inherited lipid metabolism disorder)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Alcohol-Associated Liver Disease (ALD)' → MONDO_0043693 (alcoholic liver diseases)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Liver Injury' → MONDO_0005154 (liver disorder)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Alcohol Use Disorder (AUD)' → MONDO_0007079 (alcohol dependence)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Liver Fibrosis' → HP_0001395 (Hepatic fibrosis)
12:32:15  INFO      [MainThread]    💾 Cache hit 'chronic kidney disease' → MONDO_0005300 (chronic kidney disease)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Metabolic Bone Disease' → MONDO_0800486 (metabolic bone disorder)
12:32:15  INFO      [MainThread]    💾 Cache hit 'cardiovascular disorder' → MONDO_0004995 (cardiovascular disorder)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Heart Disease' → MONDO_0004995 (cardiovascular disorder)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Prediabetes' → MONDO_0006920 (prediabetes syndrome)
12:32:15  INFO      [MainThread]    💾 Cache hit 'Cardiovascular Risk Reduction' → MONDO_0004995 (cardiovascular disorder)
12:32:15  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Dysbiosis' — querying OT search API
12:32:15  WARNING   [MainThread]      ❌ OT search could not resolve 'Dysbiosis'
12:32:15  INFO      [MainThread]    💾 Cache hit 'Type 2 Diabetes Mellitus (Prevention)' → MONDO_0005148 (type 2 diabetes mellitus)
12:32:15  INFO      [MainThread]    💾 Cache hit 'hypertriglyceridemia' → MONDO_0005347 (hypertriglyceridemia)
12:32:15  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Painful Diabetic Peripheral Neuropathy (PDPN)' — querying OT search API
12:32:16  WARNING   [MainThread]      ❌ OT search could not resolve 'Painful Diabetic Peripheral Neuropathy (PDPN)'
12:32:16  INFO      [MainThread]    💾 Cache hit 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:32:16  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Postmenopause' — querying OT search API
12:32:16  WARNING   [MainThread]      ❌ OT search could not resolve 'Postmenopause'
12:32:16  INFO      [MainThread]    💾 Cache hit 'Non-Alcoholic Fatty Liver Disease (NAFLD)' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
12:32:16  INFO      [MainThread]    💾 Cache hit 'Hepatic Impairment' → MONDO_0005154 (liver disorder)
12:32:16  INFO      [MainThread]    💾 Cache hit 'Renal Impairment' → HP_0012211 (Abnormal renal physiology)
12:32:16  INFO      [MainThread]    💾 Cache hit 'Diabetic Peripheral Neuropathy (DPN)' → MONDO_0006626 (diabetic neuropathy)
12:32:16  INFO      [MainThread]  
── Step 3: Fetching association scores ───────────────────────────
12:32:16  INFO      [MainThread]    Queuing 'Cardiometabolic Risk' (EFO_0000195) × 5 targets
12:32:16  WARNING   [MainThread]    Skipping 'Subclinical Atherosclerosis' — no disease ID
12:32:16  INFO      [MainThread]    Queuing 'Hypertension' (MONDO_0005430) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Dyslipidemia' (MONDO_0002525) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Alcohol-Associated Liver Disease (ALD)' (MONDO_0043693) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Liver Injury' (MONDO_0005154) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Alcohol Use Disorder (AUD)' (MONDO_0007079) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Liver Fibrosis' (HP_0001395) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'chronic kidney disease' (MONDO_0005300) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Metabolic Bone Disease' (MONDO_0800486) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'cardiovascular disorder' (MONDO_0004995) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Heart Disease' (MONDO_0004995) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Prediabetes' (MONDO_0006920) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Cardiovascular Risk Reduction' (MONDO_0004995) × 5 targets
12:32:16  WARNING   [MainThread]    Skipping 'Dysbiosis' — no disease ID
12:32:16  INFO      [MainThread]    Queuing 'Type 2 Diabetes Mellitus (Prevention)' (MONDO_0005148) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'hypertriglyceridemia' (MONDO_0005347) × 5 targets
12:32:16  WARNING   [MainThread]    Skipping 'Painful Diabetic Peripheral Neuropathy (PDPN)' — no disease ID
12:32:16  INFO      [MainThread]    Queuing 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' (MONDO_0007027) × 5 targets
12:32:16  WARNING   [MainThread]    Skipping 'Postmenopause' — no disease ID
12:32:16  INFO      [MainThread]    Queuing 'Non-Alcoholic Fatty Liver Disease (NAFLD)' (MONDO_0013209) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Hepatic Impairment' (MONDO_0005154) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Renal Impairment' (HP_0012211) × 5 targets
12:32:16  INFO      [MainThread]    Queuing 'Diabetic Peripheral Neuropathy (DPN)' (MONDO_0006626) × 5 targets
12:32:17  INFO      [score_2]      CALCR (ENSG00000004948) x 'Dyslipidemia' -> 0.0138
12:32:17  INFO      [score_1]      CALCR (ENSG00000004948) x 'Hypertension' -> N/A
12:32:17  INFO      [score_0]      CALCR (ENSG00000004948) x 'Cardiometabolic Risk' -> 0.0101
12:32:17  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Hypertension' -> N/A
12:32:17  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Cardiometabolic Risk' -> 0.2314
12:32:17  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Dyslipidemia' -> 0.0413
12:32:18  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Hypertension' -> N/A
12:32:18  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Cardiometabolic Risk' -> N/A
12:32:18  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Dyslipidemia' -> N/A
12:32:18  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Hypertension' -> N/A
12:32:18  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Cardiometabolic Risk' -> N/A
12:32:18  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Dyslipidemia' -> 0.0441
12:32:19  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Hypertension' -> N/A
12:32:19  INFO      [score_1]    -> Max score for 'Hypertension': None
12:32:19  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Cardiometabolic Risk' -> N/A
12:32:19  INFO      [score_0]    -> Max score for 'Cardiometabolic Risk': 0.2314
12:32:19  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Dyslipidemia' -> N/A
12:32:19  INFO      [score_2]    -> Max score for 'Dyslipidemia': 0.0441
12:32:19  INFO      [score_1]      CALCR (ENSG00000004948) x 'Alcohol-Associated Liver Disease (ALD)' -> 0.0037
12:32:19  INFO      [score_0]      CALCR (ENSG00000004948) x 'Liver Injury' -> 0.0242
12:32:19  INFO      [score_2]      CALCR (ENSG00000004948) x 'Alcohol Use Disorder (AUD)' -> N/A
12:32:19  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Alcohol-Associated Liver Disease (ALD)' -> 0.0113
12:32:20  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Liver Injury' -> 0.5865
12:32:20  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Alcohol Use Disorder (AUD)' -> 0.1204
12:32:20  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:32:20  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Liver Injury' -> 0.0608
12:32:20  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Alcohol Use Disorder (AUD)' -> N/A
12:32:21  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:32:21  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Liver Injury' -> 0.0216
12:32:21  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Alcohol Use Disorder (AUD)' -> N/A
12:32:21  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Alcohol-Associated Liver Disease (ALD)' -> N/A
12:32:21  INFO      [score_1]    -> Max score for 'Alcohol-Associated Liver Disease (ALD)': 0.0113
12:32:21  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Liver Injury' -> 0.0605
12:32:21  INFO      [score_0]    -> Max score for 'Liver Injury': 0.5865
12:32:21  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Alcohol Use Disorder (AUD)' -> N/A
12:32:21  INFO      [score_2]    -> Max score for 'Alcohol Use Disorder (AUD)': 0.1204
12:32:21  INFO      [score_1]      CALCR (ENSG00000004948) x 'Liver Fibrosis' -> 0.0037
12:32:22  INFO      [score_0]      CALCR (ENSG00000004948) x 'chronic kidney disease' -> 0.0048
12:32:22  INFO      [score_2]      CALCR (ENSG00000004948) x 'Metabolic Bone Disease' -> 0.6390
12:32:22  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Liver Fibrosis' -> 0.3033
12:32:22  INFO      [score_0]      GLP1R (ENSG00000112164) x 'chronic kidney disease' -> 0.4221
12:32:22  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Metabolic Bone Disease' -> 0.0903
12:32:22  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Liver Fibrosis' -> 0.0105
12:32:22  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'chronic kidney disease' -> N/A
12:32:23  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Metabolic Bone Disease' -> N/A
12:32:23  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Liver Fibrosis' -> 0.0074
12:32:23  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'chronic kidney disease' -> 0.0069
12:32:23  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Metabolic Bone Disease' -> 0.0015
12:32:23  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Liver Fibrosis' -> N/A
12:32:23  INFO      [score_1]    -> Max score for 'Liver Fibrosis': 0.3033
12:32:23  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'chronic kidney disease' -> 0.0094
12:32:23  INFO      [score_0]    -> Max score for 'chronic kidney disease': 0.4221
12:32:24  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Metabolic Bone Disease' -> N/A
12:32:24  INFO      [score_2]    -> Max score for 'Metabolic Bone Disease': 0.6390
12:32:24  INFO      [score_1]      CALCR (ENSG00000004948) x 'cardiovascular disorder' -> 0.2125
12:32:24  INFO      [score_0]      CALCR (ENSG00000004948) x 'Heart Disease' -> 0.2125
12:32:24  INFO      [score_2]      CALCR (ENSG00000004948) x 'Prediabetes' -> 0.1853
12:32:24  INFO      [score_1]      GLP1R (ENSG00000112164) x 'cardiovascular disorder' -> 0.5114
12:32:24  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Heart Disease' -> 0.5114
12:32:25  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Prediabetes' -> 0.3851
12:32:25  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'cardiovascular disorder' -> 0.5781
12:32:25  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Prediabetes' -> 0.1848
12:32:25  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Heart Disease' -> 0.5781
12:32:25  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'cardiovascular disorder' -> 0.0809
12:32:26  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Heart Disease' -> 0.0809
12:32:26  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Prediabetes' -> 0.1848
12:32:26  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'cardiovascular disorder' -> 0.1060
12:32:26  INFO      [score_1]    -> Max score for 'cardiovascular disorder': 0.5781
12:32:26  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Heart Disease' -> 0.1060
12:32:26  INFO      [score_0]    -> Max score for 'Heart Disease': 0.5781
12:32:26  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Prediabetes' -> 0.1848
12:32:26  INFO      [score_2]    -> Max score for 'Prediabetes': 0.3851
12:32:26  INFO      [score_1]      CALCR (ENSG00000004948) x 'Cardiovascular Risk Reduction' -> 0.2125
12:32:27  INFO      [score_0]      CALCR (ENSG00000004948) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.4917
12:32:27  INFO      [score_2]      CALCR (ENSG00000004948) x 'hypertriglyceridemia' -> N/A
12:32:27  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Cardiovascular Risk Reduction' -> 0.5114
12:32:27  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.7607
12:32:27  INFO      [score_2]      GLP1R (ENSG00000112164) x 'hypertriglyceridemia' -> 0.0486
12:32:27  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Cardiovascular Risk Reduction' -> 0.5781
12:32:27  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3320
12:32:27  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'hypertriglyceridemia' -> N/A
12:32:28  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Cardiovascular Risk Reduction' -> 0.0809
12:32:28  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'hypertriglyceridemia' -> N/A
12:32:28  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3402
12:32:28  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Cardiovascular Risk Reduction' -> 0.1060
12:32:28  INFO      [score_1]    -> Max score for 'Cardiovascular Risk Reduction': 0.5781
12:32:28  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'hypertriglyceridemia' -> N/A
12:32:28  INFO      [score_2]    -> Max score for 'hypertriglyceridemia': 0.0486
12:32:29  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Type 2 Diabetes Mellitus (Prevention)' -> 0.3500
12:32:29  INFO      [score_0]    -> Max score for 'Type 2 Diabetes Mellitus (Prevention)': 0.7607
12:32:29  INFO      [score_1]      CALCR (ENSG00000004948) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.0103
12:32:29  INFO      [score_2]      CALCR (ENSG00000004948) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0109
12:32:29  INFO      [score_0]      CALCR (ENSG00000004948) x 'Hepatic Impairment' -> 0.0242
12:32:29  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.4140
12:32:29  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.5700
12:32:29  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Hepatic Impairment' -> 0.5865
12:32:30  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> N/A
12:32:30  INFO      [score_2]      RAMP1 (ENSG00000132329) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> N/A
12:32:30  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Hepatic Impairment' -> 0.0608
12:32:30  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> 0.0015
12:32:30  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Hepatic Impairment' -> 0.0216
12:32:30  INFO      [score_2]      RAMP2 (ENSG00000131477) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0015
12:32:31  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Metabolic Dysfunction-associated Steatohepatitis (MASH)' -> N/A
12:32:31  INFO      [score_1]    -> Max score for 'Metabolic Dysfunction-associated Steatohepatitis (MASH)': 0.4140
12:32:31  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Hepatic Impairment' -> 0.0605
12:32:31  INFO      [score_0]    -> Max score for 'Hepatic Impairment': 0.5865
12:32:31  INFO      [score_2]      RAMP3 (ENSG00000122679) x 'Non-Alcoholic Fatty Liver Disease (NAFLD)' -> 0.0092
12:32:31  INFO      [score_2]    -> Max score for 'Non-Alcoholic Fatty Liver Disease (NAFLD)': 0.5700
12:32:31  INFO      [score_1]      CALCR (ENSG00000004948) x 'Renal Impairment' -> 0.0106
12:32:31  INFO      [score_0]      CALCR (ENSG00000004948) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:32:32  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Renal Impairment' -> 0.0542
12:32:32  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Diabetic Peripheral Neuropathy (DPN)' -> 0.3187
12:32:32  INFO      [score_1]      RAMP1 (ENSG00000132329) x 'Renal Impairment' -> N/A
12:32:32  INFO      [score_0]      RAMP1 (ENSG00000132329) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:32:33  INFO      [score_1]      RAMP2 (ENSG00000131477) x 'Renal Impairment' -> 0.0050
12:32:33  INFO      [score_0]      RAMP2 (ENSG00000131477) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:32:33  INFO      [score_1]      RAMP3 (ENSG00000122679) x 'Renal Impairment' -> N/A
12:32:33  INFO      [score_1]    -> Max score for 'Renal Impairment': 0.0542
12:32:33  INFO      [score_0]      RAMP3 (ENSG00000122679) x 'Diabetic Peripheral Neuropathy (DPN)' -> N/A
12:32:33  INFO      [score_0]    -> Max score for 'Diabetic Peripheral Neuropathy (DPN)': 0.3187
12:32:33  INFO      [MainThread]  
── Step 4: Saving to C:\Users\P90022569\Downloads\cagrilintide+semaglutide_label_expansion_OUTPUT.xlsx
12:32:33  INFO      [MainThread]  ✅ Saved: C:\Users\P90022569\Downloads\cagrilintide+semaglutide_label_expansion_OUTPUT.xlsx
12:32:33  INFO      [MainThread]  
── Summary ───────────────────────────────────────────────────────
12:32:33  INFO      [MainThread]    MoA targets resolved : 5 / 5
12:32:33  INFO      [MainThread]    Indications resolved : 20 / 24
12:32:33  INFO      [MainThread]    Scores found         : 19 / 24
12:32:33  INFO      [MainThread]    Cache saved to       : C:\Users\P90022569\Downloads\Book1_cache.json

📊 Score results:
  Cardiometabolic Risk                          0.2314      (metabolic syndrome)
  Subclinical Atherosclerosis                   N/A         (unresolved)
  Hypertension                                  N/A         (early onset hypertension)
  Dyslipidemia                                  0.0441      (inherited lipid metabolism disorder)
  Alcohol-Associated Liver Disease (ALD)        0.0113      (alcoholic liver diseases)
  Liver Injury                                  0.5865      (liver disorder)
  Alcohol Use Disorder (AUD)                    0.1204      (alcohol dependence)
  Liver Fibrosis                                0.3033      (Hepatic fibrosis)
  chronic kidney disease                        0.4221      (chronic kidney disease)
  Metabolic Bone Disease                        0.6390      (metabolic bone disorder)
  cardiovascular disorder                       0.5781      (cardiovascular disorder)
  Heart Disease                                 0.5781      (cardiovascular disorder)
  Prediabetes                                   0.3851      (prediabetes syndrome)
  Cardiovascular Risk Reduction                 0.5781      (cardiovascular disorder)
  Dysbiosis                                     N/A         (unresolved)
  Type 2 Diabetes Mellitus (Prevention)         0.7607      (type 2 diabetes mellitus)
  hypertriglyceridemia                          0.0486      (hypertriglyceridemia)
  Painful Diabetic Peripheral Neuropathy (PDPN) N/A         (unresolved)
  Metabolic Dysfunction-associated Steatohepatitis (MASH) 0.4140      (metabolic dysfunction-associated steatohepatitis)
  Postmenopause                                 N/A         (unresolved)
  Non-Alcoholic Fatty Liver Disease (NAFLD)     0.5700      (metabolic dysfunction-associated steatotic liver disease)
  Hepatic Impairment                            0.5865      (liver disorder)
  Renal Impairment                              0.0542      (Abnormal renal physiology)
  Diabetic Peripheral Neuropathy (DPN)          0.3187      (diabetic neuropathy)
