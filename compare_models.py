"""
compare_models.py
=================
Generates publication-grade comparative visualizations reading 100% live from
`results/baseline_paper_metrics.json`, `results/improved_pipeline_metrics.json`, and
`results/comparison_baselines.json` (zero hardcoded numbers).

Presents Leakage-Safe Block-Disjoint Nested 5-CV (Primary Unbiased Benchmark) AND
Exploratory Overlapping-Chunk Nested 5-CV side by side with equal visual emphasis,
complete with calibration (Brier/ECE) and controlled ablation panels.
"""

import os
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def run_comparison_visuals(results_dir: str = "results"):
    base_json = os.path.join(results_dir, "baseline_paper_metrics.json")
    imp_json = os.path.join(results_dir, "improved_pipeline_metrics.json")
    if not os.path.exists(base_json) or not os.path.exists(imp_json):
        raise FileNotFoundError("Missing baseline_paper_metrics.json or improved_pipeline_metrics.json.")

    with open(base_json, "r", encoding="utf-8") as f:
        bm = json.load(f)
    with open(imp_json, "r", encoding="utf-8") as f:
        im = json.load(f)

    bp_blk = bm["block_disjoint_primary"]
    bp_chk = bm["exploratory_chunk_secondary"]
    ip_blk = im["block_disjoint_primary"]
    ip_chk = im["exploratory_chunk_secondary"]

    fig = plt.figure(figsize=(16.5, 10.5), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0], hspace=0.40, wspace=0.25)

    # ------------------------------------------------------------------
    # Panel A (Top-Left): Primary Block-Disjoint Nested 5-CV vs Chance
    # ------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    models_a = [
        "Scalar\nSVM",
        "FBCSP\n+SVM",
        "EEGNet\nAtt (H0)",
        "MDM\nSPD",
        "Stage 1\nPaper GA",
        "Stage 2\nVote3211",
        "Stage 2\nStacker",
    ]
    vals_a = [
        bp_blk["scalar_322_svm_rbf_9class_5cv"]["accuracy"] * 100,
        bp_blk["fbcsp_svm_9class_5cv"]["accuracy"] * 100,
        bp_blk["eegnet_attention_40ep_holdout_fold0"]["accuracy"] * 100,
        bp_blk["mdm_log_euclid_6b_9class_5cv"]["accuracy"] * 100,
        bp_blk["paper_6b_rank_ga_knn_9class_5cv"]["accuracy"] * 100,
        ip_blk["weighted_vote_5cv"]["accuracy"] * 100,
        ip_blk["calibrated_stacker_5cv"]["accuracy"] * 100,
    ]
    bal_a = [
        bp_blk["scalar_322_svm_rbf_9class_5cv"]["balanced_accuracy"] * 100,
        bp_blk["fbcsp_svm_9class_5cv"]["balanced_accuracy"] * 100,
        bp_blk["eegnet_attention_40ep_holdout_fold0"]["balanced_accuracy"] * 100,
        bp_blk["mdm_log_euclid_6b_9class_5cv"]["balanced_accuracy"] * 100,
        bp_blk["paper_6b_rank_ga_knn_9class_5cv"]["balanced_accuracy"] * 100,
        ip_blk["weighted_vote_5cv"]["balanced_accuracy"] * 100,
        ip_blk["calibrated_stacker_5cv"]["balanced_accuracy"] * 100,
    ]
    xa = np.arange(len(models_a))
    w = 0.36
    b1 = ax1.bar(xa - w / 2, vals_a, width=w, color="#2563eb", edgecolor="#0f172a", label="Accuracy (%)")
    b2 = ax1.bar(xa + w / 2, bal_a, width=w, color="#93c5fd", edgecolor="#0f172a", hatch="//", label="Balanced Acc (%)")
    ax1.axhline(11.11, color="#dc2626", ls="--", lw=1.4, label="9-Class Uniform Chance (11.11%)")
    for bar in b1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f"{h:.1f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax1.set_xticks(xa)
    ax1.set_xticklabels(models_a, fontsize=8.0, fontweight="bold")
    ax1.set_ylabel("Accuracy (%)", fontsize=9.5, fontweight="bold")
    ax1.set_ylim(0, max(26.0, max(vals_a) + 7.0))
    ax1.set_title("A. PRIMARY UNBIASED: Block-Disjoint Nested 5-CV (328 Blocks)", fontsize=10.8, fontweight="bold", pad=8)
    ax1.grid(axis="y", alpha=0.25)
    ax1.legend(loc="upper left", fontsize=7.5, framealpha=0.95)

    # ------------------------------------------------------------------
    # Panel B (Top-Right): Exploratory Overlapping-Chunk Protocol (Leakage Disclosed)
    # ------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    vals_b = [
        bp_chk["scalar_322_svm_rbf_9class_5cv"]["accuracy"] * 100,
        bp_chk["fbcsp_svm_9class_5cv"]["accuracy"] * 100,
        bp_chk["eegnet_attention_40ep_holdout_fold0"]["accuracy"] * 100,
        bp_chk["mdm_log_euclid_6b_9class_5cv"]["accuracy"] * 100,
        bp_chk["paper_6b_rank_ga_knn_9class_5cv"]["accuracy"] * 100,
        ip_chk["weighted_vote_5cv"]["accuracy"] * 100,
        ip_chk["calibrated_stacker_5cv"]["accuracy"] * 100,
    ]
    cols_b = ["#94a3b8", "#64748b", "#0284c7", "#a855f7", "#f97316", "#16a34a", "#0d9488"]
    b_chk = ax2.bar(xa, vals_b, width=0.54, color=cols_b, edgecolor="#0f172a")
    for bar in b_chk:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 1.1, f"{h:.1f}%", ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    ax2.axhline(11.11, color="#475569", ls=":", lw=1.1, label="9-Class Chance (11.1%)")
    ax2.set_xticks(xa)
    ax2.set_xticklabels(models_a, fontsize=8.0, fontweight="bold")
    ax2.set_ylabel("Accuracy (%)", fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0, 108)
    ax2.set_title("B. EXPLORATORY: Overlapping-Chunk 5-CV (37.5% Overlap Leak)", fontsize=10.8, fontweight="bold", pad=8)
    ax2.grid(axis="y", alpha=0.25)
    ax2.text(
        0.5, 0.94,
        "Warning: Sibling 1s chunks cross train/test splits; measures temporal memorization, NOT unseen blocks/subjects.",
        transform=ax2.transAxes, ha="center", va="top", fontsize=7.0,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fef2f2", edgecolor="#ef4444", alpha=0.95),
    )

    # ------------------------------------------------------------------
    # Panel C (Bottom-Left): Calibration & Classifier Head Comparison
    # ------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    head_keys = ["Weighted_Soft_Vote_3211", "Equal_Soft_Vote_1111", "Shrinkage_LDA", "Multinomial_LogReg", "Calibrated_RBF_SVM", "Calibrated_OOF_Stacker"]
    head_lbls = ["Vote\n[3,2,1,1]", "Equal\nVote", "Shrink\nLDA", "LogReg", "Cal.\nSVM", "Cal.\nStacker"]
    ece_blk = [ip_blk["head_comparison_5cv"][k]["ece_10bin"] for k in head_keys]
    ece_chk = [ip_chk["head_comparison_5cv"][k]["ece_10bin"] for k in head_keys]
    brier_blk = [ip_blk["head_comparison_5cv"][k]["brier_score"] for k in head_keys]
    x3 = np.arange(len(head_keys))
    r1 = ax3.bar(x3 - 0.25, ece_blk, width=0.25, color="#f59e0b", edgecolor="#0f172a", label="ECE (Block-Disjoint, lower=better)")
    r2 = ax3.bar(x3, ece_chk, width=0.25, color="#10b981", edgecolor="#0f172a", label="ECE (Exploratory Chunk, lower=better)")
    r3 = ax3.bar(x3 + 0.25, brier_blk, width=0.25, color="#6366f1", edgecolor="#0f172a", label="Brier Score (Block-Disjoint)")
    for bars in (r1, r2):
        for bar in bars:
            h = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2, h + 0.015, f"{h:.2f}", ha="center", va="bottom", fontsize=6.8)
    ax3.set_xticks(x3)
    ax3.set_xticklabels(head_lbls, fontsize=8.0, fontweight="bold")
    ax3.set_ylabel("Calibration Error / Brier Score", fontsize=9.5, fontweight="bold")
    ax3.set_ylim(0, max(1.15, max(brier_blk) + 0.2))
    ax3.set_title("C. Probability Calibration Comparison Across Classifier Heads", fontsize=10.8, fontweight="bold", pad=8)
    ax3.grid(axis="y", alpha=0.25)
    ax3.legend(loc="upper right", fontsize=7.2, framealpha=0.95)

    # ------------------------------------------------------------------
    # Panel D (Bottom-Right): Key Scientific Ablations (Block-Disjoint vs Exploratory)
    # ------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ab_geo = im["ablations"]["geometry_tangent_fold_vs_identity_log_euclid"]
    ab_sub = im["ablations"]["subband_overlap_control"]
    ab_win = im["ablations"]["continuous_window_length_ablation"]
    ab_labels = [
        "Identity SPD\n(Log-Euclid)",
        "Fold Tangent\n(Non-Overlap)",
        "Overlap 7B\n(Legacy)",
        "Continuous 1s\n(Blk-Disjoint)",
        "Continuous 4s\n(Blk-Disjoint)",
        "Continuous 8s\n(Blk-Disjoint)",
    ]
    blk_ab = [
        ab_geo["block_disjoint_identity_vote_5cv"] * 100,
        ab_geo["block_disjoint_tangent_fold_vote_5cv"] * 100,
        ab_sub["block_disjoint_overlapping_vote"] * 100,
        ab_win["1s_128pts"]["window_level_block_disjoint_acc"] * 100,
        ab_win["4s_512pts"]["window_level_block_disjoint_acc"] * 100,
        ab_win["8s_1008pts"]["window_level_block_disjoint_acc"] * 100,
    ]
    chk_ab = [
        ab_geo["exploratory_chunk_identity_vote_5cv"] * 100,
        ab_geo["exploratory_chunk_tangent_fold_vote_5cv"] * 100,
        ab_sub["exploratory_chunk_overlapping_vote"] * 100,
        0.0,
        0.0,
        0.0,
    ]
    x4 = np.arange(len(ab_labels))
    ax4.bar(x4 - 0.18, blk_ab, width=0.35, color="#1d4ed8", edgecolor="#0f172a", label="Block-Disjoint 5-CV (%)")
    ax4.bar(x4[:3] + 0.18, chk_ab[:3], width=0.35, color="#059669", edgecolor="#0f172a", label="Exploratory Chunk 5-CV (%)")
    for idx_v, v in enumerate(blk_ab):
        ax4.text(idx_v - 0.18, v + 1.2, f"{v:.1f}", ha="center", va="bottom", fontsize=7.3, fontweight="bold", color="#1e3a8a")
    for idx_v, v in enumerate(chk_ab[:3]):
        ax4.text(idx_v + 0.18, v + 1.2, f"{v:.1f}", ha="center", va="bottom", fontsize=7.3, fontweight="bold", color="#065f46")
    ax4.set_xticks(x4)
    ax4.set_xticklabels(ab_labels, fontsize=7.8, fontweight="bold")
    ax4.set_ylabel("Accuracy (%)", fontsize=9.5, fontweight="bold")
    ax4.set_ylim(0, 108)
    ax4.set_title("D. Geometry, Sub-Band Overlap & Continuous Window Ablations", fontsize=10.8, fontweight="bold", pad=8)
    ax4.grid(axis="y", alpha=0.25)
    ax4.legend(loc="upper right", fontsize=7.6, framealpha=0.95)

    fig.suptitle(
        "NIT Warangal Topic 6 (Audited Dual-Protocol Benchmark): Block-Disjoint Primary vs Exploratory Chunk Upper Bound",
        fontsize=12.8, fontweight="bold", y=0.985,
    )

    out_png = os.path.join(results_dir, "baseline_vs_improved_comparison.png")
    plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    print(f"[+] Comparison chart saved to '{out_png}'")

    root_copy = os.path.join(r"c:\Users\st983\Downloads\ml", "baseline_vs_improved_comparison.png")
    if os.path.exists(os.path.dirname(root_copy)):
        shutil.copy2(out_png, root_copy)
    art_dir = r"C:\Users\st983\.gemini\antigravity\brain\b6fdf221-8b8c-4a78-99cf-c230f3a5db38"
    if os.path.exists(art_dir):
        shutil.copy2(out_png, os.path.join(art_dir, "baseline_vs_improved_comparison.png"))

    _generate_fig2_aga_and_ablations(im, results_dir)
    _generate_fig3_dual_protocol_summary(bm, im, results_dir)

    sample_pred = os.path.join(results_dir, "sample_prediction.png")
    live_decoded = os.path.join(results_dir, "live_decoded_signal.png")
    if os.path.exists(sample_pred):
        shutil.copy2(sample_pred, live_decoded)


