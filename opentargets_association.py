22:01:02  INFO      [MainThread]  📂 Reading: C:\Users\P90022569\Downloads\Book3.xlsx
22:01:03  INFO      [MainThread]  🔗 Merged 1 spelling variants into canonical indications
22:01:03  INFO      [MainThread]  🧬 MoAs (2): ['Gastric Inhibitory Polypeptide Receptor Agonist', 'Glucagon Like Peptide 1 Receptor Agonist']
22:01:03  INFO      [MainThread]  🦠 Indications (16): ['Cardiovascular Disease', 'Hypertension', 'Dyslipidemia', 'NAFLD', 'CV Risk Reduction', 'NASH', 'Prediabetes', 'Increased Cardiovascular Risk', 'Cardiovascular Risk/Disease', 'MASH', 'Metabolic Associated Liver Disease (Malo)', 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)', 'MACE Reduction', 'Cardiovascular (Cv) Outcomes', 'Psoriatic Arthritis', 'HFpEF']
22:01:03  INFO      [MainThread]  🔧 Workers: 3  |  Batch size: 3  |  Cache: C:\Users\P90022569\Downloads\Book3_cache.json
22:01:03  INFO      [MainThread]  📦 Loaded cache from C:\Users\P90022569\Downloads\Book3_cache.json  (moas=2, indications=17)
22:01:03  INFO      [MainThread]  
── Step 1: Loading MoA targets from cache ────────────────────────
22:01:03  INFO      [MainThread]    💾 Cache hit MoA 'Gastric Inhibitory Polypeptide Receptor Agonist' → ENSG00000010310 (GIPR)
22:01:03  INFO      [MainThread]    💾 Cache hit MoA 'Glucagon Like Peptide 1 Receptor Agonist' → ENSG00000112164 (GLP1R)
22:01:03  INFO      [MainThread]  
── Step 2: Loading indications from cache ────────────────────────
22:01:03  INFO      [MainThread]    💾 Cache hit 'Cardiovascular Disease' → MONDO_0004995 (cardiovascular disorder)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Hypertension' → HP_0000822 (Hypertension)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Dyslipidemia' → MONDO_0002525 (inherited lipid metabolism disorder)
22:01:03  INFO      [MainThread]    💾 Cache hit 'NAFLD' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
22:01:03  INFO      [MainThread]    💾 Cache hit 'CV Risk Reduction' → EFO_0007924 (tonsillectomy risk measurement)
22:01:03  INFO      [MainThread]    💾 Cache hit 'NASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Prediabetes' → MONDO_0006920 (prediabetes syndrome)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Increased Cardiovascular Risk' → EFO_0000195 (metabolic syndrome)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Cardiovascular Risk/Disease' → EFO_0000195 (metabolic syndrome)
22:01:03  INFO      [MainThread]    💾 Cache hit 'MASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Metabolic Associated Liver Disease (Malo)' → MONDO_0009556 (malonic aciduria)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
22:01:03  INFO      [MainThread]    💾 Cache hit 'MACE Reduction' → EFO_0020863 (major adverse cardiovascular event measurement)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Cardiovascular (Cv) Outcomes' → MONDO_0004995 (cardiovascular disorder)
22:01:03  INFO      [MainThread]    💾 Cache hit 'Psoriatic Arthritis' → MONDO_0011849 (psoriatic arthritis)
22:01:03  WARNING   [MainThread]    ⚠️  Cache has null ID for 'HFpEF' — querying OT search API
22:01:03  WARNING   [MainThread]      ↩ Term 'HFpEF' → no match
22:01:03  WARNING   [MainThread]      ❌ OT search could not resolve 'HFpEF'
22:01:03  INFO      [MainThread]  
── Step 3: Fetching association scores ───────────────────────────
22:01:03  INFO      [MainThread]    Queuing 'Cardiovascular Disease' (MONDO_0004995) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Hypertension' (HP_0000822) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Dyslipidemia' (MONDO_0002525) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'NAFLD' (MONDO_0013209) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'CV Risk Reduction' (EFO_0007924) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'NASH' (MONDO_0007027) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Prediabetes' (MONDO_0006920) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Increased Cardiovascular Risk' (EFO_0000195) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Cardiovascular Risk/Disease' (EFO_0000195) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'MASH' (MONDO_0007027) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Metabolic Associated Liver Disease (Malo)' (MONDO_0009556) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' (MONDO_0013209) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'MACE Reduction' (EFO_0020863) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Cardiovascular (Cv) Outcomes' (MONDO_0004995) × 2 targets
22:01:03  INFO      [MainThread]    Queuing 'Psoriatic Arthritis' (MONDO_0011849) × 2 targets
22:01:03  WARNING   [MainThread]    Skipping 'HFpEF' — no disease ID
22:01:04  INFO      [score_2]      GIPR (ENSG00000010310) x 'Dyslipidemia' -> 0.0535
22:01:04  INFO      [score_1]      GIPR (ENSG00000010310) x 'Hypertension' -> 0.3743
22:01:04  INFO      [score_0]      GIPR (ENSG00000010310) x 'Cardiovascular Disease' -> 0.4519
22:01:05  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Hypertension' -> 0.4832
22:01:05  INFO      [score_2]      GLP1R (ENSG00000112164) x 'Dyslipidemia' -> 0.0413
22:01:05  INFO      [score_1]    -> Max score for 'Hypertension': 0.4832
22:01:05  INFO      [score_2]    -> Max score for 'Dyslipidemia': 0.0535
22:01:05  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Cardiovascular Disease' -> 0.5114
22:01:05  INFO      [score_0]    -> Max score for 'Cardiovascular Disease': 0.5114
22:01:05  INFO      [score_1]      GIPR (ENSG00000010310) x 'NAFLD' -> 0.1121
22:01:05  INFO      [score_2]      GIPR (ENSG00000010310) x 'CV Risk Reduction' -> N/A
22:01:05  INFO      [score_0]      GIPR (ENSG00000010310) x 'NASH' -> 0.0915
22:01:06  INFO      [score_2]      GLP1R (ENSG00000112164) x 'CV Risk Reduction' -> N/A
22:01:06  WARNING   [score_2]    No scores for 'CV Risk Reduction' with EFO_0007924 — trying fallback disease search
22:01:06  INFO      [score_0]      GLP1R (ENSG00000112164) x 'NASH' -> 0.4140
22:01:06  INFO      [score_1]      GLP1R (ENSG00000112164) x 'NAFLD' -> 0.5700
22:01:06  INFO      [score_0]    -> Max score for 'NASH': 0.4140
22:01:06  INFO      [score_1]    -> Max score for 'NAFLD': 0.5700
22:01:06  WARNING   [score_2]    Fallback term 'CV Risk Reduction' → no OT match
22:01:06  INFO      [score_1]      GIPR (ENSG00000010310) x 'Increased Cardiovascular Risk' -> 0.1138
22:01:06  INFO      [score_0]      GIPR (ENSG00000010310) x 'Prediabetes' -> 0.0031
22:01:07  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Increased Cardiovascular Risk' -> 0.2314
22:01:07  INFO      [score_1]    -> Max score for 'Increased Cardiovascular Risk': 0.2314
22:01:07  INFO      [score_2]    Fallback term 'CV Risk' → same ID EFO_0007924 already tried, skipping
22:01:07  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Prediabetes' -> 0.3851
22:01:07  INFO      [score_0]    -> Max score for 'Prediabetes': 0.3851
22:01:07  INFO      [score_1]      GIPR (ENSG00000010310) x 'Cardiovascular Risk/Disease' -> 0.1138
22:01:07  INFO      [score_2]    Fallback term 'CV' → MONDO_0011057 (cerebrovascular disorder) — re-scoring
22:01:07  INFO      [score_0]      GIPR (ENSG00000010310) x 'MASH' -> 0.0915
22:01:08  INFO      [score_0]      GLP1R (ENSG00000112164) x 'MASH' -> 0.4140
22:01:08  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Cardiovascular Risk/Disease' -> 0.2314
22:01:08  INFO      [score_0]    -> Max score for 'MASH': 0.4140
22:01:08  INFO      [score_1]    -> Max score for 'Cardiovascular Risk/Disease': 0.2314
22:01:08  INFO      [score_2]      GIPR (ENSG00000010310) x 'CV Risk Reduction' -> 0.0064
22:01:09  INFO      [score_0]      GIPR (ENSG00000010310) x 'Metabolic Associated Liver Disease (Malo)' -> N/A
22:01:09  INFO      [score_1]      GIPR (ENSG00000010310) x 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' -> 0.1121
22:01:09  INFO      [score_2]      GLP1R (ENSG00000112164) x 'CV Risk Reduction' -> 0.4134
22:01:09  INFO      [score_2]    -> Max score for 'CV Risk Reduction': 0.4134
22:01:09  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Metabolic Associated Liver Disease (Malo)' -> N/A
22:01:09  WARNING   [score_0]    No scores for 'Metabolic Associated Liver Disease (Malo)' with MONDO_0009556 — trying fallback disease search
22:01:09  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' -> 0.5700
22:01:09  INFO      [score_1]    -> Max score for 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)': 0.5700
22:01:09  INFO      [score_2]      GIPR (ENSG00000010310) x 'MACE Reduction' -> N/A
22:01:10  INFO      [score_1]      GIPR (ENSG00000010310) x 'Cardiovascular (Cv) Outcomes' -> 0.4519
22:01:10  INFO      [score_0]    Fallback term 'Metabolic Associated Liver Disease (Malo)' → same ID MONDO_0009556 already tried, skipping
22:01:10  INFO      [score_2]      GLP1R (ENSG00000112164) x 'MACE Reduction' -> N/A
22:01:10  WARNING   [score_2]    No scores for 'MACE Reduction' with EFO_0020863 — trying fallback disease search
22:01:10  INFO      [score_0]    Fallback term 'Metabolic Associated Liver Disease' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease) — re-scoring
22:01:10  WARNING   [score_2]    Fallback term 'MACE Reduction' → no OT match
22:01:10  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Cardiovascular (Cv) Outcomes' -> 0.5114
22:01:10  INFO      [score_1]    -> Max score for 'Cardiovascular (Cv) Outcomes': 0.5114
22:01:11  INFO      [score_0]      GIPR (ENSG00000010310) x 'Metabolic Associated Liver Disease (Malo)' -> 0.1121
22:01:11  INFO      [score_2]    Fallback term 'MACE' → same ID EFO_0020863 already tried, skipping
22:01:11  INFO      [score_2]    -> Max score for 'MACE Reduction': None
22:01:11  INFO      [score_1]      GIPR (ENSG00000010310) x 'Psoriatic Arthritis' -> 0.2596
22:01:11  INFO      [score_0]      GLP1R (ENSG00000112164) x 'Metabolic Associated Liver Disease (Malo)' -> 0.5700
22:01:11  INFO      [score_0]    -> Max score for 'Metabolic Associated Liver Disease (Malo)': 0.5700
22:01:11  INFO      [score_1]      GLP1R (ENSG00000112164) x 'Psoriatic Arthritis' -> 0.2800
22:01:11  INFO      [score_1]    -> Max score for 'Psoriatic Arthritis': 0.2800
22:01:11  INFO      [MainThread]  
── Step 4: Saving to C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
22:01:12  INFO      [MainThread]  ✅ Saved: C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
22:01:12  INFO      [MainThread]  
── Summary ───────────────────────────────────────────────────────
22:01:12  INFO      [MainThread]    MoA targets resolved : 2 / 2
22:01:12  INFO      [MainThread]    Indications resolved : 15 / 16
22:01:12  INFO      [MainThread]    Scores found         : 14 / 16
22:01:12  INFO      [MainThread]    Cache saved to       : C:\Users\P90022569\Downloads\Book3_cache.json

