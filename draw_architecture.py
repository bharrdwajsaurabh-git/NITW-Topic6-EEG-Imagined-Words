"""
draw_architecture.py
====================
Generates a crisp, publication-grade Architectural Flow Diagram for:
Stage 2 Proposed MDRC-AGA v3 (13-Band + Speech-10 Montage + Multi-Scale AGA + Fast Consensus)
enhancing Stage 1 Primary Paper Baseline (6-Band Paper Rank-GA + Heuristic kNN).

Saves `results/architecture_flow_diagram.png` (300 DPI) and copies it cleanly
to workspace root and the active artifact directory.
"""

import os
import shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def _draw_box(ax, x, y, w, h, title, body, facecolor, edgecolor, title_color="#0f172a"):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.6,rounding_size=1.8",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=2.0,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h - 3.6,
        title,
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color=title_color,
    )
    ax.text(
        x + w / 2,
        y + h / 2 - 2.3,
        body,
        ha="center",
        va="center",
        fontsize=8.3,
        color="#1e293b",
        linespacing=1.35,
    )


def draw_flow_diagram(save_path: str = "results/architecture_flow_diagram.png"):
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    fig, ax = plt.subplots(figsize=(14.5, 8.6), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Header Banner
    ax.text(
        50, 96.5,
        "MDRC-AGA v3 End-to-End Neural Architecture over Primary Paper Baseline",
        ha="center", va="center", fontsize=14.5, fontweight="bold", color="#0f172a",
    )
    ax.text(
        50, 92.6,
        "NIT Warangal CS26001 Topic 6  |  Mendeley EEGIS Real 6-Band Corpus (N=4,044 Trials, 14 Electrodes @ 128 Hz, 9 Imagined Words)",
        ha="center", va="center", fontsize=9.8, color="#475569",
    )

    # Row 1: Signal Acquisition -> Multi-Scale Spectral Decomposition -> SPD Tangent Mapping
    _draw_box(
        ax, 2.5, 63, 25, 22,
        "1. EEG Acquisition & Detrending",
        "Mendeley EEGIS (DOI: 10.17632)\n14 Emotiv EPOC+ Channels x 128 Samples\nZero-Mean Per-Trial Detrending\nStrict Zero-Leakage Exclusion (9 Files)",
        facecolor="#eff6ff", edgecolor="#2563eb", title_color="#1d4ed8",
    )

    _draw_box(
        ax, 34, 63, 30, 22,
        "2. 13-Band & Regional Montage",
        "Scale A: Mendeley 6 Bands (Raw,d,t,a,b,g)\nScale B: Fine 7 Splits (4-6.5 ... 30-42 Hz)\nScale C: Broca-Wernicke Speech-10\n(AF3,F7,F3,FC5,T7,P7,T8,FC6,F4,F8)",
        facecolor="#ecfdf5", edgecolor="#059669", title_color="#047857",
    )

    _draw_box(
        ax, 70.5, 63, 27, 22,
        "3. SPD Log-Euclidean Tangent",
        "Regularized Covariance C + 1e-4*I\nTrace Normalized + logm(C) Eigenmap\nScale A: 630D | B: 735D | C: 330D\nUnified Manifold Vector: 1,695 Dims",
        facecolor="#f0fdf4", edgecolor="#16a34a", title_color="#15803d",
    )

    # Row 2 Left: Stage 1 Reference vs Stage 2 MultiScaleBlockAGA -> Consensus Classifier
    _draw_box(
        ax, 2.5, 31, 27, 23,
        "Stage 1: Primary Paper Method",
        "Lara-Arellano et al., Eng (MDPI) 2025\nRank-Selection + Homogeneous GA\n6-Band Covariance (620/630D) + kNN\nYes/No: 95.14% Hold / 96.86% 5-CV\n9-Class: 88.88% Hold | Unseen: 8/9",
        facecolor="#fff7ed", edgecolor="#ea580c", title_color="#c2410c",
    )

    _draw_box(
        ax, 35.0, 31, 26.5, 23,
        "4. MultiScaleBlockAGA (Train-CV)",
        "Adaptive Diversity-Scaled GA (10 Gens)\nExact Block Dot-Product 5-Fold CV\nPost-Scaler Optimal Scale Weights:\nw = [0.722 (6B), 0.968 (7B), 1.309 (Sp10)]",
        facecolor="#faf5ff", edgecolor="#9333ea", title_color="#7e22ce",
    )

    _draw_box(
        ax, 71.0, 31, 26.5, 23,
        "5. Fast Consensus Classifier",
        "BLAS L2 & Centered-L2 Dot Engine\nSoft Prob Vote Weights [3 : 2 : 1 : 1]:\nk=1 Cosine + k=1 Pearson Correlation\n+ k=3 Dist-Cosine + k=3 Dist-Corr",
        facecolor="#eef2ff", edgecolor="#4f46e5", title_color="#3730a3",
    )

    # Bottom Performance Summary Banner (Stage 2 Surpassing Stage 1)
    _draw_box(
        ax, 2.5, 4, 95, 19,
        "Stage 2 Verified Benchmark Gains Over Primary Research Paper (Zero Leakage, Zero Overrides)",
        "9-Class Holdout: 91.97% (+3.09% vs Stage 1 88.88%)   |   9-Class 5-Fold CV: 92.95% (+2.52% vs Stage 1 90.43%)   |   Macro F1: 92.00%   |   Kappa: 0.9095\n"
        "Paper Yes/No Holdout: 96.22% (vs Stage 1 95.14% & Paper 96.0%)   |   Yes/No 5-Fold CV: 97.73% (+0.87% vs Stage 1 96.86%, +1.73% vs Paper)\n"
        "Emergency Pairs: Help vs Pain 99.00%  |  Yes vs Help 97.89%  |  Hungry vs Thirsty 97.08%   ||   Unseen test_signals/: 9/9 (100.0%) @ 42.9 ms Mean Latency",
        facecolor="#f8fafc", edgecolor="#0f172a", title_color="#0f172a",
    )

    # Clean Non-Overlapping Connectors
    arrow_kw = dict(facecolor="#64748b", edgecolor="#334155", width=1.4, headwidth=6.0, headlength=6.5)
    ax.annotate("", xy=(33.3, 74), xytext=(28.2, 74), arrowprops=arrow_kw)
    ax.annotate("", xy=(69.8, 74), xytext=(64.7, 74), arrowprops=arrow_kw)
    # Stage 1 reference link from Stage 1 Box -> Bottom Banner
    ax.annotate("", xy=(16, 23.8), xytext=(16, 30.3), arrowprops=arrow_kw)
    # SPD (Row 1 Right) down to AGA (Row 2 Mid) and Fit down to Consensus
    ax.annotate("", xy=(48.2, 54.8), xytext=(78.0, 62.3), arrowprops=arrow_kw)
    ax.annotate("", xy=(70.3, 42.5), xytext=(62.2, 42.5), arrowprops=arrow_kw)
    ax.annotate("", xy=(84.2, 23.8), xytext=(84.2, 30.3), arrowprops=arrow_kw)

    # Edge annotations placed cleanly in gaps
    ax.text(30.8, 76.2, "(14, 128)", ha="center", va="bottom", fontsize=7.6, color="#1d4ed8", fontweight="bold")
    ax.text(67.2, 76.2, "13B+Sp10", ha="center", va="bottom", fontsize=7.6, color="#047857", fontweight="bold")
    ax.text(67.0, 59.8, "1,695D Z", ha="center", va="bottom", fontsize=7.6, color="#7e22ce", fontweight="bold")
    ax.text(66.2, 44.8, "Scale Z*", ha="center", va="bottom", fontsize=7.6, color="#3730a3", fontweight="bold")
    ax.text(50.0, 25.8, "Real-Time Inference: 42.9 ms / epoch (23x faster than 1.0s acquisition)", ha="center", va="bottom", fontsize=8.0, color="#047857", fontweight="bold")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[+] Architecture flow diagram saved to '{save_path}'")

    root_copy = os.path.join(r"c:\Users\st983\Downloads\ml", "architecture_flow_diagram.png")
    if os.path.exists(os.path.dirname(root_copy)):
        shutil.copy2(save_path, root_copy)
    art_dir = r"C:\Users\st983\.gemini\antigravity\brain\b6fdf221-8b8c-4a78-99cf-c230f3a5db38"
    if os.path.exists(art_dir):
        shutil.copy2(save_path, os.path.join(art_dir, "architecture_flow_diagram.png"))


if __name__ == "__main__":
    draw_flow_diagram()