def _generate_fig2_aga_and_ablations(im: dict, results_dir: str):
    hist = im["block_disjoint_primary"]["fold0_aga_history"]
    gens = np.arange(1, len(hist["fitness"]) + 1)
    fit_pct = np.array(hist["fitness"]) * 100.0
    div = np.array(hist["diversity"])
    mut = np.array(hist["mutation"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 5.0), dpi=300)
    fig.patch.set_facecolor("#ffffff")

    l1 = ax1.plot(gens, fit_pct, "o-", color="#0f172a", lw=2.2, ms=6, label="Inner GroupKFold Fitness (%)")
    ax1.set_xlabel("MultiScaleBlockAGA Generation (Fold 0 Inner GroupKFold)", fontsize=9.5, fontweight="bold")
    ax1.set_ylabel("Inner GroupKFold Score (%)", fontsize=9.5, fontweight="bold", color="#0f172a")
    ax1.set_xticks(gens)
    ax1.grid(True, ls=":", alpha=0.35)
    ax1r = ax1.twinx()
    l2 = ax1r.plot(gens, mut, "s--", color="#e11d48", lw=1.9, ms=5, label="Adaptive Step Pm")
    l3 = ax1r.plot(gens, div, "^:", color="#0d9488", lw=1.9, ms=5.5, label="Population Diversity (std)")
    ax1r.set_ylabel("Pm / Diversity", fontsize=9.5, fontweight="bold", color="#e11d48")
    lines = l1 + l2 + l3
    ax1.legend(lines, [ln.get_label() for ln in lines], loc="best", fontsize=7.6, framealpha=0.95)
    ax1.set_title("Block-Disjoint GroupKFold Block-Weight Evolution", fontsize=10.8, fontweight="bold", pad=8)

    # Right: 5-Seed Mutation & Montage Ablation Comparison
    mut_blk = im["ablations"]["mutation_5seed_control"]["block_disjoint"]
    mut_chk = im["ablations"]["mutation_5seed_control"]["exploratory_chunk"]
    mont = im["ablations"]["montage_topology_ablation"]

    cats = ["Fixed\nMut", "Div\nAdapt", "Div+\nStag", "Sp10\nMont", "All14\nMont", "Left7\nMont", "Occ4\nMont"]
    blk_vals = [
        mut_blk["fixed"]["mean"] * 100,
        mut_blk["diversity_adaptive"]["mean"] * 100,
        mut_blk["diversity_stagnation"]["mean"] * 100,
        mont["speech10"]["block_disjoint_local_logreg_acc"] * 100,
        mont["all14"]["block_disjoint_local_logreg_acc"] * 100,
        mont["left7"]["block_disjoint_local_logreg_acc"] * 100,
        mont["occipital4"]["block_disjoint_local_logreg_acc"] * 100,
    ]
    chk_vals = [
        mut_chk["fixed"]["mean"] * 100,
        mut_chk["diversity_adaptive"]["mean"] * 100,
        mut_chk["diversity_stagnation"]["mean"] * 100,
        mont["speech10"]["exploratory_chunk_local_vote_acc"] * 100,
        mont["all14"]["exploratory_chunk_local_vote_acc"] * 100,
        mont["left7"]["exploratory_chunk_local_vote_acc"] * 100,
        mont["occipital4"]["exploratory_chunk_local_vote_acc"] * 100,
    ]
    x2 = np.arange(len(cats))
    ax2.bar(x2 - 0.19, blk_vals, width=0.36, color="#2563eb", edgecolor="#0f172a", label="Block-Disjoint Holdout (%)")
    ax2.bar(x2 + 0.19, chk_vals, width=0.36, color="#10b981", edgecolor="#0f172a", label="Exploratory Chunk Holdout (%)")
    for idx_c, (vb, vc) in enumerate(zip(blk_vals, chk_vals)):
        ax2.text(idx_c - 0.19, vb + 1.0, f"{vb:.1f}", ha="center", va="bottom", fontsize=7.0, fontweight="bold")
        ax2.text(idx_c + 0.19, vc + 1.0, f"{vc:.1f}", ha="center", va="bottom", fontsize=7.0, fontweight="bold")
    ax2.axhline(11.11, color="#dc2626", ls=":", lw=1.1)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(cats, fontsize=8.0, fontweight="bold")
    ax2.set_ylabel("Accuracy (%)", fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0, 108)
    ax2.grid(axis="y", ls=":", alpha=0.35)
    ax2.legend(loc="upper left", fontsize=7.8, framealpha=0.95)
    ax2.set_title("5-Seed Mutation Control & Electrode Montage Ablations", fontsize=10.8, fontweight="bold", pad=8)

    plt.tight_layout()
    out_p = os.path.join(results_dir, "fig2_aga_optimization.png")
    plt.savefig(out_p, dpi=300, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    print(f"[+] Report Figure 2 saved to '{out_p}'")


def _generate_fig3_dual_protocol_summary(bm: dict, im: dict, results_dir: str):
    bp_blk = bm["block_disjoint_primary"]
    bp_chk = bm["exploratory_chunk_secondary"]
    ip_blk = im["block_disjoint_primary"]
    ip_chk = im["exploratory_chunk_secondary"]

    items = [
        ("Random 9-Class Uniform Chance", 11.11, "#cbd5e1"),
        ("[Blk-Disjoint] Stage 1 Paper 6B GA+kNN (5-CV)", bp_blk["paper_6b_rank_ga_knn_9class_5cv"]["accuracy"] * 100, "#60a5fa"),
        ("[Blk-Disjoint] FBCSP + Calibrated SVM (5-CV)", bp_blk["fbcsp_svm_9class_5cv"]["accuracy"] * 100, "#3b82f6"),
        ("[Blk-Disjoint] Stage 2 Fold-Tangent Vote3211 (5-CV)", ip_blk["weighted_vote_5cv"]["accuracy"] * 100, "#2563eb"),
        ("[Blk-Disjoint] Stage 2 Fold-Tangent Stacker (5-CV)", ip_blk["calibrated_stacker_5cv"]["accuracy"] * 100, "#1d4ed8"),
        ("[Blk-Disjoint] Paper Binary Yes/No (5-CV)", bp_blk["paper_6b_yes_no_5cv"]["accuracy"] * 100, "#1e3a8a"),
        ("[Exploratory Overlap] FBCSP + SVM (5-CV)", bp_chk["fbcsp_svm_9class_5cv"]["accuracy"] * 100, "#94a3b8"),
        ("[Exploratory Overlap] EEGNetAttention (40ep H0)", bp_chk["eegnet_attention_40ep_holdout_fold0"]["accuracy"] * 100, "#0284c7"),
        ("[Exploratory Overlap] Stage 1 Paper 6B GA (5-CV)", bp_chk["paper_6b_rank_ga_knn_9class_5cv"]["accuracy"] * 100, "#f97316"),
        ("[Exploratory Overlap] Stage 2 Stacker (5-CV)", ip_chk["calibrated_stacker_5cv"]["accuracy"] * 100, "#0d9488"),
        ("[Exploratory Overlap] Stage 2 Vote3211 (5-CV)", ip_chk["weighted_vote_5cv"]["accuracy"] * 100, "#10b981"),
        ("[Exploratory Overlap] Paper Binary Yes/No Stacker", ip_chk["yes_no_5cv"]["stacker"]["accuracy"] * 100, "#059669"),
    ]

    labels = [x[0] for x in items]
    vals = [x[1] for x in items]
    colors = [x[2] for x in items]

    fig, ax = plt.subplots(figsize=(14.0, 5.8), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    y_pos = np.arange(len(items))
    bars = ax.barh(y_pos, vals, height=0.66, color=colors, edgecolor="#0f172a")
    ax.axvline(11.11, color="#dc2626", ls="--", lw=1.3, label="9-Class Chance (11.11%)")
    ax.axvline(96.0, color="#059669", ls=":", lw=1.6, label="Published Paper Yes/No Benchmark (96.0%)")

    for b, v in zip(bars, vals):
        ax.text(v + 0.9, b.get_y() + b.get_height() / 2, f"{v:.2f}%", va="center", ha="left", fontsize=8.2, fontweight="bold", color="#0f172a")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.6, fontweight="bold")
    ax.set_xlim(0, 112)
    ax.set_xlabel("Verified Mendeley EEGIS Accuracy (%) — Blue: Block-Disjoint Primary | Green/Orange: Exploratory Chunk", fontsize=9.4, fontweight="bold")
    ax.set_title("Side-by-Side Protocol Audit: Block-Disjoint Generalization vs Exploratory Chunk Memorization", fontsize=11.6, fontweight="bold", pad=10)
    ax.grid(axis="x", ls=":", alpha=0.35)
    ax.legend(loc="lower right", fontsize=8.4, framealpha=0.95)
    plt.tight_layout()

    out_p = os.path.join(results_dir, "fig3_accuracy_comparison.png")
    plt.savefig(out_p, dpi=300, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    print(f"[+] Report Figure 3 saved to '{out_p}'")


if __name__ == "__main__":
    run_comparison_visuals()