📊 Score results:
  Cardiovascular Disease                        0.5114      (cardiovascular disorder)
  Hypertension                                  0.4832      (Hypertension)
  Dyslipidemia                                  0.0535      (inherited lipid metabolism disorder)
  NAFLD                                         0.5700      (metabolic dysfunction-associated steatotic liver disease)
  CV Risk Reduction                             0.4134      (tonsillectomy risk measurement)
  NASH                                          0.4140      (metabolic dysfunction-associated steatohepatitis)
  Prediabetes                                   0.3851      (prediabetes syndrome)  (also: Pre-Diabetes)
  Increased Cardiovascular Risk                 0.2314      (metabolic syndrome)
  Cardiovascular Risk/Disease                   0.2314      (metabolic syndrome)
  MASH                                          0.4140      (metabolic dysfunction-associated steatohepatitis)
  Metabolic Associated Liver Disease (Malo)     0.5700      (malonic aciduria)
  Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld) 0.5700      (metabolic dysfunction-associated steatotic liver disease)
  MACE Reduction                                N/A         (major adverse cardiovascular event measurement)
  Cardiovascular (Cv) Outcomes                  0.5114      (cardiovascular disorder)
  Psoriatic Arthritis                           0.2800      (psoriatic arthritis)
  HFpEF                                         N/A         (unresolved)
