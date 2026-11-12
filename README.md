# EEG-Based Imagined Words Decoding via Multi-Scale Riemannian Manifold & Nested Adaptive GA (CS26001)

> **NIT Warangal — Course Project (Topic 6): Deep & Evolutionary Frameworks for EEG-Based Imagined Speech Decoding**  
> **Team:** Saurabh Bharrdwaj (Lead) • Badvath Jaipal • Saurabh Kumar  
> **Scope Notice:** Offline Signal-Driven BCI Research Prototype on pre-recorded 1.0 s 14-channel 128 Hz epochs (NOT a real-time clinical streaming controller or hardware DAC system).  
> **Primary Research Reference:** Lara-Arellano, E., Takacs, T. A., Tovar-Arriaga, S., & Rodriguez-Resendiz, J. (2025). *"Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram Signal Classification."* **Eng (MDPI)**, 6(4), 75. DOI: `10.3390/eng6040075`.  
> **Dataset Source:** Official Real 6-Band **EEGIS Mendeley Corpus** (DOI: `10.17632/73g4fw884c.1`) — `4,044` 1.0 s trials × 6 canonical bands (`24,264` CSVs) reconstructed from **`337` continuous 8 s (1,008-sample) recording blocks** (`overlap = 48 samples / 37.5%`, `stride = 80 samples`, `within_block_max_abs_diff = 0.0 uV`, `between_block_mean_abs_diff = 197.40 uV`). Participant IDs are absent in the distributed Mendeley archive and explicitly marked `anonymized_unrecoverable` (`subject_ids_recoverable = false`).

---

## 1. Audited Dual-Protocol Evaluation Methodology (Zero Leakage & Zero Overrides)

To eliminate split leakage and present transparent, mathematically defensible evidence, all models (`Stage 1` primary paper reproduction + classical/DL baselines and `Stage 2` MDRC-AGA) exclude ALL **9 complete `test_signals/` recording blocks (`108` overlapping sibling chunks)** from the modeling pool, leaving **`N_ref = 3,936` reference epochs across `328` disjoint 8 s blocks**, and report **both** evaluation protocols side by side:

1. **Primary Unbiased Protocol — Leakage-Safe Block-Disjoint Nested 5-Fold CV (`328` disjoint blocks, Fold 0 = 20% locked block holdout):**  
   `set(train_blocks).isdisjoint(set(test_blocks))` across every outer and inner fold (`GroupKFold`). Preprocessing, fold-fitted Riemannian tangent reference $\mathbf{C}_{\text{ref}} = \exp(\text{mean}(\log \mathbf{C}_{\text{train}}))$, scaling, `MultiScaleBlockAGA` weights, and calibration fit strictly inside outer training folds.
2. **Secondary Exploratory Protocol — Overlapping-Chunk Nested 5-Fold CV (`3,936` chunks):**  
   ***Exploratory Leakage Disclosure:*** Because Mendeley slices each 8 s recording into 12 overlapping 1 s windows (`48`-sample / `37.5%` overlap) and omits subject IDs, chunk-level CV shares temporal context across train/test splits and measures **within-block temporal memorization**, NOT unseen-block or unseen-subject generalization.

---

## 2. Stage 1 vs Stage 2 Dual-Protocol Results & Reproducible Baselines

All accuracies, balanced accuracies, Cohen's $\kappa$, block-cluster bootstrap 95% CIs, multiclass Brier scores, and 10-bin Expected Calibration Errors (ECE) are generated directly from [`baseline_paper.py`](baseline_paper.py) and [`improved_pipeline.py`](improved_pipeline.py) (`code_version = 2.0.0-audit-remediated`, zero hardcoded predictions, zero prediction overrides):

### A. 9-Class Imagined Vocabulary Benchmarks (`N_ref = 3,936`, Chance = `11.11%`)

