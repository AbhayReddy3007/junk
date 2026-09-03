(cognito) C:\Users\P90022569\Downloads\LE>python opentargets.py
12:52:01  INFO      [MainThread]  📂 Reading: C:\Users\P90022569\Downloads\Book3.xlsx
12:52:01  INFO      [MainThread]  🧬 MoAs (2): ['Gastric Inhibitory Polypeptide Receptor Agonist', 'Glucagon Like Peptide 1 Receptor Agonist']
12:52:01  INFO      [MainThread]  🦠 Indications (17): ['Cardiovascular Disease', 'Hypertension', 'Dyslipidemia', 'NAFLD', 'CV Risk Reduction', 'NASH', 'Prediabetes', 'Increased Cardiovascular Risk', 'Cardiovascular Risk/Disease', 'Pre-Diabetes', 'MASH', 'Metabolic Associated Liver Disease (Malo)', 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)', 'MACE Reduction', 'Cardiovascular (Cv) Outcomes', 'Psoriatic Arthritis', 'HFpEF']
12:52:01  INFO      [MainThread]  🔧 Workers: 3  |  Batch size: 3  |  Cache: C:\Users\P90022569\Downloads\Book3_cache.json
12:52:01  INFO      [MainThread]  📦 Loaded cache from C:\Users\P90022569\Downloads\Book3_cache.json  (moas=2, indications=17)
12:52:01  INFO      [MainThread]  
── Step 1: Loading MoA targets from cache ────────────────────────
12:52:01  WARNING   [MainThread]    ⚠️  Cache has null ID for MoA 'Gastric Inhibitory Polypeptide Receptor Agonist' — querying OT search API
12:52:02  WARNING   [MainThread]      ❌ OT search could not resolve MoA 'Gastric Inhibitory Polypeptide Receptor Agonist'
12:52:02  WARNING   [MainThread]    ⚠️  Cache has null ID for MoA 'Glucagon Like Peptide 1 Receptor Agonist' — querying OT search API
12:52:02  WARNING   [MainThread]      ❌ OT search could not resolve MoA 'Glucagon Like Peptide 1 Receptor Agonist'
12:52:02  INFO      [MainThread]  
── Step 2: Loading indications from cache ────────────────────────
12:52:02  INFO      [MainThread]    💾 Cache hit 'Cardiovascular Disease' → MONDO_0004995 (cardiovascular disorder)
12:52:02  INFO      [MainThread]    💾 Cache hit 'Hypertension' → HP_0000822 (Hypertension)
12:52:02  INFO      [MainThread]    💾 Cache hit 'Dyslipidemia' → MONDO_0002525 (inherited lipid metabolism disorder)
12:52:02  INFO      [MainThread]    💾 Cache hit 'NAFLD' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
12:52:02  WARNING   [MainThread]    ⚠️  Cache has null ID for 'CV Risk Reduction' — querying OT search API
12:52:03  WARNING   [MainThread]      ❌ OT search could not resolve 'CV Risk Reduction'
12:52:03  INFO      [MainThread]    💾 Cache hit 'NASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:52:03  INFO      [MainThread]    💾 Cache hit 'Prediabetes' → MONDO_0006920 (prediabetes syndrome)
12:52:03  INFO      [MainThread]    💾 Cache hit 'Increased Cardiovascular Risk' → EFO_0000195 (metabolic syndrome)
12:52:03  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Cardiovascular Risk/Disease' — querying OT search API
12:52:03  WARNING   [MainThread]      ❌ OT search could not resolve 'Cardiovascular Risk/Disease'
12:52:03  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Pre-Diabetes' — querying OT search API
12:52:04  WARNING   [MainThread]      ❌ OT search could not resolve 'Pre-Diabetes'
12:52:04  INFO      [MainThread]    💾 Cache hit 'MASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:52:04  INFO      [MainThread]    💾 Cache hit 'Metabolic Associated Liver Disease (Malo)' → MONDO_0009556 (malonic aciduria)
12:52:04  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' — querying OT search API
12:52:05  WARNING   [MainThread]      ❌ OT search could not resolve 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)'
12:52:05  WARNING   [MainThread]    ⚠️  Cache has null ID for 'MACE Reduction' — querying OT search API
12:52:05  WARNING   [MainThread]      ❌ OT search could not resolve 'MACE Reduction'
12:52:05  WARNING   [MainThread]    ⚠️  Cache has null ID for 'Cardiovascular (Cv) Outcomes' — querying OT search API
12:52:05  WARNING   [MainThread]      ❌ OT search could not resolve 'Cardiovascular (Cv) Outcomes'
12:52:05  INFO      [MainThread]    💾 Cache hit 'Psoriatic Arthritis' → MONDO_0011849 (psoriatic arthritis)
12:52:05  WARNING   [MainThread]    ⚠️  Cache has null ID for 'HFpEF' — querying OT search API
12:52:06  WARNING   [MainThread]      ❌ OT search could not resolve 'HFpEF'
12:52:06  INFO      [MainThread]  
── Step 3: Fetching association scores ───────────────────────────
12:52:06  ERROR     [MainThread]  No valid targets resolved — cannot score.
12:52:06  INFO      [MainThread]  
── Step 4: Saving to C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
12:52:06  INFO      [MainThread]  ✅ Saved: C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
12:52:06  INFO      [MainThread]  
── Summary ───────────────────────────────────────────────────────
12:52:06  INFO      [MainThread]    MoA targets resolved : 0 / 2
12:52:06  INFO      [MainThread]    Indications resolved : 10 / 17
12:52:06  INFO      [MainThread]    Scores found         : 0 / 17
12:52:06  INFO      [MainThread]    Cache saved to       : C:\Users\P90022569\Downloads\Book3_cache.json

📊 Score results:
  Cardiovascular Disease                        N/A         (cardiovascular disorder)
  Hypertension                                  N/A         (Hypertension)
  Dyslipidemia                                  N/A         (inherited lipid metabolism disorder)
  NAFLD                                         N/A         (metabolic dysfunction-associated steatotic liver disease)
  CV Risk Reduction                             N/A         (unresolved)
  NASH                                          N/A         (metabolic dysfunction-associated steatohepatitis)
  Prediabetes                                   N/A         (prediabetes syndrome)
  Increased Cardiovascular Risk                 N/A         (metabolic syndrome)
  Cardiovascular Risk/Disease                   N/A         (unresolved)
  Pre-Diabetes                                  N/A         (unresolved)
  MASH                                          N/A         (metabolic dysfunction-associated steatohepatitis)
  Metabolic Associated Liver Disease (Malo)     N/A         (malonic aciduria)
  Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld) N/A         (unresolved)
  MACE Reduction                                N/A         (unresolved)
  Cardiovascular (Cv) Outcomes                  N/A         (unresolved)
  Psoriatic Arthritis                           N/A         (psoriatic arthritis)
  HFpEF                                         N/A         (unresolved)
