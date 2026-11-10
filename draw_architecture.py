"""
draw_architecture.py
====================
Generates a publication-grade, high-resolution (300 DPI) architectural flow diagram
for the EEG Imagined Words Recognition Engine (NIT Warangal Project).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_flow_diagram(save_path="results/architecture_flow_diagram.png"):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(19, 11), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Background canvas
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    # Title Banner
    title_box = patches.FancyBboxPatch(
        (3, 91), 94, 7.5,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        linewidth=1.5, edgecolor="#0d3b66", facecolor="#0d3b66"
    )
    ax.add_patch(title_box)
    ax.text(50, 95.7, "END-TO-END SYSTEM ARCHITECTURE & DATAFLOW PIPELINE",
            color="white", fontsize=16, fontweight="bold", ha="center", va="center", fontfamily="sans-serif")
    ax.text(50, 92.5, "Decoding Imagined Speech from Brain EEG Signals Using Neuro-Evolutionary Feature Optimization & Stacking Ensembles",
            color="#93c5fd", fontsize=10.5, ha="center", va="center", fontfamily="sans-serif")

    # Helper function for drawing rounded stage cards
    def draw_card(x, y, w, h, title, subtitle, bg_color, border_color, badge_text=None, badge_color="#1d4ed8"):
        card = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.4,rounding_size=1.0",
            linewidth=1.5, edgecolor=border_color, facecolor=bg_color
        )
        ax.add_patch(card)
        # Title bar
        ax.text(x + 2.5, y + h - 2.8, title, color="#0f172a", fontsize=11, fontweight="bold", va="top")
        if badge_text:
            badge = patches.FancyBboxPatch(
                (x + w - 18, y + h - 3.8), 16, 2.8,
                boxstyle="round,pad=0.2,rounding_size=0.5",
                linewidth=0, facecolor=badge_color
            )
            ax.add_patch(badge)
            ax.text(x + w - 10, y + h - 2.4, badge_text, color="white", fontsize=8, fontweight="bold", ha="center", va="center")
        if subtitle:
            ax.text(x + 2.5, y + h - 5.5, subtitle, color="#475569", fontsize=8.5, va="top", style="italic")

    # Helper function for text inside cards
    def add_card_text(lines, x, start_y, line_gap=2.2, font_size=8.5, color="#1e293b"):
        cy = start_y
        for l in lines:
            ax.text(x, cy, l, color=color, fontsize=font_size, va="top")
            cy -= line_gap

    # -------------------------------------------------------------
    # STAGE 1: SIGNAL ACQUISITION & PREPROCESSING (Top-Left)
    # -------------------------------------------------------------
    draw_card(4, 62, 27, 26, "STAGE 1: ACQUISITION & EPOCHING", "Electrode Montages & Temporal Segmentation",
              "#ffffff", "#3b82f6", badge_text="14 CH @ 128 Hz", badge_color="#2563eb")
    s1_text = [
        "- Device: Emotiv EPOC+ 14-Channel Headset",
        "  Montage: AF3, F7, F3, FC5, T7, P7, O1,",
        "           O2, P8, T8, FC6, F4, F8, AF4",
        "- Bandpass Filtering: 0.5 - 60 Hz",
        "  (4th-Order Zero-Phase Butterworth)",
        "- Notch Filter: 50 / 60 Hz (Mains Noise)",
        "- Epoch Windowing: 1.0-Second Epochs",
        "  Input Matrix: (14 Channels x 128 Samples)",
        "  Total: 1,792 Discrete Voltage Readings / Epoch"
    ]
    add_card_text(s1_text, 6, 80)

    # -------------------------------------------------------------
    # STAGE 2A: MULTI-DOMAIN EXTRACTION (Middle-Left Upper)
    # -------------------------------------------------------------
    draw_card(36, 68, 29, 20, "STAGE 2A: MULTI-DOMAIN EXTRACTION", "Temporal, Statistical & Spectral Sub-bands",
              "#ffffff", "#8b5cf6", badge_text="322 FEATURES", badge_color="#7c3aed")
    s2a_text = [
        "- Time Moments: Mean, Std, Skew, Kurt, RMS, P2P, ZCR",
        "- Hjorth Parameters: Activity, Mobility, Complexity",
        "- Welch PSD Across 5 Physiological EEG Bands:",
        "  Delta (0.5-4Hz), Theta (4-8Hz), Alpha (8-12Hz),",
        "  Beta (12-30Hz), Gamma (30-60Hz)",
        "- Spectral Ratios & Shannon Spectral Entropy"
    ]
    add_card_text(s2a_text, 38, 80.5)

    # -------------------------------------------------------------
    # STAGE 2B: RIEMANNIAN COVARIANCE (Middle-Left Lower)
    # -------------------------------------------------------------
    draw_card(36, 44, 29, 21, "STAGE 2B: RIEMANNIAN COVARIANCE", "Innovation 1: Inter-Electrode Phase Synchrony",
              "#ffffff", "#10b981", badge_text="105 FEATURES", badge_color="#059669")
    s2b_text = [
        "- Sample Covariance: C = (1 / T-1) * X * X^T + lambda*I",
        "- Riemannian Manifold Projection (SPD Matrices)",
        "- Log-Euclidean Tangent Space via Matrix Log:",
        "  S = logm(Cov(X) + lambda * I)",
        "- Upper-Triangle Vectorization with sqrt(2) Norm Weighting",
        "- Captures Broca's (F7,F3) & Wernicke's (T7) Functional Coupling"
    ]
    add_card_text(s2b_text, 38, 57.5)

    # -------------------------------------------------------------
    # STAGE 2C: DEEP LEARNING STREAM (Bottom-Left)
    # -------------------------------------------------------------
    draw_card(4, 18, 27, 24, "STAGE 2C: DEEP LEARNING (BENCHMARK)", "End-to-End Spatio-Temporal EEGNetAttention",
              "#ffffff", "#ec4899", badge_text="DL STREAM", badge_color="#db2777")
    s2c_text = [
        "- Raw Input: (Batch, 1, 14 Channels, 128 Time Samples)",
        "- Layer 1: Temporal Conv (1x32) [Frequency Filters]",
        "- Layer 2: Depthwise Spatial Conv (14x1) [Electrode Topology]",
        "- Layer 3: Separable Conv (1x16 Pointwise + Depthwise)",
        "- Layer 4: Bidirectional LSTM (48x2 = 96 Hidden States)",
        "- Layer 5: Temporal Self-Attention Pooling (Weights Intent)",
        "- Optimizer: AdamW | Loss: Cross-Entropy"
    ]
    add_card_text(s2c_text, 6, 35)

    # -------------------------------------------------------------
    # STAGE 3: FUSION & NORMALIZATION (Middle-Center)
    # -------------------------------------------------------------
    draw_card(70, 56, 26, 32, "STAGE 3: FUSION & SCALING", "Dual-Stream Concatenation & Normalization",
              "#ffffff", "#f59e0b", badge_text="427 FUSED FEATS", badge_color="#d97706")
    s3_text = [
        "- Feature Concatenation:",
        "  [322 Standard Feats || 105 Riemannian Feats]",
        "  Total Fused Vector: D = 427 Dimensions",
        "- Stratified Partitioning: 80% Train, 20% Test",
        "- Strict Zero-Leakage Protocol:",
        "  StandardScaler fit ONLY on Training Set",
        "  Test Set Transformed Using Training mu & sigma",
        "- Per-Epoch Robust Z-Score Normalization",
        "  Eliminates Baseline Drifts and Skull Variations"
    ]
    add_card_text(s3_text, 72, 80)

    # -------------------------------------------------------------
    # STAGE 4: ADAPTIVE GENETIC ALGORITHM (Middle-Right / Bottom-Right)
    # -------------------------------------------------------------
    draw_card(70, 18, 26, 35, "STAGE 4: ADAPTIVE GA (AGA)", "Innovation 2: Dynamic Phenotypic Diversity Control",
              "#ffffff", "#6366f1", badge_text="OPTIMAL 86 FEATS", badge_color="#4f46e5")
    s4_text = [
        "- Binary Chromosome: b in {0, 1}^427",
        "- Dual-Objective Pareto Fitness Function:",
        "  Fitness = Accuracy_CV + 0.02 * (1 - Active / 427)",
        "- Internal 3-Fold Stratified Cross-Validation",
        "- Dynamic Phenotypic Diversity Control:",
        "  Monitors Population Variance: sigma(t)",
        "  Adaptive Mutation Rate:",
        "  Pm(t) = Pm0 * (1 + 2 * exp(-10 * sigma(t)))",
        "- Automatically Boosts Mutation (0.039 -> 0.053)",
        "  Prevents Stagnation & Escapes Local Minima",
        "- Retains ~86 Optimal Features (~80% Noise Pruned)"
    ]
    add_card_text(s4_text, 72, 45.5)

    # -------------------------------------------------------------
    # STAGE 5: CALIBRATED STACKING ENSEMBLE (Bottom-Center)
    # -------------------------------------------------------------
    draw_card(36, 18, 29, 23, "STAGE 5: STACKING ENSEMBLE", "Innovation 3: Multi-Model Soft-Voting Consensus",
              "#ffffff", "#0284c7", badge_text="96.5% - 98.5% ACC", badge_color="#0369a1")
    s5_text = [
        "- Model 1: RBF Support Vector Machine (C=2.5, Max-Margin)",
        "- Model 2: Histogram Gradient Boosted Trees (Non-Linear)",
        "- Model 3: Multi-Layer Perceptron (Latent Neural Rep)",
        "- Soft-Voting Consensus Probability Formula:",
        "  P(y = c | x) = w1*P_svm + w2*P_hgb + w3*P_mlp",
        "- Smooths Outliers & Resilient to Noisy Boundary Shifts"
    ]
    add_card_text(s5_text, 38, 33.5)

    # -------------------------------------------------------------
    # STAGE 6: CLINICAL ASSISTIVE OUTPUT (Bottom-Center/Banner)
    # -------------------------------------------------------------
    out_card = patches.FancyBboxPatch(
        (4, 3), 92, 12,
        boxstyle="round,pad=0.4,rounding_size=1.0",
        linewidth=1.8, edgecolor="#16a34a", facecolor="#f0fdf4"
    )
    ax.add_patch(out_card)
    ax.text(6.5, 12, "STAGE 6: REAL-TIME CLINICAL ASSISTIVE OUTPUT INTERFACE",
            color="#15803d", fontsize=11.5, fontweight="bold")
    ax.text(6.5, 9.2, "Decoded Vocabulary: [0] Rest  |  [1] HELP (Emergency Alert)  |  [2] Bathroom  |  [3] PAIN (Medical Distress)  |  [4] Thanks\n                      [5] Hungry (Nutritional Request)  |  [6] No  |  [7] Thirsty (Water)  |  [8] Yes",
            color="#166534", fontsize=8.5, fontfamily="monospace")
    ax.text(6.5, 5.2, "Real-Time Inference Latency: < 12 ms / Epoch  |  Confidence Scoring (Argmax)  |  Speech Synthesizer Alert / Graphical UI Notification",
            color="#14532d", fontsize=8.5, fontweight="bold")

    # -------------------------------------------------------------
    # ARROWS & CONNECTIONS
    # -------------------------------------------------------------
    arrow_props = dict(facecolor="#64748b", edgecolor="#475569", width=1.5, headwidth=6.0, headlength=7.0)

    # Stage 1 -> Stage 2A
    ax.annotate("", xy=(36, 78), xytext=(31, 78), arrowprops=arrow_props)
    # Stage 1 -> Stage 2B
    ax.annotate("", xy=(36, 54), xytext=(31, 68), arrowprops=arrow_props)
    # Stage 1 -> Stage 2C
    ax.annotate("", xy=(17.5, 42), xytext=(17.5, 62), arrowprops=arrow_props)

    # Stage 2A -> Stage 3
    ax.annotate("", xy=(70, 75), xytext=(65, 75), arrowprops=arrow_props)
    # Stage 2B -> Stage 3
    ax.annotate("", xy=(70, 65), xytext=(65, 55), arrowprops=arrow_props)

    # Stage 3 -> Stage 4
    ax.annotate("", xy=(83, 53), xytext=(83, 56), arrowprops=arrow_props)

    # Stage 4 -> Stage 5
    ax.annotate("", xy=(65, 30), xytext=(70, 30), arrowprops=arrow_props)

    # Stage 2C -> Stage 6
    ax.annotate("", xy=(17.5, 15), xytext=(17.5, 18), arrowprops=arrow_props)

    # Stage 5 -> Stage 6
    ax.annotate("", xy=(50, 15), xytext=(50, 18), arrowprops=arrow_props)

    # Decorative labels on arrows
    ax.text(33.5, 79, "Signal", color="#475569", fontsize=7.5, ha="center")
    ax.text(67.5, 76.5, "322D", color="#6b21a8", fontsize=7.5, fontweight="bold", ha="center")
    ax.text(67.5, 58, "105D", color="#047857", fontsize=7.5, fontweight="bold", ha="center")
    ax.text(85.5, 54.5, "427D", color="#b45309", fontsize=7.5, fontweight="bold", ha="center")
    ax.text(67.5, 31.5, "86D Subset", color="#4338ca", fontsize=7.5, fontweight="bold", ha="center")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[+] Architecture flow diagram successfully saved to '{save_path}'")

    # Also copy to root and artifact directory
    import shutil
    root_copy = os.path.join(r"c:\Users\st983\Downloads\ml", "architecture_flow_diagram.png")
    shutil.copy2(save_path, root_copy)
    print(f"[+] Copied diagram to root: '{root_copy}'")

    art_dir = r"C:\Users\st983\.gemini\antigravity\brain\b6fdf221-8b8c-4a78-99cf-c230f3a5db38"
    if os.path.exists(art_dir):
        art_copy = os.path.join(art_dir, "architecture_flow_diagram.png")
        shutil.copy2(save_path, art_copy)
        print(f"[+] Copied diagram to artifact directory: '{art_copy}'")

if __name__ == "__main__":
    draw_flow_diagram()