| Architecture / Pipeline | Primary Block-Disjoint 5-CV (328 blks) | Bal. Acc / Kappa | Brier / ECE (Blk-Disj.) | Exploratory Chunk 5-CV (*Overlap Leak*) |
| :--- | :---: | :---: | :---: | :---: |
| Random Uniform Chance | 11.11% | 11.11% / 0.000 | — | 11.11% |
| Scalar 322D Moments + RBF-SVM | 10.34% `[8.54, 11.89]` | 9.87% / -0.013 | — | 19.39% |
| Scalar 322D Moments + kNN (`k=7`) | 10.16% `[8.87, 11.38]` | 9.98% / -0.012 | — | 18.22% |
| FBCSP + Calibrated SVM | 9.96% `[8.36, 11.74]` | 9.62% / -0.018 | 0.895 / 0.049 | 19.46% |
| Log-Euclidean MDM (6-Band SPD) | 8.74% `[6.63, 10.65]` | 8.82% / -0.025 | — | 16.11% |
| True Fold-Tangent LogReg (6-Band) | 10.72% `[9.55, 11.81]` | 10.58% / -0.005 | 1.474 / 0.667 | 20.78% |
| `EEGNetAttention` (PyTorch 40 ep, Fold 0) | 11.24% `[7.20, 15.15]` | 10.74% / -0.000 | 0.913 / 0.103 | 16.62% |
| **Stage 1: Paper 6B Rank-GA + kNN** | **10.01%** `[8.66, 11.46]` | 9.93% / -0.013 | 1.131 / 0.327 | **90.02%** (`k=1`, H0: 91.62%) |
| **Stage 2: MDRC-AGA `MultiMetricSoftVote`** | **10.14%** `[8.79, 11.23]` | 10.00% / -0.012 | 1.520 / 0.728 | **91.84%** (`ECE = 0.037`, H0: 93.78%) |
| **Stage 2: MDRC-AGA `CalibratedStacker`** | **9.68%** `[8.33, 10.80]` | 9.31% / -0.021 | **0.913 / 0.100** | 74.67% (`Brier = 0.418, ECE = 0.178`) |

> **Critical Audit Finding:** Across ALL architectures (classical, deep `EEGNetAttention`, FBCSP, MDM, Stage 1 GA, and Stage 2 MDRC-AGA), true cross-block generalization on `328` disjoint blocks hovers near random chance (**`8.74%–11.41%`** for 9-class and **`44.44%–49.88%`** for binary subtasks; max binary **`49.88%`** Hungry vs Thirsty, **`46.33%`** Stage 2 Stacker on Yes vs No). Meanwhile, offline 9-file format check accuracy drops cleanly from synthetic/leaked sibling matches to **`0/9 (0.0%)`** once all `108` overlapping sibling chunks of the `9` test blocks are excluded. Removing overlapping siblings reveals that the ~90–97% accuracy reported under chunk-random splits in prior literature is driven by within-block 37.5% window overlap rather than block-independent speech decoding.

### B. Binary Subtasks (`Yes vs No` Paper Task + Clinical Emergency Pairs, 5-CV)

| Binary Subtask | Block-Disjoint 5-CV (Stage 1 GA) | Block-Disjoint 5-CV (Stage 2 Stacker / Vote) | Exploratory Chunk 5-CV (Stage 1 GA) | Exploratory Chunk 5-CV (Stage 2 Stacker / Vote) |
| :--- | :---: | :---: | :---: | :---: |
| **Yes (`Sí`) vs No** (`N=900, 75 blks`) | 45.11% `[39.00, 51.23]` | **46.33%** / 44.44% | **96.11%** | 93.89% / **95.67%** |
| **Help vs Rest** (`N=936, 78 blks`) | 47.33% | **48.08%** / 47.65% | **97.12%** | 92.84% / **97.44%** |
| **Help vs Pain** (`N=972, 81 blks`) | **46.91%** | 46.40% / 46.40% | 96.19% | 93.83% / **96.50%** |
| **Hungry vs Thirsty** (`N=828, 69 blks`) | 47.34% | 44.57% / **49.88%** | 95.41% | 90.58% / **96.38%** |
| **Yes vs Help** (`N=924, 77 blks`) | **49.35%** | 47.84% / 47.29% | 96.00% | 94.37% / **96.86%** |

