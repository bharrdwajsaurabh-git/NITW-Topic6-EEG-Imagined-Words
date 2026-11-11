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

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

from dataset_loader import load_eegis_dataset, CLASS_MAP
from eeg_features import extract_dataset_features
from models.ga_feature_selector import GeneticFeatureSelector


def run_baseline_paper(data_dir: str = "data", save_dir: str = "results", n_generations: int = 5, test_size: float = 0.25):
    os.makedirs(save_dir, exist_ok=True)
    print("=" * 75)
    print("      STAGE 1: REPLICATION OF RESEARCH PAPER (LARA-ARELLANO ET AL. 2025)      ")
    print("               [EVALUATED ON REAL MENDELEY EEGIS IN-VIVO DATASET]             ")
    print(f"               [DATASET SPLIT: {int((1-test_size)*100)}% Train / {int(test_size*100)}% Test Stratified]")
    print("=" * 75)

    # 1. Load Real Features or Raw Data
    real_feats_path = os.path.join(data_dir, "eegis_real_features.npz")
    if os.path.exists(real_feats_path):
        print(f"[*] Loading pre-extracted real EEGIS feature bundle: '{real_feats_path}'...")
        bundle = np.load(real_feats_path)
        feat_matrix = bundle["X"][:, :322]  # First 322 columns are paper standard multi-domain moments
        y = bundle["y"]
        channel_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
        print(f"[+] Loaded {len(feat_matrix)} real EEG trials with {feat_matrix.shape[1]} standard features.")
    else:
        X, y, channel_names = load_eegis_dataset(data_dir=data_dir)
        print("[*] Extracting Paper Features (Statistical Moments, Hjorth, Welch PSD)...")
        feat_matrix, feat_names = extract_dataset_features(X, channel_names)

    # Use a balanced real cohort for evaluation (e.g. 720 trials across classes)
    sub_idx = []
    for c in range(9):
        c_idx = np.where(y == c)[0]
        sub_idx.extend(c_idx[:80])
    sub_idx = np.array(sub_idx)

    X_eval = feat_matrix[sub_idx]
    y_eval = y[sub_idx]

    # 3. Stratified Split (e.g. 75% Train, 25% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X_eval, y_eval, test_size=test_size, random_state=42, stratify=y_eval
    )
    print(f"[*] Dataset Partition: Train = {X_train.shape[0]} trials | Test = {X_test.shape[0]} trials (REAL EEG)")

    # 4. Standardize Features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 5. Standard Genetic Algorithm (Fixed Mutation Rate)
    print("\n[*] Running Standard Genetic Algorithm Feature Optimization...")
    ga = GeneticFeatureSelector(
        n_population=24,
        n_generations=n_generations,
        crossover_rate=0.8,
        mutation_rate=0.03,
        parsimony_penalty=0.01,
        cv_splits=3,
        random_state=42
    )
    ga.fit(X_train_scaled, y_train)

    X_train_opt = ga.transform(X_train_scaled)
    X_test_opt = ga.transform(X_test_scaled)
    selected_count = int(np.sum(ga.best_mask_))

    # 6. Fit Baseline Classifier (Single Support Vector Machine)
    print(f"\n[*] Training Single Support Vector Machine on {selected_count} selected features...")
    clf = SVC(kernel="rbf", C=2.0, gamma="scale", random_state=42)
    clf.fit(X_train_opt, y_train)

    # Pure organic prediction from the trained baseline model (zero artificial overrides)
    y_pred = clf.predict(X_test_opt)

    test_acc = float(accuracy_score(y_test, y_pred))
    macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    target_names = [CLASS_MAP[i] for i in sorted(list(CLASS_MAP.keys()))]
    report_dict = classification_report(y_test, y_pred, target_names=target_names, output_dict=True, zero_division=0)
    report_text = classification_report(y_test, y_pred, target_names=target_names, zero_division=0)

    print("\n" + "=" * 75)
    print("        STAGE 1 BASELINE PAPER COMPREHENSIVE EVALUATION")
    print("=" * 75)
    print(f"[*] TEST ACCURACY:    {test_acc * 100:.2f}%")
    print(f"[*] MACRO PRECISION:  {macro_prec:.4f}  (Positive Predictive Value)")
    print(f"[*] MACRO RECALL:     {macro_rec:.4f}  (Sensitivity / True Positive Rate)")
    print(f"[*] MACRO F1-SCORE:   {macro_f1:.4f}  (Harmonic Mean of Precision & Recall)")
    print("-" * 75)
    print("PER-WORD DETAILED CLASSIFICATION REPORT (PRECISION & RECALL):")
    print(report_text)
    print("=" * 75)

    metrics = {
        "model_name": "Paper Baseline (GA + Single SVM)",
        "train_test_split": f"{int((1-test_size)*100)}/{int(test_size*100)}",
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "accuracy": test_acc,
        "precision": macro_prec,
        "recall": macro_rec,
        "macro_f1": macro_f1,
        "n_original_features": int(feat_matrix.shape[1]),
        "n_selected_features": selected_count,
        "classification_method": "Single RBF SVM",
        "per_class": report_dict
    }

    metrics_file = os.path.join(save_dir, "baseline_paper_metrics.json")
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[+] Saved baseline metrics to '{metrics_file}'")

    # Plot Baseline Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=target_names, yticklabels=target_names)
    plt.title(f"Baseline Paper Replication Confusion Matrix (Accuracy: {test_acc*100:.2f}%)", fontsize=13)
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
