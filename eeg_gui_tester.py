"""
eeg_gui_tester.py
=================
Graphical User Interface (GUI) for Real-Time EEG Imagined Speech Decoding.
Designed for interactive laboratory demonstrations and committee evaluations.

Features:
- Pure signal-driven testing: Load any .csv or .npy EEG recording with zero text typing.
- Live 14-channel multichannel brainwave oscilloscope plot.
- One-click Neural Decoding: predicts imagined word, confidence, and millisecond latency.
- Full 9-class probability distribution bar chart.
- Blind clinical ground-truth verification audit.
"""

import os
import sys
import time
import json
import pickle
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Ensure src/ is in Python path for clean modular imports
src_dir = os.path.join(os.path.dirname(__file__), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from dataset_loader import CLASS_MAP, CHANNEL_NAMES
from predict import load_best_model, predict_signal, load_raw_eeg_file


class EEGDecoderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NIT Warangal — Assistive EEG Imagined Speech Signal Decoder")
        self.root.geometry("1280x780")
        self.root.minsize(1100, 700)

        # Apply dark clinical theme
        self.bg_color = "#0f172a"
        self.card_bg = "#1e293b"
        self.accent_blue = "#38bdf8"
        self.accent_green = "#4ade80"
        self.accent_gold = "#facc15"
        self.accent_red = "#f87171"
        self.text_light = "#f8fafc"
        self.text_muted = "#94a3b8"

        self.root.configure(bg=self.bg_color)

        # State
        self.current_signal = None
        self.current_filename = "None loaded"
        self.model_pkg = None
        self.test_signal_files = self._discover_test_signals()
        self.current_test_idx = 0

        self._load_model()
        self._build_ui()

        # Load first sample automatically for immediate display
        if self.test_signal_files:
            self._load_specific_file(self.test_signal_files[0])

    def _discover_test_signals(self):
        sig_dir = "test_signals"
        if os.path.exists(sig_dir):
            files = [os.path.join(sig_dir, f) for f in sorted(os.listdir(sig_dir)) if f.endswith(".csv")]
            return files
        return []

    def _load_model(self):
        try:
            self.model_pkg, self.model_type = load_best_model()
        except Exception as e:
            print(f"[!] Warning: Model loading notice: {e}")
            self.model_pkg = None
            self.model_type = None

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#090d16", height=60, padx=20, pady=10)
        header.pack(fill="x", side="top")

        lbl_title = tk.Label(
            header,
            text="NIT Warangal | CS26001: Advanced Algorithms — Topic 6: Imagined Speech Decoder",
            font=("Segoe UI", 14, "bold"),
            fg=self.accent_blue,
            bg="#090d16"
        )
        lbl_title.pack(side="left")

        lbl_sub = tk.Label(
            header,
            text="Team: Saurabh Bharrdwaj (Lead) • Badvath Jaipal • Saurabh Kumar",
            font=("Segoe UI", 10),
            fg=self.text_muted,
            bg="#090d16"
        )
        lbl_sub.pack(side="right")

        # Main Workspace: Two Columns
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=16, pady=12)
        main_frame.pack(fill="both", expand=True)

        left_panel = tk.Frame(main_frame, bg=self.card_bg, padx=14, pady=14, relief="ridge", bd=1)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_panel = tk.Frame(main_frame, bg=self.card_bg, width=440, padx=14, pady=14, relief="ridge", bd=1)
        right_panel.pack(side="right", fill="both", expand=False)
        right_panel.pack_propagate(False)

        # ----------------- LEFT PANEL: Signal Acquisition & Oscilloscope -----------------
        toolbar = tk.Frame(left_panel, bg=self.card_bg)
        toolbar.pack(fill="x", pady=(0, 10))

        btn_browse = tk.Button(
            toolbar, text="📂 Open EEG Signal File (.csv/.npy)",
            command=self._on_browse_file,
            bg="#2563eb", fg="white", font=("Segoe UI", 10, "bold"),
            padx=12, pady=6, relief="flat", cursor="hand2"
        )
        btn_browse.pack(side="left", padx=(0, 8))

        btn_cycle = tk.Button(
            toolbar, text="🎲 Load Next Patient EEG Trial",
            command=self._on_cycle_signal,
            bg="#0d9488", fg="white", font=("Segoe UI", 10, "bold"),
            padx=12, pady=6, relief="flat", cursor="hand2"
        )
        btn_cycle.pack(side="left")

        self.lbl_file_status = tk.Label(
            toolbar, text="No signal file loaded",
            font=("Consolas", 10), fg=self.accent_gold, bg=self.card_bg
        )
        self.lbl_file_status.pack(side="right")

        # Telemetry Card
        self.lbl_telemetry = tk.Label(
            left_panel,
            text="Signal Dimensions: -- | Sample Rate: 128 Hz | Electrodes: 14 | Voltage Range: --",
            font=("Segoe UI", 9), fg=self.text_muted, bg="#152033", pady=4
        )
        self.lbl_telemetry.pack(fill="x", pady=(0, 10))

        # Embedded Matplotlib Figure for Oscilloscope
        self.fig = Figure(figsize=(7, 6), dpi=100, facecolor=self.card_bg)
        self.ax_eeg = self.fig.add_subplot(111)
        self.ax_eeg.set_facecolor("#152033")
        self.fig.tight_layout()

        self.canvas_eeg = FigureCanvasTkAgg(self.fig, master=left_panel)
        self.canvas_eeg.get_tk_widget().pack(fill="both", expand=True)

        # ----------------- RIGHT PANEL: Decoding Controls & Outputs -----------------
        lbl_decode_head = tk.Label(
            right_panel, text="NEURAL DECODING ENGINE",
            font=("Segoe UI", 11, "bold"), fg=self.accent_blue, bg=self.card_bg
        )
        lbl_decode_head.pack(anchor="w")

        btn_decode = tk.Button(
            right_panel, text="🧠 DECODE EEG BRAIN SIGNAL",
            command=self._on_decode_signal,
            bg="#16a34a", fg="white", font=("Segoe UI", 12, "bold"),
            pady=10, relief="flat", cursor="hand2"
        )
        btn_decode.pack(fill="x", pady=(8, 14))

        # Prediction Winner Card
        self.card_result = tk.Frame(right_panel, bg="#132738", padx=12, pady=12, relief="groove", bd=2)
        self.card_result.pack(fill="x", pady=(0, 12))

        lbl_pred_title = tk.Label(
            self.card_result, text="DECODED IMAGINED THOUGHT:",
            font=("Segoe UI", 9, "bold"), fg=self.text_muted, bg="#132738"
        )
        lbl_pred_title.pack(anchor="w")

        self.lbl_prediction = tk.Label(
            self.card_result, text="[ READY TO DECODE ]",
            font=("Segoe UI", 18, "bold"), fg=self.accent_gold, bg="#132738"
        )
        self.lbl_prediction.pack(pady=4)

        self.lbl_conf_latency = tk.Label(
            self.card_result, text="Confidence: -- %  |  Inference Latency: -- ms",
            font=("Segoe UI", 10), fg=self.accent_green, bg="#132738"
        )
        self.lbl_conf_latency.pack()

        # Probability Spectrum Bars
        lbl_prob_head = tk.Label(
            right_panel, text="All-Class Probability Distribution:",
            font=("Segoe UI", 10, "bold"), fg=self.text_light, bg=self.card_bg
        )
        lbl_prob_head.pack(anchor="w", pady=(4, 4))

        self.fig_prob = Figure(figsize=(4.2, 2.8), dpi=100, facecolor=self.card_bg)
        self.ax_prob = self.fig_prob.add_subplot(111)
        self.ax_prob.set_facecolor("#152033")
        self.fig_prob.tight_layout()

        self.canvas_prob = FigureCanvasTkAgg(self.fig_prob, master=right_panel)
        self.canvas_prob.get_tk_widget().pack(fill="both", expand=True)

        # Verification Box
        self.box_verify = tk.Frame(right_panel, bg="#1a2333", padx=8, pady=8, relief="ridge", bd=1)
        self.box_verify.pack(fill="x", pady=(8, 0))

        btn_verify = tk.Button(
            self.box_verify, text="🔍 Verify with Medical Ground Truth Ledger",
            command=self._on_verify_ground_truth,
            bg="#475569", fg="white", font=("Segoe UI", 9),
            relief="flat", cursor="hand2"
        )
        btn_verify.pack(fill="x", pady=(0, 4))

        self.lbl_verify_text = tk.Label(
            self.box_verify, text="Ground truth hidden. Click to verify.",
            font=("Segoe UI", 8), fg=self.text_muted, bg="#1a2333", wraplength=380
        )
        self.lbl_verify_text.pack()

    def _on_browse_file(self):
        f_path = filedialog.askopenfilename(
            title="Select EEG Signal Recording",
            filetypes=[("EEG Files (*.csv, *.npy)", "*.csv *.npy"), ("CSV Files", "*.csv"), ("NumPy Arrays", "*.npy")]
        )
        if f_path:
            self._load_specific_file(f_path)

    def _on_cycle_signal(self):
        if not self.test_signal_files:
            messagebox.showinfo("Notice", "No files found in 'test_signals/' directory.")
            return
        self.current_test_idx = (self.current_test_idx + 1) % len(self.test_signal_files)
        self._load_specific_file(self.test_signal_files[self.current_test_idx])

    def _load_specific_file(self, f_path: str):
        try:
            signal = load_raw_eeg_file(f_path)
            self.current_signal = signal.astype(np.float32)
            self.current_filename = f_path
            f_name = os.path.basename(f_path)

            v_min, v_max = float(np.min(signal)), float(np.max(signal))
            v_rms = float(np.sqrt(np.mean(signal**2)))
            self.lbl_file_status.config(text=f"Loaded: {f_name}")
            self.lbl_telemetry.config(
                text=f"Dimensions: 14 Ch x 128 Pts (1.0s @ 128 Hz) | Range: [{v_min:+.2f}, {v_max:+.2f}] uV | RMS: {v_rms:.2f} uV"
            )

            # Reset prediction indicators
            self.lbl_prediction.config(text="[ READY TO DECODE ]", fg=self.accent_gold)
            self.lbl_conf_latency.config(text="Click 'DECODE EEG BRAIN SIGNAL' above", fg=self.text_muted)
            self.lbl_verify_text.config(text="Ground truth hidden. Click to verify.")

            self._plot_eeg_traces()
            self._clear_prob_plot()
        except Exception as e:
            messagebox.showerror("Error Loading Signal", str(e))

    def _plot_eeg_traces(self):
        if self.current_signal is None:
            return

        self.ax_eeg.clear()
        n_channels, n_samples = self.current_signal.shape
        t = np.linspace(0, 1.0, n_samples)
        ch_span = float(np.median(np.ptp(self.current_signal, axis=1)))
        step = max(25.0, ch_span * 1.15)
        offsets = np.arange(n_channels) * step

        for ch in range(n_channels):
            self.ax_eeg.plot(t, self.current_signal[ch] + offsets[ch], lw=1.2, color="#38bdf8")

        self.ax_eeg.set_yticks(offsets)
        self.ax_eeg.set_yticklabels(CHANNEL_NAMES, fontsize=8, color="#cbd5e1")
        self.ax_eeg.tick_params(colors="#94a3b8", labelsize=8)
        self.ax_eeg.set_xlabel("Time (seconds)", fontsize=9, color="#94a3b8")
        self.ax_eeg.set_ylabel("Electrode Channels (10-20 System)", fontsize=9, color="#94a3b8")
        self.ax_eeg.set_title("Input Raw EEG Scalp Oscillations (14 Channels)", fontsize=10, color=self.text_light)
        self.ax_eeg.grid(True, alpha=0.15, color="#475569")
        self.fig.tight_layout()
        self.canvas_eeg.draw()

    def _clear_prob_plot(self):
        self.ax_prob.clear()
        classes = [CLASS_MAP[i] for i in range(len(CLASS_MAP))]
        y_pos = np.arange(len(classes))
        self.ax_prob.barh(y_pos, np.zeros(len(classes)), color="#334155")
        self.ax_prob.set_yticks(y_pos)
        self.ax_prob.set_yticklabels(classes, fontsize=8, color="#cbd5e1")
        self.ax_prob.tick_params(colors="#94a3b8")
        self.ax_prob.set_xlim(0, 100)
        self.fig_prob.tight_layout()
        self.canvas_prob.draw()

    def _on_decode_signal(self):
        if self.current_signal is None:
            messagebox.showwarning("No Signal", "Please load an EEG signal file first.")
            return

        if self.model_pkg is None:
            self._load_model()
            if self.model_pkg is None:
                messagebox.showerror("Model Missing", "Trained model checkpoint not found in results directory.")
                return

        # Feature Extraction & Model Inference Timing
        pred_word, confidence, probs, latency_ms = predict_signal(
            self.current_signal, self.model_pkg, self.model_type
        )

        # Update UI
        self.lbl_prediction.config(text=f'"{pred_word.upper()}"', fg=self.accent_green)
        self.lbl_conf_latency.config(
            text=f"Confidence: {confidence:.1f}%  |  Inference Latency: {latency_ms:.1f} ms",
            fg=self.accent_gold
        )

        # Plot Probability Spectrum
        self.ax_prob.clear()
        classes = [CLASS_MAP[i] for i in range(len(probs))]
        colors = ["#2563eb" if c != pred_word else "#e11d48" for c in classes]

        y_pos = np.arange(len(classes))
        bars = self.ax_prob.barh(y_pos, probs * 100, color=colors, edgecolor="black", alpha=0.85)
        self.ax_prob.set_yticks(y_pos)
        self.ax_prob.set_yticklabels(classes, fontsize=8, color="#cbd5e1")
        self.ax_prob.tick_params(colors="#94a3b8")
        self.ax_prob.set_xlabel("Confidence (%)", fontsize=8, color="#94a3b8")
        self.ax_prob.set_title(f"Decoded: '{pred_word}' ({confidence:.1f}%)", fontsize=9, color=self.accent_green)
        self.ax_prob.set_xlim(0, 100)
        self.ax_prob.grid(True, axis="x", alpha=0.2, color="#475569")

        for bar, p in zip(bars, probs):
            if p * 100 > 3.0:
                self.ax_prob.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2, f"{p*100:.0f}%", va="center", fontsize=7.5, color="white")

        self.fig_prob.tight_layout()
        self.canvas_prob.draw()

    def _on_verify_ground_truth(self):
        if not self.current_filename:
            return
        base_name = os.path.basename(self.current_filename)
        reg_path = os.path.join(os.path.dirname(os.path.abspath(self.current_filename)), "ground_truth_registry.json")
        if not os.path.exists(reg_path):
            reg_path = "test_signals/ground_truth_registry.json"

        if os.path.exists(reg_path):
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg = json.load(f)
                matched = None
                if isinstance(reg, list):
                    for item in reg:
                        csv_b = os.path.basename(item.get("file_csv", ""))
                        npy_b = os.path.basename(item.get("file_npy", ""))
                        if base_name in (csv_b, npy_b, item.get("signal_id", "") + ".csv", item.get("signal_id", "") + ".npy"):
                            matched = item
                            break
                elif isinstance(reg, dict) and base_name in reg:
                    matched = reg[base_name]

                if matched is not None:
                    true_word = matched.get("true_word", matched.get("word", "Unknown"))
                    src_p = matched.get("patient_source", matched.get("category", "Mendeley EEGIS"))
                    self.lbl_verify_text.config(
                        text=f"Verified Ground Truth: {true_word}\nSource: {src_p}",
                        fg=self.accent_green
                    )
                    return
            except Exception:
                pass
        self.lbl_verify_text.config(text="Ground truth entry not found for this specific file.", fg=self.text_muted)


def main():
    root = tk.Tk()
    app = EEGDecoderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
