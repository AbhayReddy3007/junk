(cognito) C:\Users\P90022569\Downloads\LE>python opentargets.py
12:53:54  INFO      [MainThread]  📂 Reading: C:\Users\P90022569\Downloads\Book3.xlsx
12:53:54  INFO      [MainThread]  🧬 MoAs (2): ['Gastric Inhibitory Polypeptide Receptor Agonist', 'Glucagon Like Peptide 1 Receptor Agonist']
12:53:54  INFO      [MainThread]  🦠 Indications (17): ['Cardiovascular Disease', 'Hypertension', 'Dyslipidemia', 'NAFLD', 'CV Risk Reduction', 'NASH', 'Prediabetes', 'Increased Cardiovascular Risk', 'Cardiovascular Risk/Disease', 'Pre-Diabetes', 'MASH', 'Metabolic Associated Liver Disease (Malo)', 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)', 'MACE Reduction', 'Cardiovascular (Cv) Outcomes', 'Psoriatic Arthritis', 'HFpEF']
12:53:54  INFO      [MainThread]  🔧 Workers: 3  |  Batch size: 3  |  Cache: C:\Users\P90022569\Downloads\Book3_cache.json
12:53:54  INFO      [MainThread]  
── Step 1: Loading MoA targets from cache ────────────────────────
12:53:54  WARNING   [MainThread]    ⚠️  MoA 'Gastric Inhibitory Polypeptide Receptor Agonist' not in cache — querying OT search API
12:53:54  WARNING   [MainThread]      ❌ OT search could not resolve MoA 'Gastric Inhibitory Polypeptide Receptor Agonist'
12:53:54  WARNING   [MainThread]    ⚠️  MoA 'Glucagon Like Peptide 1 Receptor Agonist' not in cache — querying OT search API
12:53:55  WARNING   [MainThread]      ❌ OT search could not resolve MoA 'Glucagon Like Peptide 1 Receptor Agonist'
12:53:55  INFO      [MainThread]  
── Step 2: Loading indications from cache ────────────────────────
12:53:55  WARNING   [MainThread]    ⚠️  'Cardiovascular Disease' not in cache — querying OT search API
12:53:55  INFO      [MainThread]      ✅ OT search resolved 'Cardiovascular Disease' → MONDO_0004995 (cardiovascular disorder)
12:53:55  WARNING   [MainThread]    ⚠️  'Hypertension' not in cache — querying OT search API
12:53:56  INFO      [MainThread]      ✅ OT search resolved 'Hypertension' → HP_0000822 (Hypertension)
12:53:56  WARNING   [MainThread]    ⚠️  'Dyslipidemia' not in cache — querying OT search API
12:53:56  INFO      [MainThread]      ✅ OT search resolved 'Dyslipidemia' → MONDO_0002525 (inherited lipid metabolism disorder)
12:53:56  WARNING   [MainThread]    ⚠️  'NAFLD' not in cache — querying OT search API
12:53:57  INFO      [MainThread]      ✅ OT search resolved 'NAFLD' → MONDO_0013209 (metabolic dysfunction-associated steatotic liver disease)
12:53:57  WARNING   [MainThread]    ⚠️  'CV Risk Reduction' not in cache — querying OT search API
12:53:57  WARNING   [MainThread]      ❌ OT search could not resolve 'CV Risk Reduction'
12:53:57  WARNING   [MainThread]    ⚠️  'NASH' not in cache — querying OT search API
12:53:58  INFO      [MainThread]      ✅ OT search resolved 'NASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:53:58  WARNING   [MainThread]    ⚠️  'Prediabetes' not in cache — querying OT search API
12:53:58  INFO      [MainThread]      ✅ OT search resolved 'Prediabetes' → MONDO_0006920 (prediabetes syndrome)
12:53:58  WARNING   [MainThread]    ⚠️  'Increased Cardiovascular Risk' not in cache — querying OT search API
12:53:59  INFO      [MainThread]      ✅ OT search resolved 'Increased Cardiovascular Risk' → EFO_0000195 (metabolic syndrome)
12:53:59  WARNING   [MainThread]    ⚠️  'Cardiovascular Risk/Disease' not in cache — querying OT search API
12:53:59  WARNING   [MainThread]      ❌ OT search could not resolve 'Cardiovascular Risk/Disease'
12:53:59  WARNING   [MainThread]    ⚠️  'Pre-Diabetes' not in cache — querying OT search API
12:54:00  WARNING   [MainThread]      ❌ OT search could not resolve 'Pre-Diabetes'
12:54:00  WARNING   [MainThread]    ⚠️  'MASH' not in cache — querying OT search API
12:54:00  INFO      [MainThread]      ✅ OT search resolved 'MASH' → MONDO_0007027 (metabolic dysfunction-associated steatohepatitis)
12:54:00  WARNING   [MainThread]    ⚠️  'Metabolic Associated Liver Disease (Malo)' not in cache — querying OT search API
12:54:01  INFO      [MainThread]      ✅ OT search resolved 'Metabolic Associated Liver Disease (Malo)' → MONDO_0009556 (malonic aciduria)
12:54:01  WARNING   [MainThread]    ⚠️  'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)' not in cache — querying OT search API
12:54:01  WARNING   [MainThread]      ❌ OT search could not resolve 'Metabolic Dysfunction-Associated Steatotic Liver Disease (Masld)'
12:54:01  WARNING   [MainThread]    ⚠️  'MACE Reduction' not in cache — querying OT search API
12:54:02  WARNING   [MainThread]      ❌ OT search could not resolve 'MACE Reduction'
12:54:02  WARNING   [MainThread]    ⚠️  'Cardiovascular (Cv) Outcomes' not in cache — querying OT search API
12:54:02  WARNING   [MainThread]      ❌ OT search could not resolve 'Cardiovascular (Cv) Outcomes'
12:54:02  WARNING   [MainThread]    ⚠️  'Psoriatic Arthritis' not in cache — querying OT search API
12:54:03  INFO      [MainThread]      ✅ OT search resolved 'Psoriatic Arthritis' → MONDO_0011849 (psoriatic arthritis)
12:54:03  WARNING   [MainThread]    ⚠️  'HFpEF' not in cache — querying OT search API
12:54:03  WARNING   [MainThread]      ❌ OT search could not resolve 'HFpEF'
12:54:03  INFO      [MainThread]  
── Step 3: Fetching association scores ───────────────────────────
12:54:03  ERROR     [MainThread]  No valid targets resolved — cannot score.
12:54:03  INFO      [MainThread]  
── Step 4: Saving to C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
12:54:03  INFO      [MainThread]  ✅ Saved: C:\Users\P90022569\Downloads\BOOK3_OUTPUT.xlsx
12:54:03  INFO      [MainThread]  
── Summary ───────────────────────────────────────────────────────
12:54:03  INFO      [MainThread]    MoA targets resolved : 0 / 2
12:54:03  INFO      [MainThread]    Indications resolved : 10 / 17
12:54:03  INFO      [MainThread]    Scores found         : 0 / 17
12:54:03  INFO      [MainThread]    Cache saved to       : C:\Users\P90022569\Downloads\Book3_cache.json

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