---

## 3. Controlled Scientific Ablations & Offline Profiling (`improved_pipeline.py`)

- **Geometry Comparison (`tangent_fold` vs `log_euclid_identity`):** Under Block-Disjoint 5-CV: Identity `10.34%` vs Fold-Tangent Vote `10.14%` / Stacker `9.68%` (Exploratory Chunk: `91.77%` vs `91.84%`). Individual Fold 0 head comparison under Block-Disjoint 5-CV spans `Calibrated_RBF_SVM = 11.41%` (`ECE = 0.022, Brier = 0.889`), `Multinomial_LogReg = 10.57%`, `Shrinkage_LDA = 10.39%`, `Weighted_Vote_3211 = 10.14%`, `Cosine_kNN_k3_Dist = 9.78%`, `Calibrated_OOF_Stacker = 9.68%` (`ECE = 0.100, Brier = 0.913`).
- **5-Seed Mutation Mode Control (Holdout Fold 0, 10 pop / 6 gen):** Block-Disjoint `fixed = 11.52% ± 0.22%`, `diversity_adaptive = 11.49% ± 0.20%`, `diversity_stagnation = 11.49% ± 0.08%` (Exploratory Chunk: `93.58% ± 0.21%`, `93.45% ± 0.13%`, `93.50% ± 0.20%`). All 1,695 dimensions remain active under 3-block scalar weighting (`active_feature_count = 1695`, mean fold weights `w = [0.8493, 0.6632, 1.4875]` block-disjoint vs `[1.2962, 0.9847, 0.7192]` exploratory chunk).
- **Mutually Exclusive vs Overlapping Fine 7-Band Splits:** Non-overlapping `[4-6, 6-8, 8-10.5, 10.5-13, 13-20, 20-30, 30-40 Hz]` yields `10.14%` block-disjoint / `91.84%` chunk vs overlapping `9.71%` block-disjoint / `92.51%` chunk.
- **Electrode Montage Topology (Fold 0):** Block-Disjoint local LogReg accuracy: `left7` (168D) `13.38%`, `all14` (630D) `12.63%`, `speech10` (330D) `11.24%`, `occipital4` (60D) `9.85%`. Exploratory Chunk Vote: `all14` `92.26%`, `speech10` `82.49%`, `left7` `60.41%`, `occipital4` `26.90%`.
- **Continuous 8 s Filtering & Window-Length Diagnostics (`328` continuous 1,008-sample blocks):**
  - *IIR Edge Transient (`filter-continuous-before-slice` vs `filter-isolated-1s`):* `edge16_mean_abs_diff = 0.0175 uV` (`max = 3.3181 uV`), `interior_mean_abs_diff = 0.2401 uV`.
  - *Continuous Window Lengths (Block-Disjoint LogReg):* `1s (128 pts)`: `11.28%` window / `11.89%` block-agg; `2s (256 pts)`: `10.26%` / `12.20%`; `4s (512 pts)`: `9.45%`; `8s (1,008 pts)`: `10.06%`.
- **Offline Per-Epoch CPU Compute Latency (`latency_breakdown` on 9 CSVs):** Load + Validate = `14.75 ms`, Preprocess = `0.04 ms`, Feature Extraction (19-view tangent) = `9.59 ms`, Classification = `7.40 ms` → **`31.77 ms` total per isolated 1 s CSV** (excludes hardware EEG acquisition/DAC loop).

---

## 4. Remediated Codebase Structure

