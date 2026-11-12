"""
improved_pipeline.py
====================
Stage 2: MDRC-AGA Framework with Leakage-Free Nested Optimization, True Fold-Fitted
Riemannian Tangent Space, Calibrated OOF Stacking, and Complete Scientific Ablations.

Remediated audit items (All Flaws #1-#17, #27-#30):
  1. Uses the exact locked `N_ref=3,936` (328 block-disjoint recordings; 9 complete test_signals
     blocks / 108 sibling chunks excluded via `ensure_canonical_splits`).
  2. Reports BOTH protocols side by side with equal emphasis:
       - Primary Unbiased Benchmark: Block-Disjoint Nested 5-Fold CV (`328` disjoint blocks;
         Fold 0 = 20% Locked Block Holdout, `set(train_blocks).isdisjoint(test_blocks)`).
       - Secondary Exploratory Benchmark: Overlapping-Chunk Nested 5-Fold CV (`N_ref=3,936`)
         with explicit leakage warning.
  3. Zero CV leakage: Fits `MultiScaleTangentExtractor(geometry='tangent_fold')` (`C_ref` mean),
     `StandardScaler`, `MultiScaleBlockAGA` (using `GroupKFold` in block-disjoint mode), and
     `CalibratedManifoldStacker` strictly inside every outer training fold.
  4. Executes genuine controlled ablations:
       - Geometry: True Fold Tangent Space (`C_ref`) vs Identity Log-Euclidean (`I`)
       - Classifier Head: `MultiMetricSoftVotingClassifier` (`[3,2,1,1]` & `[1,1,1,1]` un-calibrated vote)
         vs `CalibratedManifoldStacker` (OOF Logistic Calibration -> Brier, ECE) vs LDA / LogReg / Calibrated SVM / kNN
       - 5-Seed Mutation Control (`fixed` vs `diversity_adaptive` vs `diversity_stagnation`)
       - Sub-Band Overlap (`non_overlapping` vs `overlapping`)
       - Electrode Montage (`speech10` vs `all14` vs `left7` vs `occipital4`)
       - Continuous Window Length & IIR Filter-Transient Stability (`1s`, `2s`, `4s`, `8s` on continuous 1,008-sample blocks)
"""

import os
import sys
import json
import time
import pickle
import numpy as np
import scipy.linalg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

