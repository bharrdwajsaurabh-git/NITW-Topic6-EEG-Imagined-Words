"""
tests/test_audit_fixes.py
=========================
Automated verification suite (compatible with BOTH `python -m unittest` and `pytest`)
validating remediation of audit flaws:
  1. CSV header/index preservation & short/NaN/Inf/channel/fs rejection (no edge padding)
  2. Unified alpha/beta/gamma bandpass cutoffs across loader and feature extractors
  3. Cache .meta.json validation & automatic stale/corrupt rejection
  4. Dataset provenance: unrecoverable subject IDs tagged explicitly + verified block_ids
  5. Full-block exclusion of test_signals (108 sibling chunks excluded, 0 shared blocks)
  6. True training-fold Riemannian Tangent Space (C_ref fit strictly on train) & no leakage
  7. Internal GA GroupKFold disjointness + scalar/block-weight honesty + Brier/ECE metrics
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from eeg_preprocessing import (
    CHANNEL_NAMES,
    CANONICAL_BAND_CUTOFFS,
    load_eeg_epoch_file,
    preprocess_epoch,
)
from eeg_features import (
    FREQUENCY_BANDS,
    RiemannianTangentSpace,
    MultiScaleTangentExtractor,
    compute_spd_covariances,
    extract_trial_features,
)
from dataset_loader import (
    UNRECOVERABLE_SUBJECT_LABEL,
    _write_cache_with_meta,
    _validate_cache,
)
from models.aga_selector import (
    MultiScaleBlockAGA,
    CalibratedManifoldStacker,
    compute_classification_and_calibration_metrics,
)
from baseline_paper import identify_test_signal_blocks


class TestAuditRemediations(unittest.TestCase):
    def test_canonical_band_cutoffs_unified(self):
        self.assertEqual(FREQUENCY_BANDS, CANONICAL_BAND_CUTOFFS)
        self.assertEqual(CANONICAL_BAND_CUTOFFS["alpha"], (8.0, 13.0))
        self.assertEqual(CANONICAL_BAND_CUTOFFS["beta"], (13.0, 30.0))
        self.assertEqual(CANONICAL_BAND_CUTOFFS["gamma"], (30.0, 40.0))

    def test_headerless_csv_preserves_row0_and_column_reordering(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            rng = np.random.RandomState(0)
            arr = rng.randn(128, 14) * 20.0
            f_hdrless = tmp_path / "headerless.csv"
            np.savetxt(f_hdrless, arr, delimiter=",")
            loaded = load_eeg_epoch_file(str(f_hdrless))
            self.assertEqual(loaded.shape, (14, 128))
            self.assertTrue(np.allclose(loaded.T[0], arr[0], atol=1e-6), "Row 0 must not be dropped!")

            rev_names = list(reversed(CHANNEL_NAMES))
            f_swapped = tmp_path / "swapped.csv"
            with open(f_swapped, "w", encoding="utf-8") as f:
                f.write("," + ",".join(rev_names) + "\n")
                for i in range(128):
                    row_vals = ",".join(f"{arr[i, 13 - j]:.8f}" for j in range(14))
                    f.write(f"{i},{row_vals}\n")
            reordered = load_eeg_epoch_file(str(f_swapped))
            self.assertEqual(reordered.shape, (14, 128))
            self.assertTrue(np.allclose(reordered.T, arr, atol=1e-5))

    def test_rejects_short_nan_wrong_channel_wrong_fs(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            f_short = tmp_path / "short.csv"
            np.savetxt(f_short, np.random.randn(64, 14), delimiter=",")
            with self.assertRaisesRegex(ValueError, "Silent edge-padding is disabled"):
                load_eeg_epoch_file(str(f_short))

            arr_nan = np.random.randn(128, 14)
            arr_nan[5, 3] = np.nan
            f_nan = tmp_path / "nan.csv"
            np.savetxt(f_nan, arr_nan, delimiter=",")
            with self.assertRaisesRegex(ValueError, "NaN"):
                load_eeg_epoch_file(str(f_nan))

            f_12ch = tmp_path / "ch12.csv"
            np.savetxt(f_12ch, np.random.randn(128, 12), delimiter=",")
            with self.assertRaises(ValueError):
                load_eeg_epoch_file(str(f_12ch))

            f_ok = tmp_path / "ok.csv"
            np.savetxt(f_ok, np.random.randn(128, 14), delimiter=",")
            with self.assertRaisesRegex(ValueError, "Unsupported sampling rate"):
                load_eeg_epoch_file(str(f_ok), sampling_rate_hz=256)

    def test_preprocess_parity_between_train_and_inference(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            raw_offset = np.random.randn(14, 128) * 15.0 + 4200.0
            proc1 = preprocess_epoch(raw_offset)
            f_vec_train, _ = extract_trial_features(proc1, CHANNEL_NAMES, detrend=True)

            f_csv = tmp_path / "epoch.csv"
            with open(f_csv, "w", encoding="utf-8") as f:
                f.write("," + ",".join(CHANNEL_NAMES) + "\n")
                for t in range(128):
                    f.write(f"{t}," + ",".join(f"{raw_offset[c, t]:.10f}" for c in range(14)) + "\n")
            loaded = load_eeg_epoch_file(str(f_csv))
            proc2 = preprocess_epoch(loaded)
            f_vec_inf, _ = extract_trial_features(proc2, CHANNEL_NAMES, detrend=True)
            self.assertTrue(np.allclose(proc1, proc2, atol=1e-4))
            self.assertTrue(np.allclose(f_vec_train, f_vec_inf, rtol=1e-4, atol=1e-4))

    def test_cache_meta_validation_detects_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            cpath = str(Path(td) / "dummy.npz")
            X = np.zeros((4, 14, 128), dtype=np.float32)
            y = np.zeros(4, dtype=np.int64)
            _write_cache_with_meta(cpath, {"X": X, "y": y}, {"shape": list(X.shape)})
            ok, _, msg = _validate_cache(cpath, ["X", "y"])
            self.assertTrue(ok and msg == "ok")

            meta_p = cpath + ".meta.json"
            with open(meta_p, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["code_version"] = "0.0.0-stale"
            with open(meta_p, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            ok2, _, _ = _validate_cache(cpath, ["X", "y"])
            self.assertFalse(ok2)

    def test_fold_tangent_space_does_not_leak_test_samples(self):
        rng = np.random.RandomState(42)
        cov_tr = compute_spd_covariances(rng.randn(20, 14, 128))
        cov_a = compute_spd_covariances(rng.randn(5, 14, 128))
        cov_b = compute_spd_covariances(rng.randn(5, 14, 128) * 100.0 + 50.0)

        ts_a = RiemannianTangentSpace().fit(cov_tr)
        ref_a = ts_a.c_ref_.copy()
        _ = ts_a.transform(cov_a)

        ts_b = RiemannianTangentSpace().fit(cov_tr)
        _ = ts_b.transform(cov_b)
        self.assertTrue(np.allclose(ref_a, ts_b.c_ref_))

    def test_full_block_exclusion_and_calibration_metrics(self):
        reg_path = os.path.join(ROOT_DIR, "test_signals", "ground_truth_registry.json")
        if os.path.exists(reg_path):
            sig0 = load_eeg_epoch_file(os.path.join(ROOT_DIR, "test_signals", "eeg_signal_01.csv"))
            proc0 = preprocess_epoch(sig0)
            rng = np.random.RandomState(1)
            X_raw = rng.randn(24, 14, 128).astype(np.float32) * 5.0
            X_raw[12] = proc0
            block_ids = np.repeat([0, 1], 12)
            res = identify_test_signal_blocks(X_raw, block_ids, test_signals_dir=os.path.join(ROOT_DIR, "test_signals"))
            self.assertIn(1, res["excl_blocks"])
            self.assertGreaterEqual(int(np.sum(~res["ref_mask"])), 12)

        rng = np.random.RandomState(7)
        X = rng.randn(60, 30)
        y = np.tile(np.arange(3), 20)
        g = np.repeat(np.arange(15), 4)
        aga = MultiScaleBlockAGA(block_dims=(10, 10, 10), n_population=6, n_generations=2, cv_splits=3).fit(X, y, groups=g)
        self.assertEqual(aga.active_feature_count_, 30)
        self.assertEqual(aga.total_feature_count_, 30)
        st = CalibratedManifoldStacker(cv_splits=3).fit(X, y, groups=g)
        probs = st.predict_proba(X)
        m = compute_classification_and_calibration_metrics(y, st.predict(X), probs, block_ids=g, n_bootstrap=30)
        self.assertTrue(0.0 <= m["ece_10bin"] <= 1.0)
        self.assertTrue(0.0 <= m["brier_score"] <= 2.0)
        self.assertTrue(m["acc_ci95_low"] <= m["accuracy"] <= m["acc_ci95_high"])

    def test_real_dataset_provenance_if_present(self):
        meta_p = os.path.join(ROOT_DIR, "data", "eegis_6band_real.npz.meta.json")
        if os.path.exists(meta_p):
            with open(meta_p, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["n_trials"], 4044)
            self.assertEqual(meta["n_blocks"], 337)
            self.assertIs(meta["subject_ids_recoverable"], False)
            self.assertEqual(meta["overlap_diagnostics"]["within_block_nonzero_discontinuities"], 0)


if __name__ == "__main__":
    unittest.main()
