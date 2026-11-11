"""
baseline_paper.py
=================
STAGE 1: Exact Baseline Replication of Research Paper:
"Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram
Signal Classification" (Lara-Arellano et al., Eng 2025).

Components:
1. Multi-Domain Features (Time Moments, Hjorth, Welch Spectral Bands) -> 322 features
2. Standard Genetic Algorithm (Fixed mutation rate, single-objective fitness)
3. Standard Single Classifier: Support Vector Machine (RBF kernel)
"""

import os
import sys
import json
import numpy as np

# Ensure src/ is in Python path for clean modular imports
src_dir = os.path.join(os.path.dirname(__file__), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

from dataset_loader import load_eegis_dataset, CLASS_MAP
from eeg_features import extract_dataset_features
from models.ga_feature_selector import GeneticFeatureSelector


def run_baseline_paper(data_dir: str = "data", save_dir: str = "results", n_generations: int = 5, test_size: float = 0.20):
    os.makedirs(save_dir, exist_ok=True)
    print("=" * 78)
    print("   STAGE 1: RESEARCH PAPER BASELINE (LARA-ARELLANO ET AL., MDPI ENG 2025)")
    print("            [EVALUATED ON REAL MENDELEY EEGIS IN-VIVO DATASET (N=4,044)]")
    print(f"            [9-CLASS STRATIFIED SPLIT: {int((1-test_size)*100)}% Train / {int(test_size*100)}% Test]")
    print("=" * 78)

    # 1. Load Real Raw Features (322 multi-domain moments)
    real_feats_path = os.path.join(data_dir, "eegis_real_features.npz")
    if os.path.exists(real_feats_path):
        print(f"[*] Loading pre-extracted real EEGIS feature bundle: '{real_feats_path}'...")
        bundle = np.load(real_feats_path)
        feat_matrix = bundle["X"][:, :322]
        y = bundle["y"]
        print(f"[+] Loaded {len(feat_matrix)} real EEG trials with {feat_matrix.shape[1]} standard raw features.")
    else:
        X, y, channel_names = load_eegis_dataset(data_dir=data_dir)
        print("[*] Extracting Paper Features (Statistical Moments, Hjorth, Welch PSD)...")
        feat_matrix, _ = extract_dataset_features(X, channel_names)

    # 2. Balanced 720-trial Static GA + Single SVM replication (clean 80/class evaluation)
    sub_idx = np.concatenate([np.where(y == c)[0][:80] for c in range(9)])
    sss_bal = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    b_tr, b_te = next(sss_bal.split(feat_matrix[sub_idx], y[sub_idx]))
    X_bal_tr, X_bal_te = feat_matrix[sub_idx][b_tr], feat_matrix[sub_idx][b_te]
    y_bal_tr, y_bal_te = y[sub_idx][b_tr], y[sub_idx][b_te]

    sc_bal = StandardScaler()
    X_bal_tr_s = sc_bal.fit_transform(X_bal_tr)
    X_bal_te_s = sc_bal.transform(X_bal_te)

    print("\n[*] Running Standard Static Genetic Algorithm (Balanced 720 Cohort)...")
    ga = GeneticFeatureSelector(
        n_population=24, n_generations=n_generations, crossover_rate=0.8,
        mutation_rate=0.03, parsimony_penalty=0.01, cv_splits=3, random_state=42
    )
    ga.fit(X_bal_tr_s, y_bal_tr)
    selected_count = int(np.sum(ga.best_mask_))
    clf_bal = SVC(kernel="rbf", C=2.0, gamma="scale", random_state=42).fit(ga.transform(X_bal_tr_s), y_bal_tr)
    acc_bal_ga_svm = float(accuracy_score(y_bal_te, clf_bal.predict(ga.transform(X_bal_te_s))))

    # 3. Full 4,044-trial 80/20 evaluation using Raw 322D SVM & 6-Band Stats kNN (k=7)
    sss_full = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    tr_full, te_full = next(sss_full.split(feat_matrix, y))
    sc_full = StandardScaler()
    X_tr_f = sc_full.fit_transform(feat_matrix[tr_full])
    X_te_f = sc_full.transform(feat_matrix[te_full])
    clf_full = SVC(kernel="rbf", C=2.0, gamma="scale", random_state=42).fit(X_tr_f, y[tr_full])
    y_pred = clf_full.predict(X_te_f)

    # Also test Paper-style kNN(k=7) on 6-Band Statistics (if cached)
    acc_6b_knn7_9c = None
    acc_6b_knn7_yesno = None
    fb_all_path = os.path.join(data_dir, "eegis_6band_features.npz")
    if os.path.exists(fb_all_path):
        F_stat = np.load(fb_all_path)["F_stat"]
        sc_6b = StandardScaler()
        k7 = KNeighborsClassifier(n_neighbors=7, weights="uniform").fit(sc_6b.fit_transform(F_stat[tr_full]), y[tr_full])
        acc_6b_knn7_9c = float(accuracy_score(y[te_full], k7.predict(sc_6b.transform(F_stat[te_full]))))

        mask_yn = (y == 8) | (y == 6)
        y_yn = (y[mask_yn] == 8).astype(int)
        t_yn, e_yn = next(StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42).split(F_stat[mask_yn], y_yn))
        sc_yn = StandardScaler()
        k7_yn = KNeighborsClassifier(n_neighbors=7, weights="uniform").fit(sc_yn.fit_transform(F_stat[mask_yn][t_yn]), y_yn[t_yn])
        acc_6b_knn7_yesno = float(accuracy_score(y_yn[e_yn], k7_yn.predict(sc_yn.transform(F_stat[mask_yn][e_yn]))))

    test_acc = float(accuracy_score(y[te_full], y_pred))
    macro_prec = float(precision_score(y[te_full], y_pred, average="macro", zero_division=0))
    macro_rec = float(recall_score(y[te_full], y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y[te_full], y_pred, average="macro", zero_division=0))

    target_names = [CLASS_MAP[i] for i in sorted(CLASS_MAP.keys())]
    report_dict = classification_report(y[te_full], y_pred, target_names=target_names, output_dict=True, zero_division=0)
    report_text = classification_report(y[te_full], y_pred, target_names=target_names, zero_division=0)

    print("\n" + "=" * 78)
    print("        STAGE 1 BASELINE COMPREHENSIVE EVALUATION")
    print("=" * 78)
    print(f"[*] Full 4,044 Raw Moments SVM (80/20, N=809)      : {test_acc * 100:.2f}% (F1={macro_f1:.4f})")
    print(f"[*] Balanced 720 Static GA + SVM ({selected_count}/322 feats): {acc_bal_ga_svm * 100:.2f}%")
    if acc_6b_knn7_9c is not None:
        print(f"[*] Paper-Style 6-Band Stats kNN (k=7) 9-Class     : {acc_6b_knn7_9c * 100:.2f}%")
        print(f"[*] Paper-Style 6-Band Stats kNN (k=7) Yes/No      : {acc_6b_knn7_yesno * 100:.2f}%")
    print(f"[*] Published Primary Paper Target (Binary Si/No)  : 96.00% (8 electrodes, 103 GA feats, kNN k=7)")
    print("-" * 78)
    print(report_text)
    print("=" * 78)

    metrics = {
        "model_name": "Paper Baseline (Raw Moments / Static GA + Single SVM)",
        "published_paper_binary_yes_no_acc": 0.96,
        "published_paper_recall": 0.97,
        "published_paper_f1": 0.94,
        "train_test_split": f"{int((1-test_size)*100)}/{int(test_size*100)}",
        "train_samples": int(len(tr_full)),
        "test_samples": int(len(te_full)),
        "accuracy": test_acc,
        "balanced_720_ga_svm_accuracy": acc_bal_ga_svm,
        "six_band_stats_knn7_9class_acc": acc_6b_knn7_9c,
        "six_band_stats_knn7_yes_no_acc": acc_6b_knn7_yesno,
        "precision": macro_prec,
        "recall": macro_rec,
        "macro_f1": macro_f1,
        "n_original_features": int(feat_matrix.shape[1]),
        "n_selected_features": selected_count,
        "classification_method": "Single RBF SVM / Baseline kNN (k=7)",
        "per_class": report_dict
    }

    metrics_file = os.path.join(save_dir, "baseline_paper_metrics.json")
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[+] Saved baseline metrics to '{metrics_file}'")

    cm = confusion_matrix(y[te_full], y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=target_names, yticklabels=target_names)
    plt.title(f"Baseline Raw-Signal SVM Confusion Matrix (N=4,044 9-Class Acc: {test_acc*100:.2f}%)", fontsize=13)
    plt.xlabel("Predicted Imagined Word", fontsize=11)
    plt.ylabel("True Imagined Word", fontsize=11)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    cm_path = os.path.join(save_dir, "confusion_matrix_baseline.png")
    plt.savefig(cm_path, dpi=300)
    plt.close()
    print(f"[+] Baseline confusion matrix plot saved to '{cm_path}'")

    return metrics


if __name__ == "__main__":
    run_baseline_paper()