curr_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(curr_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import confusion_matrix, classification_report

from eeg_preprocessing import (
    CODE_VERSION,
    CHANNEL_NAMES,
    CLASS_MAP,
    SAMPLING_RATE,
    SAMPLES_PER_EPOCH,
    BAND_NAMES,
    CANONICAL_BAND_CUTOFFS,
    SUB7_CUTOFFS_NONOVERLAP,
    load_eeg_epoch_file,
    preprocess_epoch,
)
from dataset_loader import (
    load_eegis_6band_with_provenance,
    reconstruct_continuous_8s_blocks,
)
from eeg_features import (
    MultiScaleTangentExtractor,
    compute_spd_covariances,
    bandpass_filter_bank,
    _spd_tangent_batch,
    extract_6band_riemannian_features,
    extract_mdrc_v3_features,
    extract_single_trial_v3_from_raw,
)
from models.aga_selector import (
    MultiScaleBlockAGA,
    MultiMetricSoftVotingClassifier,
    CalibratedManifoldStacker,
    compute_classification_and_calibration_metrics,
)
from baseline_paper import ensure_canonical_splits, OVERLAP_DISCLOSURE

WORD_CLASSES = [CLASS_MAP[i] for i in sorted(CLASS_MAP.keys())]
SEEDS_5 = [42, 7, 123, 999, 2025]


def extract_riemannian_features(X: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """Backward-compatible single-band identity-centered Log-Euclidean SPD extractor."""
    return _spd_tangent_batch(X, reg=reg)


def _run_nested_multiscale_cv(
    X6_sub: np.ndarray,
    y_sub: np.ndarray,
    fold_ids: np.ndarray,
    groups_sub: np.ndarray,
    enforce_disjoint: bool,
    geometry: str = "tangent_fold",
    subband_mode: str = "non_overlapping",
    local_montage: str = "speech10",
    mutation_mode: str = "diversity_adaptive",
    n_pop: int = 14,
    n_gen: int = 8,
    inner_cv_splits: int = 4,
    random_state: int = 42,
    run_all_heads: bool = True,
    pre_covs: tuple = None,
):
    """
    Executes strictly nested 5-fold CV where feature geometry (C_ref when tangent_fold),
    scaler, MultiScaleBlockAGA weights, and classifier/stacker fit INSIDE outer training folds only.
    """
    classes = np.unique(y_sub)
    n_c = len(classes)
    n = len(y_sub)

    oof = {
        "weighted_vote": np.zeros(n, dtype=np.int64),
        "weighted_vote_p": np.zeros((n, n_c), dtype=np.float64),
        "stacker": np.zeros(n, dtype=np.int64),
        "stacker_p": np.zeros((n, n_c), dtype=np.float64),
    }
    if run_all_heads:
        oof.update({
            "equal_vote": np.zeros(n, dtype=np.int64),
            "equal_vote_p": np.zeros((n, n_c), dtype=np.float64),
            "lda": np.zeros(n, dtype=np.int64),
            "lda_p": np.zeros((n, n_c), dtype=np.float64),
            "logreg": np.zeros(n, dtype=np.int64),
            "logreg_p": np.zeros((n, n_c), dtype=np.float64),
            "svm_cal": np.zeros(n, dtype=np.int64),
            "svm_cal_p": np.zeros((n, n_c), dtype=np.float64),
            "knn1_cos": np.zeros(n, dtype=np.int64),
            "knn3_cos": np.zeros(n, dtype=np.int64),
        })

    fold_weights = []
    fold_histories = []
    c_pos = {int(c): i for i, c in enumerate(classes)}

    def _align(clf, probs):
        aligned = np.zeros((len(probs), n_c), dtype=np.float64)
        for j, c in enumerate(clf.classes_):
            aligned[:, c_pos[int(c)]] = probs[:, j]
        return aligned

    if pre_covs is None:
        base_ext = MultiScaleTangentExtractor(
            geometry=geometry,
            subband_mode=subband_mode,
            local_montage=local_montage,
            fs=SAMPLING_RATE,
        )
        covs_all, bdims_all = base_ext.precompute_view_covariances(X6_sub[:, 0], X6_sub)
    else:
        covs_all, bdims_all = pre_covs

    for fid in range(5):
        if run_all_heads:
            print(f"    -> fold {fid+1}/5...", flush=True)
        te = fold_ids == fid
        tr = ~te
        if enforce_disjoint:
            assert set(groups_sub[tr]).isdisjoint(set(groups_sub[te]))

        ext = MultiScaleTangentExtractor(
            geometry=geometry,
            subband_mode=subband_mode,
            local_montage=local_montage,
            fs=SAMPLING_RATE,
        )
        covs_tr = [c[tr] for c in covs_all]
        covs_te = [c[te] for c in covs_all]
        ext.fit_from_covs(covs_tr, bdims_all)
        F_tr = ext.transform_from_covs(covs_tr)
        F_te = ext.transform_from_covs(covs_te)

        sc = StandardScaler().fit(F_tr)
        Z_tr = sc.transform(F_tr)
        Z_te = sc.transform(F_te)

        inner_groups = groups_sub[tr] if enforce_disjoint else None
        aga = MultiScaleBlockAGA(
            block_dims=ext.block_dims_,
            n_population=n_pop,
            n_generations=n_gen,
            cv_splits=inner_cv_splits,
            mutation_mode=mutation_mode,
            random_state=random_state + fid,
        ).fit(Z_tr, y_sub[tr], groups=inner_groups)

        Zw_tr = aga.transform(Z_tr)
        Zw_te = aga.transform(Z_te)
        fold_weights.append([round(float(w), 4) for w in aga.best_weights_])
        fold_histories.append({
            "fitness": [round(float(v), 5) for v in aga.history_],
            "diversity": [round(float(v), 5) for v in aga.diversity_history_],
            "mutation": [round(float(v), 5) for v in aga.mutation_history_],
        })

        # 1) Weighted soft voter (heuristic [3,2,1,1] un-calibrated vote fraction)
        wv = MultiMetricSoftVotingClassifier(k_base=3, weights=(3.0, 2.0, 1.0, 1.0)).fit(Zw_tr, y_sub[tr])
        oof["weighted_vote"][te] = wv.predict(Zw_te)
        oof["weighted_vote_p"][te] = _align(wv, wv.predict_proba(Zw_te))

        # 2) Calibrated OOF Stacker
        st = CalibratedManifoldStacker(cv_splits=inner_cv_splits, random_state=random_state + fid).fit(
            Zw_tr, y_sub[tr], groups=inner_groups
        )
        oof["stacker"][te] = st.predict(Zw_te)
        oof["stacker_p"][te] = _align(st, st.predict_proba(Zw_te))

        if run_all_heads:
            ev = MultiMetricSoftVotingClassifier(k_base=3, weights=(1.0, 1.0, 1.0, 1.0)).fit(Zw_tr, y_sub[tr])
            oof["equal_vote"][te] = ev.predict(Zw_te)
            oof["equal_vote_p"][te] = _align(ev, ev.predict_proba(Zw_te))

            lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(Zw_tr, y_sub[tr])
            oof["lda"][te] = lda.predict(Zw_te)
            oof["lda_p"][te] = _align(lda, lda.predict_proba(Zw_te))

            lr = LogisticRegression(C=0.1, max_iter=2000, tol=1e-3, random_state=random_state).fit(Zw_tr, y_sub[tr])
            oof["logreg"][te] = lr.predict(Zw_te)
            oof["logreg_p"][te] = _align(lr, lr.predict_proba(Zw_te))

            n_svm_comp = max(2, min(256, Zw_tr.shape[0] - 20, Zw_tr.shape[1]))
            svm = Pipeline([
                ("pca", PCA(n_components=n_svm_comp, svd_solver="randomized", random_state=random_state)),
                ("cal_svm", CalibratedClassifierCV(
                    SVC(kernel="rbf", C=1.5, cache_size=1000, tol=1e-2, random_state=random_state),
                    cv=3,
                    method="sigmoid",
                    ensemble=False,
                )),
            ]).fit(Zw_tr, y_sub[tr])
            oof["svm_cal"][te] = svm.predict(Zw_te)
            oof["svm_cal_p"][te] = _align(svm, svm.predict_proba(Zw_te))

            oof["knn1_cos"][te] = KNeighborsClassifier(1, metric="cosine").fit(Zw_tr, y_sub[tr]).predict(Zw_te)
            oof["knn3_cos"][te] = KNeighborsClassifier(3, weights="distance", metric="cosine").fit(Zw_tr, y_sub[tr]).predict(Zw_te)

    b_arg = groups_sub if enforce_disjoint else None
    summary = {
        "fold_weights": fold_weights,
        "mean_weights": [round(float(v), 4) for v in np.mean(fold_weights, axis=0)],
        "fold0_aga_history": fold_histories[0],
        "weighted_vote_5cv": compute_classification_and_calibration_metrics(
            y_sub, oof["weighted_vote"], oof["weighted_vote_p"], block_ids=b_arg, random_state=random_state
        ),
        "calibrated_stacker_5cv": compute_classification_and_calibration_metrics(
            y_sub, oof["stacker"], oof["stacker_p"], block_ids=b_arg, random_state=random_state
        ),
    }
    hold_mask = fold_ids == 0
    hb_arg = groups_sub[hold_mask] if enforce_disjoint else None
    summary["weighted_vote_holdout_fold0"] = compute_classification_and_calibration_metrics(
        y_sub[hold_mask], oof["weighted_vote"][hold_mask], oof["weighted_vote_p"][hold_mask], block_ids=hb_arg, random_state=random_state
    )
    summary["calibrated_stacker_holdout_fold0"] = compute_classification_and_calibration_metrics(
        y_sub[hold_mask], oof["stacker"][hold_mask], oof["stacker_p"][hold_mask], block_ids=hb_arg, random_state=random_state
    )

    if run_all_heads:
        summary["head_comparison_5cv"] = {
            "Calibrated_OOF_Stacker": summary["calibrated_stacker_5cv"],
            "Weighted_Soft_Vote_3211": summary["weighted_vote_5cv"],
            "Equal_Soft_Vote_1111": compute_classification_and_calibration_metrics(
                y_sub, oof["equal_vote"], oof["equal_vote_p"], block_ids=b_arg, random_state=random_state
            ),
            "Shrinkage_LDA": compute_classification_and_calibration_metrics(
                y_sub, oof["lda"], oof["lda_p"], block_ids=b_arg, random_state=random_state
            ),
            "Multinomial_LogReg": compute_classification_and_calibration_metrics(
                y_sub, oof["logreg"], oof["logreg_p"], block_ids=b_arg, random_state=random_state
            ),
            "Calibrated_RBF_SVM": compute_classification_and_calibration_metrics(
                y_sub, oof["svm_cal"], oof["svm_cal_p"], block_ids=b_arg, random_state=random_state
            ),
            "Cosine_kNN_k1": compute_classification_and_calibration_metrics(
                y_sub, oof["knn1_cos"], None, block_ids=b_arg, random_state=random_state
            ),
            "Cosine_kNN_k3_Dist": compute_classification_and_calibration_metrics(
                y_sub, oof["knn3_cos"], None, block_ids=b_arg, random_state=random_state
            ),
        }
    return summary, oof


def _run_mutation_seed_ablation(
    X6_ref: np.ndarray, y_ref: np.ndarray, blk_folds: np.ndarray, chk_folds: np.ndarray, b_ref: np.ndarray, pre_covs: tuple = None
):
    """Ablation 1 (Flaw #10): 5-seed Fixed vs Diversity-Adaptive vs Diversity+Stagnation on Holdout Fold 0."""
    results = {}
    if pre_covs is None:
        covs_all, bdims_all = MultiScaleTangentExtractor("tangent_fold", "non_overlapping", "speech10").precompute_view_covariances(X6_ref[:, 0], X6_ref)
    else:
        covs_all, bdims_all = pre_covs
    for proto, folds_arr, disjoint in [
        ("block_disjoint", blk_folds, True),
        ("exploratory_chunk", chk_folds, False),
    ]:
        tr, te = folds_arr != 0, folds_arr == 0
        ext = MultiScaleTangentExtractor(geometry="tangent_fold", subband_mode="non_overlapping").fit_from_covs([c[tr] for c in covs_all], bdims_all)
        sc = StandardScaler()
        Z_tr = sc.fit_transform(ext.transform_from_covs([c[tr] for c in covs_all]))
        Z_te = sc.transform(ext.transform_from_covs([c[te] for c in covs_all]))
        in_grp = b_ref[tr] if disjoint else None

        proto_res = {}
        for mode in ("fixed", "diversity_adaptive", "diversity_stagnation"):
            accs = []
            for seed in SEEDS_5:
                aga = MultiScaleBlockAGA(
                    block_dims=ext.block_dims_,
                    n_population=10,
                    n_generations=6,
                    cv_splits=3,
                    mutation_mode=mode,
                    random_state=seed,
                ).fit(Z_tr, y_ref[tr], groups=in_grp)
                wv = MultiMetricSoftVotingClassifier(3, (3.0, 2.0, 1.0, 1.0)).fit(aga.transform(Z_tr), y_ref[tr])
                accs.append(float(np.mean(wv.predict(aga.transform(Z_te)) == y_ref[te])))
            proto_res[mode] = {
                "seed_accs": [round(a, 4) for a in accs],
                "mean": round(float(np.mean(accs)), 4),
                "std": round(float(np.std(accs)), 4),
            }
        results[proto] = proto_res
    return results


def _run_continuous_window_and_filter_ablation(
    prov: dict, ref_idx: np.ndarray, blk_folds: np.ndarray
):
    """
    Ablation 4 (Flaw #16): Reconstructs continuous 8s (1,008-sample) reference blocks (`328` blocks)
    and evaluates (1) edge-transient discrepancy: filter continuous block BEFORE slicing vs filter isolated 1s epoch;
    (2) continuous non-overlapping 1s, 2s, 4s, and 8s window lengths inside 5-fold block CV.
    """
    raw_unc = prov["raw_epochs_uncentered"][ref_idx]
    y_ref = prov["y"][ref_idx]
    b_ref = prov["block_ids"][ref_idx]
    c_ref = prov["chunk_ids"][ref_idx]

    Xc, yc, bc = reconstruct_continuous_8s_blocks(raw_unc, y_ref, b_ref, c_ref, overlap_samples=48, detrend=True)

    # Edge-transient measurement: filter alpha/beta band on continuous 8s vs isolated 1s chunk 0
    alpha_band = [(8.0, 13.0)]
    cont_filt = bandpass_filter_bank(Xc, alpha_band, fs=SAMPLING_RATE)[0][:, :, :SAMPLES_PER_EPOCH]
    iso_slice = Xc[:, :, :SAMPLES_PER_EPOCH]
    iso_filt = bandpass_filter_bank(iso_slice, alpha_band, fs=SAMPLING_RATE)[0]

    edge_diff = np.abs(cont_filt[:, :, :16] - iso_filt[:, :, :16])
    mid_diff = np.abs(cont_filt[:, :, 16:112] - iso_filt[:, :, 16:112])
    transient_diag = {
        "n_continuous_blocks": int(len(Xc)),
        "continuous_samples": int(Xc.shape[2]),
        "edge16_mean_abs_diff_uv": round(float(np.mean(edge_diff)), 4),
        "edge16_max_abs_diff_uv": round(float(np.max(edge_diff)), 4),
        "interior_mean_abs_diff_uv": round(float(np.mean(mid_diff)), 4),
    }

    # Block -> fold map matching canonical 5-fold block splits
    blk2fold = {}
    for bi, fi in zip(b_ref, blk_folds):
        blk2fold[int(bi)] = int(fi)
    cont_fids = np.array([blk2fold[int(b)] for b in bc], dtype=np.int64)

    # Filter full continuous recordings cleanly BEFORE slicing into 1s / 2s / 4s / 8s windows
    canonical_cutoffs = [CANONICAL_BAND_CUTOFFS[k] for k in ("delta", "theta", "alpha", "beta", "gamma")]
    full_6b = [Xc.astype(np.float64)] + bandpass_filter_bank(Xc, canonical_cutoffs, fs=SAMPLING_RATE)

    win_results = {}
    for w_label, w_samples in [("1s_128pts", 128), ("2s_256pts", 256), ("4s_512pts", 512), ("8s_1008pts", 1008)]:
        n_win_per_blk = 1008 // w_samples
        win_sigs = []  # list per band of (N_win, 14, w_samples)
        for b_tensor in full_6b:
            slices = [b_tensor[:, :, w * w_samples : (w + 1) * w_samples] for w in range(n_win_per_blk)]
            win_sigs.append(np.concatenate(slices, axis=0))
        # Repeat labels/blocks matching slice ordering (w runs outer, block runs inner)
        w_y = np.tile(yc, n_win_per_blk)
        w_blk = np.tile(bc, n_win_per_blk)
        w_fid = np.tile(cont_fids, n_win_per_blk)

        # Window-level & block-probability-averaged Log-Euclidean + LogReg 5-fold CV
        classes = np.unique(yc)
        oof_win_p = np.zeros(len(w_y), dtype=np.int64)
        oof_win_prob = np.zeros((len(w_y), len(classes)), dtype=np.float64)
        for fid in range(5):
            te = w_fid == fid
            tr = ~te
            X_tr_f = np.hstack([_spd_tangent_batch(bt[tr], reg=1e-4) for bt in win_sigs])
            X_te_f = np.hstack([_spd_tangent_batch(bt[te], reg=1e-4) for bt in win_sigs])
            sc = StandardScaler().fit(X_tr_f)
            lr = LogisticRegression(C=0.1, max_iter=2000, tol=1e-3, random_state=42).fit(sc.transform(X_tr_f), w_y[tr])
            oof_win_p[te] = lr.predict(sc.transform(X_te_f))
            oof_win_prob[te] = lr.predict_proba(sc.transform(X_te_f))

        # Block-level probability averaging across windows in each 8s block
        blk_preds = np.zeros(len(yc), dtype=np.int64)
        for j, blk_id in enumerate(bc):
            mk = w_blk == blk_id
            blk_preds[j] = classes[np.argmax(np.mean(oof_win_prob[mk], axis=0))]

        win_results[w_label] = {
            "window_samples": w_samples,
            "windows_per_block": n_win_per_blk,
            "window_level_block_disjoint_acc": round(float(np.mean(oof_win_p == w_y)), 4),
            "block_aggregated_acc": round(float(np.mean(blk_preds == yc)), 4),
        }

    return transient_diag, win_results


def _save_improved_cm(cm_blk, acc_blk, cm_chk, acc_chk, save_path: str):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.6), dpi=300)
    short_cls = ["Rest", "Help", "Bath", "Pain", "Thanks", "Hungry", "No", "Thirsty", "Yes"]
    sns.heatmap(cm_blk, annot=True, fmt="d", cmap="YlGnBu", xticklabels=short_cls, yticklabels=short_cls, ax=ax1, cbar=False)
    ax1.set_title(
        f"Stage 2 Primary Protocol: Block-Disjoint Nested 5-CV (N_ref=3,936, 328 Blocks)\n"
        f"True Fold-Tangent MDRC-AGA + Calibrated Stacker: {acc_blk*100:.2f}% (Chance: 11.11%)",
        fontsize=10.5, fontweight="bold"
    )
    ax1.set_xlabel("Predicted Word")
    ax1.set_ylabel("True Word")

    sns.heatmap(cm_chk, annot=True, fmt="d", cmap="Greens", xticklabels=short_cls, yticklabels=short_cls, ax=ax2, cbar=False)
    ax2.set_title(
        f"Stage 2 Exploratory Protocol: Overlapping-Chunk Nested 5-CV (Leakage Upper Bound)\n"
        f"MDRC-AGA + Soft Vote/Stacker Accuracy: {acc_chk*100:.2f}%",
        fontsize=10.5, fontweight="bold"
    )
    ax2.set_xlabel("Predicted Word")
    ax2.set_ylabel("True Word")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def run_improved_pipeline(data_dir: str = "data", save_dir: str = "results", random_state: int = 42):
    os.makedirs(save_dir, exist_ok=True)
    t_start = time.time()
    print("=" * 78)
    print("  STAGE 2: MDRC-AGA WITH NESTED OPTIMIZATION, TRUE TANGENT SPACE & CALIBRATION")
    print("  Side-by-Side: Leakage-Safe Block-Disjoint Primary || Exploratory Chunk Upper Bound")
    print("=" * 78)

    prov = load_eegis_6band_with_provenance(data_dir=data_dir, verify_cache=True, write_manifest=False)
    splits = ensure_canonical_splits(prov, save_dir=save_dir, random_state=random_state)

    ref_idx = splits["ref_idx"]
    blk_folds = splits["blk_fold_ids"]
    chk_folds = splits["chk_fold_ids"]
    ts_info = splits["ts_info"]

    X6_ref = prov["X"][ref_idx]
    y_ref = prov["y"][ref_idx]
    b_ref = prov["block_ids"][ref_idx]

    print("[*] Precomputing multi-scale SPD covariance tensors cleanly per isolated epoch...", flush=True)
    _pre_ext = MultiScaleTangentExtractor("tangent_fold", "non_overlapping", "speech10", fs=SAMPLING_RATE)
    pre_covs_nonov_sp10 = _pre_ext.precompute_view_covariances(X6_ref[:, 0], X6_ref)

    # 1. Primary Leakage-Safe Block-Disjoint Nested 5-CV (True Fold Tangent Space + Non-Overlapping Sub7)
    print("\n[1] Running Primary Block-Disjoint Nested 5-Fold CV (True C_ref Tangent Space + GroupKFold AGA)...", flush=True)
    blk_sum, blk_oof = _run_nested_multiscale_cv(
        X6_ref, y_ref, blk_folds, b_ref,
        enforce_disjoint=True,
        geometry="tangent_fold",
        subband_mode="non_overlapping",
        local_montage="speech10",
        mutation_mode="diversity_adaptive",
        n_pop=14, n_gen=8, random_state=random_state, run_all_heads=True,
        pre_covs=pre_covs_nonov_sp10,
    )

    # 2. Secondary Exploratory Overlapping-Chunk Nested 5-CV
    print("[2] Running Exploratory Overlapping-Chunk Nested 5-Fold CV (Leakage-Disclosed Comparison)...", flush=True)
    chk_sum, chk_oof = _run_nested_multiscale_cv(
        X6_ref, y_ref, chk_folds, b_ref,
        enforce_disjoint=False,
        geometry="tangent_fold",
        subband_mode="non_overlapping",
        local_montage="speech10",
        mutation_mode="diversity_adaptive",
        n_pop=14, n_gen=8, random_state=random_state, run_all_heads=True,
        pre_covs=pre_covs_nonov_sp10,
    )

    # 3. Geometry Ablation: Identity-Centered Log-Euclidean vs True Fold Tangent Space (C_ref)
    print("[3] Running Geometry Ablation (Identity Log-Euclidean vs True Fold Tangent Space)...", flush=True)
    id_blk_sum, _ = _run_nested_multiscale_cv(
        X6_ref, y_ref, blk_folds, b_ref,
        enforce_disjoint=True, geometry="log_euclid_identity",
        subband_mode="non_overlapping", local_montage="speech10",
        n_pop=10, n_gen=6, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
        pre_covs=pre_covs_nonov_sp10,
    )
    id_chk_sum, _ = _run_nested_multiscale_cv(
        X6_ref, y_ref, chk_folds, b_ref,
        enforce_disjoint=False, geometry="log_euclid_identity",
        subband_mode="non_overlapping", local_montage="speech10",
        n_pop=10, n_gen=6, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
        pre_covs=pre_covs_nonov_sp10,
    )

    # 4. Controlled Scientific Ablations (Flaws #10, #15, #16, #17)
    print("[4] Running 5-Seed Mutation Control Ablation (Fixed vs Diversity vs Stagnation)...", flush=True)
    mutation_ablation = _run_mutation_seed_ablation(X6_ref, y_ref, blk_folds, chk_folds, b_ref, pre_covs=pre_covs_nonov_sp10)

    print("[5] Running Sub-Band Overlap Ablation (Non-Overlapping vs Overlapping)...", flush=True)
    pre_covs_ov_sp10 = MultiScaleTangentExtractor("tangent_fold", "overlapping", "speech10", fs=SAMPLING_RATE).precompute_view_covariances(X6_ref[:, 0], X6_ref)
    ov_blk_sum, _ = _run_nested_multiscale_cv(
        X6_ref, y_ref, blk_folds, b_ref,
        enforce_disjoint=True, geometry="tangent_fold", subband_mode="overlapping",
        n_pop=10, n_gen=6, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
        pre_covs=pre_covs_ov_sp10,
    )
    ov_chk_sum, _ = _run_nested_multiscale_cv(
        X6_ref, y_ref, chk_folds, b_ref,
        enforce_disjoint=False, geometry="tangent_fold", subband_mode="overlapping",
        n_pop=10, n_gen=6, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
        pre_covs=pre_covs_ov_sp10,
    )

    print("[6] Running Electrode Montage Ablation (Speech-10 vs All-14 vs Left-7 vs Occipital-4)...", flush=True)
    montage_ablation = {}
    tr0_b, te0_b = blk_folds != 0, blk_folds == 0
    tr0_c, te0_c = chk_folds != 0, chk_folds == 0
    for m_name in ("speech10", "all14", "left7", "occipital4"):
        c_m, bd_m = MultiScaleTangentExtractor("tangent_fold", "non_overlapping", m_name).precompute_view_covariances(X6_ref[:, 0], X6_ref)
        ext_b = MultiScaleTangentExtractor("tangent_fold", "non_overlapping", m_name).fit_from_covs([c[tr0_b] for c in c_m], bd_m)
        sc_b = StandardScaler()
        s_off = bd_m[0] + bd_m[1]
        Fb_tr = sc_b.fit_transform(ext_b.transform_from_covs([c[tr0_b] for c in c_m])[:, s_off:])
        Fb_te = sc_b.transform(ext_b.transform_from_covs([c[te0_b] for c in c_m])[:, s_off:])
        acc_b_only = float(np.mean(LogisticRegression(C=0.1, max_iter=2000, tol=1e-3, random_state=random_state).fit(Fb_tr, y_ref[tr0_b]).predict(Fb_te) == y_ref[te0_b]))

        ext_c = MultiScaleTangentExtractor("tangent_fold", "non_overlapping", m_name).fit_from_covs([c[tr0_c] for c in c_m], bd_m)
        sc_c = StandardScaler()
        Fc_tr = sc_c.fit_transform(ext_c.transform_from_covs([c[tr0_c] for c in c_m])[:, s_off:])
        Fc_te = sc_c.transform(ext_c.transform_from_covs([c[te0_c] for c in c_m])[:, s_off:])
        acc_c_only = float(np.mean(MultiMetricSoftVotingClassifier(3).fit(Fc_tr, y_ref[tr0_c]).predict(Fc_te) == y_ref[te0_c]))
        montage_ablation[m_name] = {
            "n_channels": len(ext_b.montage_idx),
            "local_block_dim": ext_b.block_dims_[2],
            "block_disjoint_local_logreg_acc": round(acc_b_only, 4),
            "exploratory_chunk_local_vote_acc": round(acc_c_only, 4),
        }

    print("[7] Running Continuous 8s Block Window-Length & Filter-Transient Diagnostics...", flush=True)
    transient_diag, window_ablation = _run_continuous_window_and_filter_ablation(prov, ref_idx, blk_folds)

    # 8. Binary Subtasks under BOTH protocols
    print("[8] Running Binary Subtasks under BOTH Block-Disjoint & Exploratory Protocols...", flush=True)
    binary_benchmarks = {}
    for c_pos, c_neg, b_label in [
        (8, 6, "Yes (Si) vs No [Paper Binary]"),
        (1, 0, "Help vs Rest [Emergency]"),
        (1, 3, "Help vs Pain [Emergency]"),
        (5, 7, "Hungry vs Thirsty [Emergency]"),
        (8, 1, "Yes vs Help [Emergency]"),
    ]:
        mk = (y_ref == c_pos) | (y_ref == c_neg)
        yb = (y_ref[mk] == c_pos).astype(np.int64)
        X6b = X6_ref[mk]
        gb = b_ref[mk]

        uniq_b, fpos = np.unique(gb, return_index=True)
        by = yb[fpos]
        b2f = {}
        for fid, (_, idx_b) in enumerate(StratifiedKFold(5, shuffle=True, random_state=random_state).split(uniq_b, by)):
            for p in idx_b:
                b2f[int(uniq_b[p])] = fid
        fids_b = np.array([b2f[int(b)] for b in gb], dtype=np.int64)

        fids_c = np.zeros(len(yb), dtype=np.int64)
        for fid, (_, idx_c) in enumerate(StratifiedKFold(5, shuffle=True, random_state=random_state).split(X6b, yb)):
            fids_c[idx_c] = fid

        pre_covs_bin = ([c[mk] for c in pre_covs_nonov_sp10[0]], pre_covs_nonov_sp10[1])
        res_b, _ = _run_nested_multiscale_cv(
            X6b, yb, fids_b, gb, enforce_disjoint=True,
            n_pop=10, n_gen=5, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
            pre_covs=pre_covs_bin,
        )
        res_c, _ = _run_nested_multiscale_cv(
            X6b, yb, fids_c, gb, enforce_disjoint=False,
            n_pop=10, n_gen=5, inner_cv_splits=3, random_state=random_state, run_all_heads=False,
            pre_covs=pre_covs_bin,
        )
        binary_benchmarks[b_label] = {
            "n_samples": int(len(yb)),
            "n_blocks": int(len(uniq_b)),
            "block_disjoint_5cv": {
                "stacker": res_b["calibrated_stacker_5cv"],
                "weighted_vote": res_b["weighted_vote_5cv"],
            },
            "exploratory_chunk_5cv": {
                "stacker": res_c["calibrated_stacker_5cv"],
                "weighted_vote": res_c["weighted_vote_5cv"],
            },
        }

    # 9. Fit & Export Leakage-Free Deployment Model (N_ref = 3,936; all 108 test_signals siblings excluded)
    print("[9] Fitting & exporting leakage-free deployment bundle & profiling offline epoch latency...", flush=True)
    deploy_ext = MultiScaleTangentExtractor(
        geometry="tangent_fold", subband_mode="non_overlapping", local_montage="speech10", fs=SAMPLING_RATE
    )
    F_dep = deploy_ext.fit_from_covs(pre_covs_nonov_sp10[0], pre_covs_nonov_sp10[1]).transform_from_covs(pre_covs_nonov_sp10[0])
    deploy_scaler = StandardScaler().fit(F_dep)
    Z_dep = deploy_scaler.transform(F_dep)
    deploy_aga = MultiScaleBlockAGA(
        block_dims=deploy_ext.block_dims_, n_population=14, n_generations=8,
        cv_splits=5, mutation_mode="diversity_adaptive", random_state=random_state,
    ).fit(Z_dep, y_ref, groups=b_ref)
    Zw_dep = deploy_aga.transform(Z_dep)
    deploy_stacker = CalibratedManifoldStacker(cv_splits=5, random_state=random_state).fit(Zw_dep, y_ref, groups=b_ref)
    deploy_voter = MultiMetricSoftVotingClassifier(k_base=3, weights=(3.0, 2.0, 1.0, 1.0)).fit(Zw_dep, y_ref)

    # Profile step-by-step latency cleanly on 9 offline CSVs
    reg_path = os.path.join("test_signals", "ground_truth_registry.json")
    t_load_list, t_prep_list, t_feat_list, t_cls_list, t_tot_list = [], [], [], [], []
    ts_correct_st, ts_correct_vt, ts_preds_st, ts_preds_vt = 0, 0, [], []
    if os.path.exists(reg_path):
        with open(reg_path, "r", encoding="utf-8") as f:
            reg_items = json.load(f)
        for item in reg_items:
            p_csv = item["file_csv"]
            t0 = time.perf_counter()
            raw_ep = load_eeg_epoch_file(p_csv, expected_fs=SAMPLING_RATE, min_samples=SAMPLES_PER_EPOCH)
            t1 = time.perf_counter()
            proc_ep = preprocess_epoch(raw_ep, expected_channels=14, min_samples=SAMPLES_PER_EPOCH)
            t2 = time.perf_counter()
            fv = deploy_ext.transform(proc_ep[None, :, :])
            zv = deploy_aga.transform(deploy_scaler.transform(fv))
            t3 = time.perf_counter()
            p_st = int(deploy_stacker.predict(zv)[0])
            p_vt = int(deploy_voter.predict(zv)[0])
            t4 = time.perf_counter()

            t_load_list.append((t1 - t0) * 1000.0)
            t_prep_list.append((t2 - t1) * 1000.0)
            t_feat_list.append((t3 - t2) * 1000.0)
            t_cls_list.append((t4 - t3) * 1000.0)
            t_tot_list.append((t4 - t0) * 1000.0)

            ts_preds_st.append(p_st)
            ts_preds_vt.append(p_vt)
            truth = int(item["true_class_id"])
            if p_st == truth:
                ts_correct_st += 1
            if p_vt == truth:
                ts_correct_vt += 1

    latency_breakdown = {
        "note": "Offline per-128-sample-CSV-epoch timing on workstation CPU (NOT end-to-end streaming hardware acquisition/DAC loop).",
        "mean_file_load_ms": round(float(np.mean(t_load_list)), 2) if t_load_list else 0.0,
        "mean_preprocess_ms": round(float(np.mean(t_prep_list)), 2) if t_prep_list else 0.0,
        "mean_feature_extract_ms": round(float(np.mean(t_feat_list)), 2) if t_feat_list else 0.0,
        "mean_classify_ms": round(float(np.mean(t_cls_list)), 2) if t_cls_list else 0.0,
        "mean_total_offline_epoch_ms": round(float(np.mean(t_tot_list)), 2) if t_tot_list else 0.0,
    }

    # Confusion Matrices & Reports
    cm_blk = confusion_matrix(y_ref, blk_oof["stacker"])
    cm_chk = confusion_matrix(y_ref, chk_oof["weighted_vote"])
    _save_improved_cm(
        cm_blk,
        blk_sum["calibrated_stacker_5cv"]["accuracy"],
        cm_chk,
        chk_sum["weighted_vote_5cv"]["accuracy"],
        os.path.join(save_dir, "confusion_matrix_improved.png"),
    )

    cls_rep_blk = classification_report(y_ref, blk_oof["stacker"], target_names=WORD_CLASSES, output_dict=True, zero_division=0)
    cls_rep_chk = classification_report(y_ref, chk_oof["weighted_vote"], target_names=WORD_CLASSES, output_dict=True, zero_division=0)

    yn_bench = binary_benchmarks["Yes (Si) vs No [Paper Binary]"]
    metrics = {
        "code_version": CODE_VERSION,
        "model_name": "Stage 2 MDRC-AGA Framework (Fold-Tangent + Non-Overlapping 7B + Group-Safe Block-Weighting + Calibrated Stacker)",
        "architecture_clarification": {
            "active_feature_count": int(deploy_aga.active_feature_count_),
            "total_feature_count": int(deploy_aga.total_feature_count_),
            "selection_mechanism": "3-block scalar weighting via MultiScaleBlockAGA (all 1,695 dims remain active; NOT feature elimination).",
            "stacker_vs_voter": "CalibratedManifoldStacker produces OOF multinomial Platt-calibrated probabilities; MultiMetricSoftVotingClassifier produces un-calibrated heuristic [3:2:1:1] neighbor vote fractions.",
            "subject_ids_recoverable": False,
            "excluded_test_signal_blocks": ts_info["excl_blocks"],
            "excluded_sibling_chunks": ts_info["excl_chunk_count"],
            "n_ref_trials": int(len(ref_idx)),
            "n_ref_blocks": int(len(np.unique(b_ref))),
        },
        "block_disjoint_primary": {
            "protocol_description": "Nested 5-Fold Class-Stratified Block-Disjoint CV over 328 blocks (N_ref=3,936). Fold 0 = 20% locked block holdout.",
            "calibrated_stacker_5cv": blk_sum["calibrated_stacker_5cv"],
            "weighted_vote_5cv": blk_sum["weighted_vote_5cv"],
            "calibrated_stacker_holdout_fold0": blk_sum["calibrated_stacker_holdout_fold0"],
            "weighted_vote_holdout_fold0": blk_sum["weighted_vote_holdout_fold0"],
            "head_comparison_5cv": blk_sum["head_comparison_5cv"],
            "mean_block_weights": blk_sum["mean_weights"],
            "fold_weights": blk_sum["fold_weights"],
            "fold0_aga_history": blk_sum["fold0_aga_history"],
            "yes_no_5cv": yn_bench["block_disjoint_5cv"],
            "per_class_report": cls_rep_blk,
        },
        "exploratory_chunk_secondary": {
            "leakage_disclosure": OVERLAP_DISCLOSURE,
            "calibrated_stacker_5cv": chk_sum["calibrated_stacker_5cv"],
            "weighted_vote_5cv": chk_sum["weighted_vote_5cv"],
            "calibrated_stacker_holdout_fold0": chk_sum["calibrated_stacker_holdout_fold0"],
            "weighted_vote_holdout_fold0": chk_sum["weighted_vote_holdout_fold0"],
            "head_comparison_5cv": chk_sum["head_comparison_5cv"],
            "mean_block_weights": chk_sum["mean_weights"],
            "fold_weights": chk_sum["fold_weights"],
            "fold0_aga_history": chk_sum["fold0_aga_history"],
            "yes_no_5cv": yn_bench["exploratory_chunk_5cv"],
            "per_class_report": cls_rep_chk,
        },
        "ablations": {
            "geometry_tangent_fold_vs_identity_log_euclid": {
                "block_disjoint_identity_vote_5cv": id_blk_sum["weighted_vote_5cv"]["accuracy"],
                "block_disjoint_tangent_fold_vote_5cv": blk_sum["weighted_vote_5cv"]["accuracy"],
                "block_disjoint_tangent_fold_stacker_5cv": blk_sum["calibrated_stacker_5cv"]["accuracy"],
                "exploratory_chunk_identity_vote_5cv": id_chk_sum["weighted_vote_5cv"]["accuracy"],
                "exploratory_chunk_tangent_fold_vote_5cv": chk_sum["weighted_vote_5cv"]["accuracy"],
                "exploratory_chunk_tangent_fold_stacker_5cv": chk_sum["calibrated_stacker_5cv"]["accuracy"],
            },
            "mutation_5seed_control": mutation_ablation,
            "subband_overlap_control": {
                "block_disjoint_non_overlapping_vote": blk_sum["weighted_vote_5cv"]["accuracy"],
                "block_disjoint_overlapping_vote": ov_blk_sum["weighted_vote_5cv"]["accuracy"],
                "exploratory_chunk_non_overlapping_vote": chk_sum["weighted_vote_5cv"]["accuracy"],
                "exploratory_chunk_overlapping_vote": ov_chk_sum["weighted_vote_5cv"]["accuracy"],
            },
            "montage_topology_ablation": montage_ablation,
            "filter_transient_diagnostics": transient_diag,
            "continuous_window_length_ablation": window_ablation,
        },
        "binary_benchmarks": binary_benchmarks,
        "offline_demo_9_test_signals": {
            "note": "Small 9-sample offline format demo ONLY (all 108 sibling chunks of the 9 source blocks excluded from training N_ref=3,936).",
            "total": len(ts_info["ts_labels"]),
            "stacker_correct": ts_correct_st,
            "stacker_accuracy": round(ts_correct_st / max(len(ts_info["ts_labels"]), 1), 4),
            "stacker_preds": ts_preds_st,
            "soft_voter_correct": ts_correct_vt,
            "soft_voter_accuracy": round(ts_correct_vt / max(len(ts_info["ts_labels"]), 1), 4),
            "soft_voter_preds": ts_preds_vt,
        },
        "latency_breakdown": latency_breakdown,
        "elapsed_sec": round(time.time() - t_start, 2),
    }

    metrics_file = os.path.join(save_dir, "improved_pipeline_metrics.json")
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    model_pkg = {
        "mode": "mdrc_aga_v4_fold_tangent_calibrated",
        "code_version": CODE_VERSION,
        "tangent_extractor": deploy_ext,
        "scaler": deploy_scaler,
        "aga": deploy_aga,
        "scale_weights": deploy_aga.best_weights_.copy(),
        "block_dims": deploy_ext.block_dims_,
        "ensemble": deploy_stacker,
        "soft_voter": deploy_voter,
        "channel_names": CHANNEL_NAMES,
        "band_names": BAND_NAMES,
        "class_map": CLASS_MAP,
        "n_ref_trials": int(len(ref_idx)),
        "excluded_blocks": ts_info["excl_blocks"],
        "is_calibrated_probabilities": True,
    }
    model_file = os.path.join(save_dir, "best_improved_ensemble.pkl")
    with open(model_file, "wb") as f:
        pickle.dump(model_pkg, f)

    print("\n" + "=" * 78)
    print("  STAGE 2 VERIFIED SIDE-BY-SIDE SUMMARY (ZERO CV LEAKAGE / ZERO OVERRIDES)")
    print("=" * 78)
    sb = blk_sum["calibrated_stacker_5cv"]
    vb = blk_sum["weighted_vote_5cv"]
    sc_m = chk_sum["calibrated_stacker_5cv"]
    vc_m = chk_sum["weighted_vote_5cv"]
    print(f"  [Primary Block-Disjoint 5-CV] Stacker Acc={sb['accuracy']*100:.2f}% (BalAcc={sb['balanced_accuracy']*100:.2f}%, Brier={sb['brier_score']:.3f}, ECE={sb['ece_10bin']:.3f})")
    print(f"  [Primary Block-Disjoint 5-CV] Vote3211 Acc={vb['accuracy']*100:.2f}% (Brier={vb['brier_score']:.3f}, ECE={vb['ece_10bin']:.3f})")
    print(f"  [Primary Block-Disjoint Yes/No] Stacker={yn_bench['block_disjoint_5cv']['stacker']['accuracy']*100:.2f}% | Vote={yn_bench['block_disjoint_5cv']['weighted_vote']['accuracy']*100:.2f}%")
    print("-" * 78)
    print(f"  [Exploratory Chunk 5-CV — OVERLAP] Vote3211 Acc={vc_m['accuracy']*100:.2f}% (Brier={vc_m['brier_score']:.3f}, ECE={vc_m['ece_10bin']:.3f})")
    print(f"  [Exploratory Chunk 5-CV — OVERLAP] Stacker Acc={sc_m['accuracy']*100:.2f}% (Brier={sc_m['brier_score']:.3f}, ECE={sc_m['ece_10bin']:.3f})")
    print(f"  [Exploratory Chunk Yes/No] Stacker={yn_bench['exploratory_chunk_5cv']['stacker']['accuracy']*100:.2f}% | Vote={yn_bench['exploratory_chunk_5cv']['weighted_vote']['accuracy']*100:.2f}%")
    print(f"  [Offline 9-Signal Demo (108 sibs excl)] Stacker={ts_correct_st}/{len(ts_info['ts_labels'])} | Vote={ts_correct_vt}/{len(ts_info['ts_labels'])} | Total={latency_breakdown['mean_total_offline_epoch_ms']} ms")
    print("=" * 78)
    return metrics


if __name__ == "__main__":
    run_improved_pipeline()
