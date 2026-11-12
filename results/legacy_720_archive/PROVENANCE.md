# Legacy 720-Trial First-Draft Artifacts Archive

These files are preserved strictly for historical reproducibility of the initial
project draft (`2026-10-28`, `N=720` balanced 9-class synthetic/subset exploratory phase)
and **must NOT be mixed with or cited as results from the full `N=4,044` Mendeley EEGIS pipeline**.

Archived files moved from `results/` (Flaw #25 remediation):
- `best_ml_pipeline.pkl` (10/28/2026) — initial N=720 sklearn pipeline
- `confusion_matrix_ml.png` (10/28/2026) — initial N=720 confusion matrix
- `best_eegnet_model.pth` (10/28/2026) — initial N=720 EEGNet checkpoint
- `training_curves_dl.png` (10/28/2026) — initial N=720 EEGNet training curves

Current full `N=4,044` (`N_ref=3,936` after full-block exclusion of 9 `test_signals/` blocks)
pipelines write exclusively to:
- `results/baseline_paper_metrics.json`
- `results/improved_pipeline_metrics.json`
- `results/comparison_baselines.json`
- `results/dataset_audit_report.json`
- `results/dataset_manifest.json`
- `results/full4044_splits.npz`
- `results/best_improved_ensemble.pkl`
- `results/eegnet_attention_4044.pth`