| File / Module | Purpose & Key Audit Safeguards |
| :--- | :--- |
| [`eeg_preprocessing.py`](eeg_preprocessing.py) (+ [`src/eeg_preprocessing.py`](src/eeg_preprocessing.py)) | Single canonical ingestion & preprocessing (`14 x 128 @ 128 Hz`), unified `CANONICAL_BAND_CUTOFFS` (`8-13/13-30/30-40 Hz`), row-0 preservation on headerless CSVs, column reordering, strict rejection of `<128` samples, `NaN/Inf`, wrong channels, and non-128 Hz sampling rates. |
| [`dataset_loader.py`](dataset_loader.py) (+ [`src/dataset_loader.py`](src/dataset_loader.py)) | Audited 6-band Mendeley parser (no silent `except: continue`), explicit `anonymized_unrecoverable` subject tag, continuous 8 s overlap diagnostics, SHA-256 `.npz.meta.json` validation, `results/dataset_audit_report.json` & `results/dataset_manifest.json`. |
| [`eeg_features.py`](eeg_features.py) (+ [`src/eeg_features.py`](src/eeg_features.py)) | Fold-fitted `RiemannianTangentSpace(fit/transform)`, `MultiScaleTangentExtractor` (with fast per-trial cov precomputation), `MDMClassifier`, `FilterBankCSP`, and unified `extract_trial_features`. |
| [`models/ga_feature_selector.py`](models/ga_feature_selector.py) & [`models/aga_selector.py`](models/aga_selector.py) (+ `src/models/`) | `GroupKFold`-aware inner CV (`groups`), `PaperRankGeneticSelector`, `AdaptiveScalarGeneticSelector`, `MultiScaleBlockAGA`, `MultiMetricSoftVotingClassifier`, `CalibratedManifoldStacker`, and block-bootstrap CI + Brier/ECE metrics. |
| [`baseline_paper.py`](baseline_paper.py) & [`improved_pipeline.py`](improved_pipeline.py) | End-to-end Stage 1 & Stage 2 side-by-side nested CV suites saving `results/full4044_splits.npz`, `results/baseline_paper_metrics.json`, `results/comparison_baselines.json`, `results/improved_pipeline_metrics.json`, `results/best_improved_ensemble.pkl`. |
| [`predict.py`](predict.py) & [`eeg_gui_tester.py`](eeg_gui_tester.py) | Offline signal-driven CLI & Tkinter waveform inspector displaying calibrated posterior distributions, mismatch disclosure vs registry labels, and strict `--fs` / format validation. |
| [`compare_models.py`](compare_models.py) & [`draw_architecture.py`](draw_architecture.py) | Dynamically populated dual-protocol charts and architecture diagram reading directly from `results/*.json`. |
| [`build_nitw_12page_report.py`](build_nitw_12page_report.py) & [`build_presentation_deck.py`](build_presentation_deck.py) | Generates exact 12-page [`NITW_Topic6_Imagined_Words_Final_Report.pdf`](NITW_Topic6_Imagined_Words_Final_Report.pdf), `.docx` mirror, and interactive HTML slide deck [`NITW_Topic6_Presentation.html`](NITW_Topic6_Presentation.html). |
| [`requirements.txt`](requirements.txt) & [`tests/test_audit_fixes.py`](tests/test_audit_fixes.py) | Pinned runtime dependencies and 8 automated unit/integration tests covering preprocessing parity, input validation, cache `.meta.json` tamper checks, fold-only tangent fitting, and block-exclusion invariants (`python -m unittest tests/test_audit_fixes.py -v`). |
| [`results/legacy_720_archive/`](results/legacy_720_archive/PROVENANCE.md) | Quarantined superseded 720-trial artifacts from `2026-10-28` with provenance documentation. |

---

## 5. Quick Reproduction & Verification Commands

```bash
# 1. Install pinned dependencies & verify all 8 audit remediation tests
pip install -r requirements.txt
python -m unittest tests/test_audit_fixes.py -v

# 2. Rebuild verified dataset cache, run Stage 1 & Stage 2 audited pipelines
python dataset_loader.py
python baseline_paper.py
python improved_pipeline.py

# 3. Regenerate dynamic visual charts & run offline CLI / GUI demos
python compare_models.py
python draw_architecture.py
python predict.py --all
python predict.py 1
python eeg_gui_tester.py

# 4. Rebuild exact 12-page PDF/DOCX report & HTML slide deck
python build_nitw_12page_report.py
python build_presentation_deck.py
```
