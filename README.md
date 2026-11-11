# EEG Imagined Words Recognition Engine (Brain-Computer Interface)
### CS26001: Advanced Algorithms — Course Project: Topic 6
> **"Prediction of imagined words (Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes) by using Brain EEG signals."**  
> **Department of Computer Science and Engineering, National Institute of Technology Warangal**  
> **Team:** Saurabh Bharrdwaj (26CSM2R20, Lead) • Badvath Jaipal (26CSM2R04) • Saurabh Kumar (26CSM2R20)  
> **Date:** November 2026

---

## 1. Real Mendeley EEGIS Evaluation & Academic Integrity Disclosure
* **Real Dataset Used (Zero Synthetic Fallbacks)**: Evaluated exclusively on all **4,044 real in-vivo human EEG recordings** across 10 participants and 9 classes from the official Mendeley EEGIS Database ([DOI: 10.17632/73g4fw884c.1](https://data.mendeley.com/datasets/73g4fw884c/1)). `dataset_loader.py` raises `FileNotFoundError` if real recordings are absent.
* **Foundational Research Paper**: *Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram Signal Classification* (Lara-Arellano, Tovar-Arriaga, Takacs, Rodríguez-Reséndiz, *Eng* MDPI, 2025). [DOI: 10.3390/eng6040075](https://doi.org/10.3390/eng6040075)
  * Under strict multi-subject 9-class evaluation on raw 1.0-second real Mendeley EEGIS trials (balanced 720-trial cohort: 540 train / 180 unseen holdout; random chance = 11.11%), replicating the Static GA (`Pm=0.03`) + Single SVM pipeline achieves **36.11%** accuracy (`0.3453` Macro F1) on 102/322 features.
* **Proposed Algorithmic Innovations (MDRC-AGA)**:
  1. *Dual-Stream Riemannian Tangent Space Covariance*: Computes regularized spatial covariance on the SPD manifold and projects via matrix logarithm ($S_k = \log(C_k)$) to Euclidean tangent space, adding 105 spatial connectivity features ($D = 427$).
  2. *Diversity-Driven Adaptive Genetic Algorithm (AGA)*: Dynamically scales mutation rate $P_m(t)$ (`0.0397` to `0.0437`) using population phenotypic variance $\sigma(t)$, pruning **69.3%** of noisy features (`427` down to `131` optimal descriptors).
  3. *Calibrated Soft-Voting Stacking Ensemble*: Fuses RBF-SVM (`0.60`), HistGradientBoosting (`0.20`), and MLP (`0.20`) with weights `[3.0, 1.0, 1.0]`.
* **Verified Real-EEGIS Results (100% Organic Model Inference, Zero Overrides)**:
  * **Balanced 9-Class Holdout (180 test trials)**: Proposed Dual-Stream + AGA + Ensemble achieves **44.44%** accuracy (**+8.33%** over Static GA+SVM baseline, **4.0x** random chance, `0.4392` Macro F1); isolating Stream 2 Riemannian tangent features (105D) peaks at **46.11%** (`0.4499` Macro F1, `0.394` Kappa).
  * **Full 4,044-Trial Multi-Subject Benchmark (3,033 train / 1,011 test)**: Riemannian geometry lifts cross-subject 9-class accuracy from **20.08%** (scalar moments) to **27.10%** (**+7.02%** gain).
  * **Unfiltered Emergency Binary Triage (All Real Trials)**: `Help vs Pain` ($N=996$): `61.45%` $\rightarrow$ **67.07%** (**+5.62%**); `Help vs Rest` ($N=960$): `63.33%` $\rightarrow$ **67.92%** (**+4.59%**).
  * **Critical Emergency Recall**: **80.0% recall** (`0.696` F1) on `Help (Ayuda)`.
  * **Real-Time Signal Test Suite (`predict.py --all`)**: **5/9 (55.6%)** exact multi-class accuracy (**5.0x** random chance) on unseen raw EEG CSV/NPY files at **95.6 ms** mean CPU latency per 1.0 s epoch.

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
*Outputs a complete scorecard comparing organic model predictions against ground truth across all 9 real EEGIS test signals (**5/9 = 55.6%**, 5.0x random chance, **95.6 ms** mean CPU latency).*

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
* **One-Click Neural Decoding**: Extracts 427 dual-stream features, prunes to 131 via AGA, and produces calibrated probability bars in ~95 ms.
* **Browse Signal Button**: Load any `.csv` or `.npy` file from anywhere on your PC.
* **Ground-Truth Audit**: Reveals patient ground truth to demonstrate decoding fidelity.

---

## 4. Academic Reports & Presentation Deck

The project includes submission-ready documents matching NIT Warangal standards:

1. **12-Page PDF Report**: `NITW_Topic6_Imagined_Words_Final_Report.pdf` (Strictly matches the reference layout, typography, booktabs tables, and citations).
2. **Word Report (.docx)**: `NITW_Topic6_Imagined_Words_Final_Report.docx` (Fully editable Microsoft Word document).
3. **18-Slide Presentation Deck**: `NITW_Topic6_Presentation.html` (Interactive, dark clinical presentation with charts and animations).

To re-compile the report:
```bash
python build_nitw_12page_report.py
```

---

## 5. Clean Project Structure

```
imagined_speech_eeg/
├── data/
│   ├── eegis_real_dataset.npz              # 4,044 real human 14-ch EEG trials (Mendeley EEGIS)
│   └── eegis_real_features.npz             # Cached 427-dim Multi-Domain + Riemannian features
├── models/
│   ├── aga_selector.py                     # Innovation 2: Adaptive GA feature selector
│   ├── ga_feature_selector.py              # Baseline static GA selector
│   └── eegnet_attention.py                 # PyTorch EEGNet neural network
├── results/
│   ├── best_improved_ensemble.pkl          # Proposed Stacking Ensemble + AGA model (44.44% / 131 feats)
│   ├── best_ml_pipeline.pkl                # Baseline Static GA + SVM model weights (36.11% / 102 feats)
│   ├── baseline_paper_metrics.json         # Real-EEGIS baseline holdout metrics
│   ├── improved_pipeline_metrics.json      # Real-EEGIS proposed holdout + AGA trajectory metrics
│   ├── architecture_flow_diagram.png       # Figure 1: End-to-end architecture flowchart
│   ├── fig2_aga_optimization.png           # Figure 2: AGA convergence trajectory
│   ├── fig3_accuracy_comparison.png        # Figure 3: Cross-architecture accuracy bar chart
│   ├── baseline_vs_improved_comparison.png # Combined side-by-side figure
│   ├── confusion_matrix_baseline.png       # Baseline 9-Class confusion matrix
│   ├── confusion_matrix_improved.png       # Figure 4: Proposed 9-Class confusion matrix
│   ├── live_decoded_signal.png             # Figure 5: 14-Channel oscilloscope waveform
│   └── sample_prediction.png               # Latest decoded signal waveform & confidence plot
├── src/                                    # Modular source code
├── test_signals/                           # 9 Real 14-channel EEGIS test recordings (CSV & NPY)
│   ├── eeg_signal_01.csv to 09.csv
│   ├── eeg_signal_01.npy to 09.npy
│   └── ground_truth_registry.json          # Medical ground truth registry
├── dataset_loader.py                       # Real-only Mendeley EEGIS loader (auto-reads data/ or dataset/, zero synthetic fallback)
├── baseline_paper.py                       # Static GA + SVM baseline script (36.11% real EEGIS)
├── improved_pipeline.py                    # Proposed Dual-Stream + AGA + Ensemble script (44.44% real EEGIS)
├── compare_models.py                       # Side-by-side chart generation from real JSON metrics
├── predict.py                              # Real-time predictor (accepts ANY signal, zero overrides)
├── test_eeg_signal.py                      # Signal-driven test script
├── eeg_gui_tester.py                       # Real-time oscilloscope desktop GUI
├── build_nitw_12page_report.py             # Pure-Python 12-page PDF & Word builder
├── build_presentation_deck.py              # Interactive 18-slide HTML presentation builder
├── NITW_Topic6_Imagined_Words_Final_Report.pdf   # Final 12-page PDF report
├── NITW_Topic6_Imagined_Words_Final_Report.docx  # Final Microsoft Word report
├── NITW_Topic6_Presentation.html           # 18-slide interactive presentation deck
└── README.md                               # Project documentation
```
