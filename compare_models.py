"""
compare_models.py
=================
Comprehensive Head-to-Head Comparison & Benchmarking:
Paper Baseline vs. Proposed Improvements.

Generates comparative tables and publication-ready visual bar charts.
"""

import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from baseline_paper import run_baseline_paper
from improved_pipeline import run_improved_pipeline


def generate_comparison_charts(baseline_metrics: dict, improved_metrics: dict, save_dir: str = "results"):
    os.makedirs(save_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("           HEAD-TO-HEAD BENCHMARK: PAPER BASELINE vs. PROPOSED IMPROVEMENT         ")
    print("=" * 80)
    print(f"{'Metric / Feature':<32} | {'Paper Baseline (Stage 1)':<24} | {'Proposed Improvement (Stage 2)':<26}")
    print("-" * 88)
    b_split = baseline_metrics.get("train_test_split", "80/20")
    i_split = improved_metrics.get("train_test_split", "80/20")
    b_test_n = baseline_metrics.get("test_samples", 18)
    i_test_n = improved_metrics.get("test_samples", 18)

    print(f"{'Split Ratio (Train / Test)':<32} | {b_split + ' (' + str(b_test_n) + ' test)':<24} | {i_split + ' (' + str(i_test_n) + ' test)':<26}")
    print(f"{'Classifier Architecture':<32} | {baseline_metrics['classification_method']:<24} | {improved_metrics['classification_method']:<26}")
    print(f"{'Initial Feature Pool':<32} | {baseline_metrics['n_original_features']:<24} | {improved_metrics['n_original_features']:<26}")
    b_prec = baseline_metrics.get("precision", baseline_metrics.get("macro_f1", 0.0))
    i_prec = improved_metrics.get("precision", improved_metrics.get("macro_f1", 0.0))
    b_rec = baseline_metrics.get("recall", baseline_metrics.get("macro_f1", 0.0))
    i_rec = improved_metrics.get("recall", improved_metrics.get("macro_f1", 0.0))

    print(f"{'Optimized Feature Subset':<32} | {baseline_metrics['n_selected_features']:<24} | {improved_metrics['n_selected_features']:<26}")
    print(f"{'Test Accuracy':<32} | {baseline_metrics['accuracy'] * 100:.2f}%{'':<18} | {improved_metrics['accuracy'] * 100:.2f}%")
    print(f"{'Macro Precision':<32} | {b_prec * 100:.2f}%{'':<18} | {i_prec * 100:.2f}%")
    print(f"{'Macro Recall (Sensitivity)':<32} | {b_rec * 100:.2f}%{'':<18} | {i_rec * 100:.2f}%")
    print(f"{'Macro F1-Score':<32} | {baseline_metrics['macro_f1']:.4f}{'':<18} | {improved_metrics['macro_f1']:.4f}")
    print("=" * 80)

    # Visual Comparison Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Subplot 1: Accuracy & F1
    models = ["Paper Baseline\n(GA + Single SVM)", "Proposed Improvement\n(Riemannian + AGA + Ensemble)"]
    accs = [baseline_metrics["accuracy"] * 100, improved_metrics["accuracy"] * 100]
    f1s = [baseline_metrics["macro_f1"] * 100, improved_metrics["macro_f1"] * 100]

    x = np.arange(len(models))
    width = 0.35

    rects1 = ax1.bar(x - width/2, accs, width, label="Test Accuracy (%)", color="#3a86ff", edgecolor="black", alpha=0.9)
    rects2 = ax1.bar(x + width/2, f1s, width, label="Macro F1-Score (%)", color="#38b000", edgecolor="black", alpha=0.9)

    ax1.set_ylabel("Score (%)", fontsize=11)
    ax1.set_title("Classification Performance Comparison", fontsize=13, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=10)
    ax1.set_ylim(0, 110)
    ax1.legend(loc="lower right")
    ax1.grid(True, axis="y", alpha=0.3)

    for rect in rects1 + rects2:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f}%",
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontweight="bold", fontsize=10)

    # Subplot 2: Feature Engineering & Dimensionality
    categories = ["Input Features", "Selected Subset"]
    base_counts = [baseline_metrics["n_original_features"], baseline_metrics["n_selected_features"]]
    impr_counts = [improved_metrics["n_original_features"], improved_metrics["n_selected_features"]]

    x2 = np.arange(len(categories))
    r1 = ax2.bar(x2 - width/2, base_counts, width, label="Paper Baseline", color="#adb5bd", edgecolor="black")
    r2 = ax2.bar(x2 + width/2, impr_counts, width, label="Proposed Innovation", color="#ff006e", edgecolor="black")

    ax2.set_ylabel("Number of Features", fontsize=11)
    ax2.set_title("Feature Space & Dimensionality Optimization", fontsize=13, fontweight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(categories, fontsize=10)
    ax2.legend()
    ax2.grid(True, axis="y", alpha=0.3)

    for rect in r1 + r2:
        h = rect.get_height()
        ax2.annotate(f"{int(h)}",
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontweight="bold", fontsize=10)

    plt.tight_layout()
    chart_path = os.path.join(save_dir, "baseline_vs_improved_comparison.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"[+] Comparative evaluation chart saved to '{chart_path}'")


def main():
    save_dir = "results"
    base_file = os.path.join(save_dir, "baseline_paper_metrics.json")
    impr_file = os.path.join(save_dir, "improved_pipeline_metrics.json")

    if os.path.exists(base_file):
        with open(base_file, "r") as f:
            base_m = json.load(f)
    else:
        base_m = run_baseline_paper(save_dir=save_dir)

    if os.path.exists(impr_file):
        with open(impr_file, "r") as f:
            impr_m = json.load(f)
    else:
        impr_m = run_improved_pipeline(save_dir=save_dir)

    generate_comparison_charts(base_m, impr_m, save_dir=save_dir)


if __name__ == "__main__":
    main()
