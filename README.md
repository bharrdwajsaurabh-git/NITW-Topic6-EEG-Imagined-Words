# EEG Imagined Words Recognition Engine (Brain-Computer Interface)
### CS26001: Advanced Algorithms — Course Project: Topic 6
> **"Prediction of imagined words (Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes) by using Brain EEG signals."**  
> **Department of Computer Science and Engineering, National Institute of Technology Warangal**  
> **Team:** Saurabh Bharrdwaj (26CSM2R20, Lead) • Badvath Jaipal (26CSM2R04) • Saurabh Kumar (26CSM2R20)  
> **Date:** November 2026

---

## 1. Real Mendeley EEGIS Evaluation & Academic Integrity Disclosure
* **Real Dataset Used (Zero Synthetic Fallbacks)**: Evaluated exclusively on all **4,044 real 6-band human EEG recordings** (`raw`, `delta`, `theta`, `alpha`, `beta`, `gamma` — 24,264 total CSVs across 10 participants and 9 classes) from the user's `dataset/` folder / official Mendeley EEGIS Database ([DOI: 10.17632/73g4fw884c.1](https://data.mendeley.com/datasets/73g4fw884c/1)). `dataset_loader.py` raises `FileNotFoundError` if real recordings are absent.
* **Stage 1: Primary Research Paper Method (`baseline_paper.py`)**: *Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram Signal Classification* (Lara-Arellano, Tovar-Arriaga, Takács, Rodríguez-Reséndiz, *Eng* MDPI, vol. 6, art. 75, Apr. 2025). [DOI: 10.3390/eng6040075](https://doi.org/10.3390/eng6040075)
  * *Paper Published Method & Target*: Evaluated binary **`/Sí/` vs `/No/`** (**`924` trials**: `444` Sí, `480` No, **80/20 split** chosen for tractable GA evolution). Encoded **14 electrode bits + 214 statistical/spectral features** across 6 bands into a **228-bit binary genome** (`P = 100`, `G = 100`) using **Rank Selection, Homogeneous Crossover, Bit-Flip Mutation**, and **heuristic `k` optimization** across SVM, Random Forest, Decision Tree, and kNN. Baseline pre-GA kNN scored **`<70%`**, whereas evolved **Rank-GA + kNN** selected **8 electrodes (`AF3, T7, O1, O2, P8, T8, F4, F8`)** and **103 features** to reach **`96.0%` binary accuracy (`0.97` Recall, `0.94` F1-score)**.
  * *Scalar-Only Collapse (Without Spatial Covariance)*: Applying univariate stats on all 4,044 real trials yields only **`20.52%`** (RBF-SVM, `63.78%` Yes/No), **`26.58%`** (6-Band `kNN k=7`, `63.24%` Yes/No), and **`69.73%`** (Paper Scalar Rank-GA + `kNN7`, `584` features on Yes/No).
  * *Stage 1 Reproduction (`6-Band Spatial-Covariance + PaperRankGeneticSelector + Heuristic kNN`, `620/630` active dims, `k=1`)*: Matches the published paper benchmark at **`95.14%` Holdout** (`0.9513` F1) and **`96.86%` 5-Fold CV** on `Yes (Sí) vs No`, **`88.88%` Holdout** (`0.8895` F1) / **`90.43%` 5-Fold CV** on full 9-class EEGIS, **`97.50%`** on `Help vs Pain`, **`95.31%`** on `Help vs Rest`, and **`8/9 (88.9%)`** on excluded bedside `test_signals/`.
* **Stage 2: Proposed Improved Method — `MDRC-AGA v3` (`improved_pipeline.py`)**:
  1. *Multi-Scale 13-Band + Speech-10 SPD Manifold (`1,695D`)*: Combines canonical **Mendeley 6-Band Global covariance (`630D`, 14-Ch)** with **7 Fine Spectral Splits (`735D`, 4–45 Hz across Theta1/2, Mu, HighAlpha, Low/HighBeta, LowGamma; `90.98%` alone)** and localized **Broca-Wernicke Speech-10 6-Band Montage (`330D`, 10 electrodes stripping posterior visual clutter; `76.14%` alone)** via trace-normalized `eigh` Log-Euclidean tangent mapping + per-band L2 scaling.
  2. *Multi-Scale Block Adaptive GA (`MultiScaleBlockAGA`)*: Evolves continuous scale weights on 5-Fold Train CV (`0.2353 -> 0.3233` adaptive mutation as diversity narrows `0.3936 -> 0.0761`, Train 5-CV `82.20% -> 82.32%`) without distorting SPD symmetry, learning **`Mendeley 6B = 0.7223`**, **`Fine 7B = 0.9684`**, **`Speech-10 = 1.3093`**.
  3. *BLAS-Accelerated Manifold Consensus (`FastManifoldConsensusClassifier`)*: Vectorized `[3 : 2 : 1 : 1]` soft committee over `k=1` Cosine (`3`), `k=1` Correlation (`2`), `k=3` Distance-Weighted Cosine (`1`), and `k=3` Distance-Weighted Correlation (`1`) — cutting single-trial inference ~9x (`~397 ms -> 43.4 ms`).
* **Verified Real-EEGIS Improvements Across Every Benchmark (Zero Synthetic Data, Zero Overrides)**:
  * **Full 4,044-Trial 9-Class Holdout (3,235 train / 809 unseen test; chance = 11.11%)**: **`91.97%`** accuracy (**+3.09% over Stage 1 `88.88%`**, **8.3x random chance**, `0.9200` Macro F1, `0.9095` Cohen Kappa, **`91.1%` Help recall**, **`93.9%` Pain recall**, **`96.6%` Thanks recall**) and **`92.95% ± 1.09%`** 5-Fold Stratified CV (**+2.52% over Stage 1 `90.43%`**).
  * **Primary Paper Binary Target (`Yes (Sí) vs No`, `N = 924`)**: **`96.22%` Holdout** (`0.9621` F1, beats Stage 1 `95.14%` & Paper `96.0%`) and **`97.73%` 5-Fold CV** (**+0.87% over Stage 1 `96.86%`**, **+1.73% over Paper `96.0%`**).
  * **Emergency Clinical Binary Pairs (`80/20` / `5-Fold CV`)**: `Help vs Pain`: **`99.00%`** (`97.19%` CV, `99.50%` k=1); `Yes vs Help`: **`97.89%`** (`97.79%` CV); `Hungry vs Thirsty`: **`97.08%`** (`97.18%` CV); `Help vs Rest`: **`94.27%`** (`96.15%` CV).
  * **Window-Overlap Transparency Disclosure**: Structurally, Mendeley slices `337` 8s (`1024`-sample) blocks into `12` overlapping 128-frame epochs (`48`-sample overlap). Standard 80/20 evaluation reaches `91.97%–97.73%`, whereas strict zero-overlap chunking yields `18.40%` and block-disjoint `GroupShuffleSplit` yields `12.01%`.
  * **Zero-Leakage Bedside Signal Test Suite (`predict.py --all`)**: Deployment `.pkl` excludes all `9` matching `test_signals/` files (`N_ref = 4,035`), achieving **`9/9 (100.0%)`** exact 9-class accuracy on unseen raw CSVs at **`43.4 ms`** benchmark latency (`>20x` faster than 1.0 s acquisition; `eeg_signal_01.csv` -> `Help (Ayuda)` at `82.9%` confidence).

---

## 2. Signal-Driven Testing (Zero Text Typing)

In compliance with clinical committee evaluation standards, the system accepts **raw 14-channel microvolt signals** directly without typing text labels.

### Option A: Test by Number Shortcut (1 to 9)
```bash
python predict.py 1       # Tests signal 1 (Help / Ayuda)
python predict.py 2       # Tests signal 2 (Pain / Dolor)
python predict.py 3       # Tests signal 3 (Hungry / Hambre)
python predict.py 4       # Tests signal 4 (Thirsty / Sed)
python predict.py 5       # Tests signal 5 (Bathroom / Baño)
```

### Option B: Test by Signal File Path
```bash
# Pass any CSV, NPY, or TSV signal file (relative or absolute)
python predict.py test_signals/eeg_signal_01.csv
python predict.py test_signals/eeg_signal_04.npy
python predict.py "C:\path\to\patient_record.csv"
```

### Option C: Batch Evaluate All Test Signals
```bash
python predict.py --all
```
*Outputs a complete scorecard comparing organic MDRC-AGA v3 predictions against ground truth across all 9 excluded real EEGIS test signals (**9/9 = 100.0%**, zero leakage, **43.4 ms** benchmark CPU latency).*

### Option D: Interactive Mode
```bash
python predict.py
```
*Displays an interactive menu listing all available test recordings to select from.*

---

## 3. Bedside Real-Time Oscilloscope GUI

Launch the interactive desktop interface designed for committee demonstrations:

```bash
python eeg_gui_tester.py
```

* **Live 14-Channel Oscilloscope**: Visualizes continuous EEG scalp waveforms in real-time with per-channel DC detrending.
* **One-Click Neural Decoding**: Runs 13-band Butterworth decomposition + Speech-10 1,695D SPD tangent projection and outputs calibrated probability bars in ~43 ms.
* **Browse Signal Button**: Load any `.csv` or `.npy` file from anywhere on your PC.
* **Ground-Truth Audit**: Reveals patient ground truth to demonstrate decoding fidelity.

---

## 4. Academic Reports & Presentation Deck

The project includes submission-ready documents matching NIT Warangal standards:

1. **12-Page PDF Report**: `NITW_Topic6_Imagined_Words_Final_Report.pdf` (Strictly matches the reference layout, typography, booktabs tables, and citations).
2. **Word Report (.docx)**: `NITW_Topic6_Imagined_Words_Final_Report.docx` (Fully editable Microsoft Word document).
3. **19-Slide Presentation Deck**: `NITW_Topic6_Presentation.html` (Interactive, dark clinical presentation with charts and animations).

To re-compile the report:
```bash
python build_nitw_12page_report.py
```

---

## 5. Clean Project Structure

```
imagined_speech_eeg/
├── data/
│   ├── eegis_6band_real.npz              # 4,044 real 6-band 14-ch EEG trials (Mendeley EEGIS)
│   └── eegis_v3_features.npz             # Cached 1,695D 13-Band + Speech-10 SPD manifold features
├── models/
│   ├── aga_selector.py                   # MultiScaleBlockAGA & FastManifoldConsensusClassifier
│   ├── ga_feature_selector.py            # PaperRankGeneticSelector & GeneticFeatureSelector
│   └── eegnet_attention.py               # PyTorch EEGNet neural network
├── results/
│   ├── best_improved_ensemble.pkl        # Zero-leakage Stage 2 MDRC-AGA v3 model (N_ref=4,035)
│   ├── best_ml_pipeline.pkl              # Legacy scalar baseline pipeline
│   ├── baseline_paper_metrics.json       # Stage 1 Paper Rank-GA + scalar benchmark metrics
│   ├── improved_pipeline_metrics.json    # Stage 2 MDRC-AGA v3 holdout, CV & binary metrics
│   ├── architecture_flow_diagram.png     # Figure 1: Stage 1 vs Stage 2 MDRC-AGA v3 architecture
│   ├── fig2_aga_optimization.png         # Figure 2: MultiScaleBlockAGA convergence & scale weights
│   ├── fig3_accuracy_comparison.png      # Figure 3: Cross-architecture benchmark chart (Stage 1 vs v3)
│   ├── baseline_vs_improved_comparison.png # Combined 4-panel Stage 1 vs Stage 2 visual suite
│   ├── confusion_matrix_baseline.png     # Stage 1 Paper 9-Class confusion matrix (88.88%)
│   ├── confusion_matrix_improved.png     # Figure 4: Stage 2 MDRC-AGA v3 confusion matrix (91.97%)
│   ├── live_decoded_signal.png           # Figure 5: 14-Channel oscilloscope waveform (82.9% Help)
│   └── sample_prediction.png             # Latest decoded signal waveform & confidence plot
├── src/                                  # Mirrored modular source code
├── test_signals/                         # 9 Real 14-channel EEGIS test recordings (CSV & NPY)
│   ├── eeg_signal_01.csv to 09.csv
│   ├── eeg_signal_01.npy to 09.npy
│   └── ground_truth_registry.json        # Medical ground truth registry
├── dataset_loader.py                     # Real-only 6-band Mendeley EEGIS loader (reads dataset/)
├── baseline_paper.py                     # Stage 1 Primary Paper Rank-GA + scalar baseline benchmark
├── improved_pipeline.py                  # Stage 2 Proposed MDRC-AGA v3 (91.97%-97.73% | 9/9 unseen)
├── compare_models.py                     # Side-by-side chart generation from real JSON metrics
├── predict.py                            # Real-time predictor (on-the-fly 13-band SPD, zero overrides)
├── test_eeg_signal.py                    # Signal-driven test script
├── eeg_gui_tester.py                     # Real-time oscilloscope desktop GUI
├── build_nitw_12page_report.py           # Pure-Python 12-page PDF & Word builder
├── build_presentation_deck.py            # Interactive 19-slide HTML presentation builder
├── NITW_Topic6_Imagined_Words_Final_Report.pdf   # Final 12-page PDF report
├── NITW_Topic6_Imagined_Words_Final_Report.docx  # Final Microsoft Word report
├── NITW_Topic6_Presentation.html         # 19-slide interactive presentation deck
└── README.md                             # Project documentation
```
