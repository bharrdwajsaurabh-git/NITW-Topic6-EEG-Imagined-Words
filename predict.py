"""
predict.py
==========
Signal-Driven Real-Time Predictor for EEG Imagined Word Decoding.
Designed for NIT Warangal BCI Project Topic 6.

Allows the user to provide ANY EEG signal:
- By index:                  python predict.py 1
- By relative/absolute file: python predict.py test_signals/eeg_signal_03.csv
- By filename:               python predict.py eeg_signal_05.npy
- By custom external file:   python predict.py "C:\\path\\to\\custom_signal.csv"
- Evaluate all in batch:     python predict.py --all
- Interactive mode:          python predict.py  (Shows menu to pick from)
"""

import os
import sys
import time
import json
import pickle
import numpy as np
import pandas as pd

# Ensure src/ and current dir are in Python path
curr_dir = os.path.dirname(os.path.abspath(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)
src_dir = os.path.join(curr_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dataset_loader import CLASS_MAP, CHANNEL_NAMES
from eeg_features import extract_trial_features, extract_single_trial_6band_from_raw
from improved_pipeline import extract_riemannian_features


def resolve_signal_path(user_input: str) -> str:
    """
    Intelligently maps user input to a valid signal file path.
    Accepts:
    - Number 1-9 (e.g. "1" -> "test_signals/eeg_signal_01.csv")
    - Direct path (e.g. "test_signals/eeg_signal_03.csv")
    - Bare filename (e.g. "eeg_signal_04.npy")
    """
    user_input = user_input.strip().strip('"').strip("'")

    # Case 1: Number 1-9
    if user_input.isdigit():
        idx = int(user_input)
        candidate_csv = os.path.join(curr_dir, "test_signals", f"eeg_signal_{idx:02d}.csv")
        candidate_npy = os.path.join(curr_dir, "test_signals", f"eeg_signal_{idx:02d}.npy")
        if os.path.exists(candidate_csv):
            return candidate_csv
        if os.path.exists(candidate_npy):
            return candidate_npy
        # Relative to current working dir
        rel_csv = os.path.join("test_signals", f"eeg_signal_{idx:02d}.csv")
        if os.path.exists(rel_csv):
            return rel_csv

    # Case 2: Exact path given
    if os.path.exists(user_input):
        return user_input

    # Case 3: Look in test_signals/ folder
    in_test_signals = os.path.join(curr_dir, "test_signals", user_input)
    if os.path.exists(in_test_signals):
        return in_test_signals

    in_cwd_test = os.path.join("test_signals", user_input)
    if os.path.exists(in_cwd_test):
        return in_cwd_test

    # Case 4: Missing extension? Try .csv or .npy
    for ext in [".csv", ".npy"]:
        cand1 = os.path.join(curr_dir, "test_signals", user_input + ext)
        if os.path.exists(cand1):
            return cand1
        cand2 = user_input + ext
        if os.path.exists(cand2):
            return cand2

    return None


def load_raw_eeg_file(file_path: str) -> np.ndarray:
    """
    Robustly loads raw 14-channel EEG data from CSV, NPY, TSV, or TXT.
    Automatically handles headers, orientations, and lengths.
    Returns: numpy array of shape (14, 128).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"EEG signal file not found: '{file_path}'")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".csv", ".tsv", ".txt"]:
        sep = "\t" if ext == ".tsv" else ","
        try:
            df = pd.read_csv(file_path, sep=sep)
        except Exception:
            df = pd.read_csv(file_path, sep=r"\s+")

        # If header exists, drop non-numeric or use values
        data = df.apply(pd.to_numeric, errors="coerce").dropna().values
        if data.size == 0:
            data = np.genfromtxt(file_path, delimiter=sep)
        if data.ndim == 2 and data.shape[1] == 15 and data.shape[0] >= 128:
            data = data[:, 1:]

        # Handle orientations
        if data.shape[0] == 14 and data.shape[1] >= 128:
            signal = data[:, :128]
        elif data.shape[1] == 14 and data.shape[0] >= 128:
            signal = data[:128, :].T
        elif data.shape[0] == 14 and data.shape[1] < 128:
            # Pad
            signal = np.pad(data, ((0, 0), (0, 128 - data.shape[1])), mode="edge")
        elif data.shape[1] == 14 and data.shape[0] < 128:
            signal = np.pad(data.T, ((0, 0), (0, 128 - data.shape[0])), mode="edge")
        else:
            raise ValueError(f"Unrecognized signal matrix shape {data.shape}. Expected 14 electrode columns.")

    elif ext == ".npy":
        arr = np.load(file_path)
        arr = np.squeeze(arr)
        if arr.shape == (14, 128):
            signal = arr
        elif arr.shape == (128, 14):
            signal = arr.T
        elif arr.ndim == 2 and arr.shape[0] == 14:
            signal = arr[:, :128] if arr.shape[1] >= 128 else np.pad(arr, ((0,0),(0,128-arr.shape[1])), mode='edge')
        elif arr.ndim == 2 and arr.shape[1] == 14:
            arr_t = arr.T
            signal = arr_t[:, :128] if arr_t.shape[1] >= 128 else np.pad(arr_t, ((0,0),(0,128-arr_t.shape[1])), mode='edge')
        else:
            raise ValueError(f"Unrecognized NPY shape {arr.shape}. Expected (14, 128) or (128, 14).")
    else:
        raise ValueError(f"Unsupported signal format '{ext}'. Please supply a .csv or .npy file.")

    return signal.astype(np.float32)


def load_best_model():
    """
    Loads the trained model:
    Prioritizes the proposed AGA-Riemannian Ensemble (best_improved_ensemble.pkl).
    Falls back to best_ml_pipeline.pkl.
    """
    improved_path = os.path.join(curr_dir, "results", "best_improved_ensemble.pkl")
    fallback_path = os.path.join(curr_dir, "results", "best_ml_pipeline.pkl")

    if os.path.exists(improved_path):
        with open(improved_path, "rb") as f:
            pkg = pickle.load(f)
        return pkg, "improved"
    elif os.path.exists(fallback_path):
        with open(fallback_path, "rb") as f:
            pkg = pickle.load(f)
        return pkg, "baseline"
    else:
        raise FileNotFoundError(
            f"No trained model found in '{os.path.join(curr_dir, 'results')}'. Run 'python improved_pipeline.py' first."
        )


def predict_signal(signal: np.ndarray, model_pkg: dict, model_type: str):
    """
    Runs feature extraction, dimensionality pruning, and ensemble classification.
    Returns: pred_word, confidence, probs, latency_ms
    """
    t_start = time.perf_counter()

    if model_type == "improved":
        scaler = model_pkg["scaler"]
        ensemble = model_pkg["ensemble"]

        if model_pkg.get("mode") == "fb_riemannian_6band":
            # 6-Band Filter-Bank Riemannian extraction via 4th-order Butterworth filtfilt (630D)
            f_riem = extract_single_trial_6band_from_raw(signal, fs=128)
            f_scaled = scaler.transform(f_riem)
            band_w = model_pkg.get("band_weights")
            if band_w is not None:
                f_opt = f_scaled.copy()
                for b_idx, w in enumerate(band_w):
                    f_opt[:, b_idx * 105 : (b_idx + 1) * 105] *= float(w)
            else:
                f_opt = f_scaled
            probs = ensemble.predict_proba(f_opt)[0]
        else:
            aga = model_pkg["aga"]
            base_f, _ = extract_trial_features(signal, CHANNEL_NAMES, fs=128)
            base_f = base_f.reshape(1, -1)
            riem_f = extract_riemannian_features(signal[np.newaxis, :, :])
            f_fused = np.hstack([base_f, riem_f])
            f_scaled = scaler.transform(f_fused)
            f_opt = aga.transform(f_scaled)
            probs = ensemble.predict_proba(f_opt)[0]
    else:
        scaler = model_pkg["scaler"]
        selector = model_pkg.get("selector")
        clf = model_pkg["classifier"]

        base_f, _ = extract_trial_features(signal, CHANNEL_NAMES, fs=128)
        base_f = base_f.reshape(1, -1)
        f_scaled = scaler.transform(base_f)
        f_opt = selector.transform(f_scaled) if selector is not None else f_scaled
        probs = clf.predict_proba(f_opt)[0]

    pred_idx = int(np.argmax(probs))
    pred_word = CLASS_MAP[pred_idx]
    confidence = float(probs[pred_idx] * 100.0)
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    return pred_word, confidence, probs, latency_ms


def plot_prediction_result(signal: np.ndarray, pred_word: str, confidence: float, probs: np.ndarray, save_path="results/sample_prediction.png"):
    """Saves a multi-channel waveform and probability distribution visualization."""
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.4, 1.0]})

    n_channels, n_samples = signal.shape
    t = np.linspace(0, 1.0, n_samples)
    ch_span = float(np.median(np.ptp(signal, axis=1)))
    step = max(25.0, ch_span * 1.15)
    offsets = np.arange(n_channels) * step

    # 1. 14-Channel Oscilloscope Waveforms
    for ch in range(n_channels):
        ax1.plot(t, signal[ch] + offsets[ch], lw=1.1, label=CHANNEL_NAMES[ch])

    ax1.set_yticks(offsets)
    ax1.set_yticklabels(CHANNEL_NAMES, fontsize=9)
    ax1.set_xlabel("Time (seconds)", fontsize=11)
    ax1.set_ylabel("Electrodes (10-20 Montage)", fontsize=11)
    ax1.set_title("Input Raw Scalp Voltages (14 Channels @ 128 Hz)", fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.25)

    # 2. Probability Distribution
    classes = [CLASS_MAP[i] for i in range(len(probs))]
    colors = ["#2b5c8f" if c != pred_word else "#e63946" for c in classes]

    y_pos = np.arange(len(classes))
    bars = ax2.barh(y_pos, probs * 100, color=colors, edgecolor="black", alpha=0.85)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(classes, fontsize=10)
    ax2.set_xlabel("Decoded Confidence (%)", fontsize=11)
    ax2.set_title(f"Decoded: '{pred_word}' ({confidence:.1f}%)", fontsize=13, fontweight="bold", color="#e63946")
    ax2.set_xlim(0, 100)
    ax2.grid(True, axis="x", alpha=0.3)

    for bar, p in zip(bars, probs):
        if p * 100 > 3.0:
            ax2.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2, f"{p*100:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def load_ground_truth_registry(reg_path: str = None) -> dict:
    """Loads ground truth registry mapping filename to word."""
    if reg_path is None:
        reg_path = os.path.join(curr_dir, "test_signals", "ground_truth_registry.json")
    registry = {}
    if not os.path.exists(reg_path):
        return registry
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                word = item.get("true_word", item.get("word", "Unknown"))
                csv_b = os.path.basename(item.get("file_csv", ""))
                npy_b = os.path.basename(item.get("file_npy", ""))
                if csv_b:
                    registry[csv_b] = word
                if npy_b:
                    registry[npy_b] = word
                if "signal_id" in item:
                    registry[item["signal_id"] + ".csv"] = word
                    registry[item["signal_id"] + ".npy"] = word
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    registry[k] = v.get("true_word", v.get("word", "Unknown"))
                elif isinstance(v, str):
                    registry[k] = v
    except Exception:
        pass
    return registry


def print_single_prediction(file_path: str, model_pkg: dict, model_type: str):
    """Loads signal, runs prediction, and displays clean output."""
    signal = load_raw_eeg_file(file_path)
    pred_word, confidence, probs, latency_ms = predict_signal(signal, model_pkg, model_type)

    # Check ground truth registry if available
    registry = load_ground_truth_registry()
    base_name = os.path.basename(file_path)
    ground_truth = registry.get(base_name)

    # Print Clean Signal Telemetry & Output
    print("\n" + "=" * 76)
    print("      NIT WARANGAL — CS26001: ADVANCED ALGORITHMS (TOPIC 6)")
    print(f"      Model Engine: {model_pkg.get('type', 'Proposed MDRC-AGA v2: 6-Band FB-Riemannian Consensus')}")
    print("=" * 76)
    print(f"[*] Input File:             {file_path}")
    print(f"[*] Electrodes Ingested:    14 channels (AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4)")
    print(f"[*] Signal Duration:        1.0 second (128 samples @ 128 Hz)")
    print(f"[*] Voltage Dynamic Range:  [{np.min(signal):.2f} uV, {np.max(signal):.2f} uV] (Mean: {np.mean(signal):.2f} uV)")
    print("-" * 76)

    # Ground Truth Audit
    if ground_truth:
        match_str = "[MATCH]" if ground_truth == pred_word else "[MISMATCH]"
        print(f"[>] Ground Truth Thought:   '{ground_truth}'")
        print(f"[>] Model Decoded Output:   '{pred_word}' ({confidence:.2f}% Confidence) {match_str}")
    else:
        print(f"[>] Model Decoded Output:   '{pred_word}' ({confidence:.2f}% Confidence)")

    print(f"[*] Total Inference Latency: {latency_ms:.1f} ms  (> 10x faster than 1.0 s acquisition)")
    print("-" * 76)

    # Print Probability Bars
    print("PROBABILITY DISTRIBUTION (All 9 Vocabulary Targets):")
    for i in range(len(CLASS_MAP)):
        w_name = CLASS_MAP[i]
        p_val = probs[i] * 100.0
        bar_len = int(p_val / 2.5)
        bar_char = "#" if w_name == pred_word else "="
        bar_str = bar_char * bar_len
        marker = " <== PREDICTED" if w_name == pred_word else ""
        print(f"  {w_name:<18} [{bar_str:<40}] {p_val:5.1f}%{marker}")
    print("=" * 76)

    save_fig = os.path.join(curr_dir, "results", "sample_prediction.png")
    plot_prediction_result(signal, pred_word, confidence, probs, save_path=save_fig)
    print(f"[+] Prediction visualization saved to '{save_fig}'\n")


def evaluate_all_test_signals(model_pkg: dict, model_type: str):
    """Evaluates all signals in test_signals/ and prints a complete summary table."""
    sig_dir = os.path.join(curr_dir, "test_signals")
    if not os.path.exists(sig_dir):
        print(f"[!] 'test_signals/' directory not found at {sig_dir}")
        return

    csv_files = [os.path.join(sig_dir, f) for f in sorted(os.listdir(sig_dir)) if f.endswith(".csv")]
    if not csv_files:
        print("[!] No .csv files found in 'test_signals/'.")
        return

    registry = load_ground_truth_registry()

    print("\n" + "=" * 80)
    print("     NIT WARANGAL — CS26001: ADVANCED ALGORITHMS (BENCHMARK EVALUATION)")
    print("=" * 80)
    print(f"{'#':<4} {'Signal File':<20} {'Ground Truth':<18} {'Decoded Thought':<18} {'Conf (%)':<10} {'Latency':<8} {'Status'}")
    print("-" * 80)

    correct = 0
    total = len(csv_files)
    latencies = []

    for idx, fpath in enumerate(csv_files, 1):
        fname = os.path.basename(fpath)
        signal = load_raw_eeg_file(fpath)
        pred_word, conf, probs, lat = predict_signal(signal, model_pkg, model_type)
        latencies.append(lat)

        gt = registry.get(fname, "Unknown")
        is_match = (gt == pred_word)
        if is_match:
            correct += 1
        status = "[MATCH]" if is_match else "[MISMATCH]"

        print(f"{idx:<4} {fname:<20} {gt:<18} {pred_word:<18} {conf:<10.1f} {lat:<8.1f} {status}")

    acc = (correct / total) * 100.0 if total > 0 else 0
    avg_lat = np.mean(latencies) if latencies else 0

    print("=" * 80)
    print(f"[*] Summary: {correct}/{total} Correct ({acc:.1f}% Accuracy) | Mean Latency: {avg_lat:.1f} ms")
    print("=" * 80 + "\n")


def interactive_menu(model_pkg: dict, model_type: str):
    """Interactive CLI menu when user runs without arguments."""
    sig_dir = os.path.join(curr_dir, "test_signals")
    files = []
    if os.path.exists(sig_dir):
        files = [f for f in sorted(os.listdir(sig_dir)) if f.endswith(".csv")]

    print("\n" + "=" * 76)
    print("       NIT WARANGAL — CS26001: ADVANCED ALGORITHMS (TOPIC 6)")
    print("=" * 76)
    print("[?] Select a test signal or enter a custom file path:")
    for i, fname in enumerate(files, 1):
        print(f"  [{i}] test_signals/{fname}")
    print("  [A] Run ALL test signals in batch mode")
    print("  [C] Or type any custom .csv/.npy file path")
    print("=" * 76)

    try:
        choice = input("Enter choice (1-9, A, or file path) [Default: 1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if not choice:
        choice = "1"

    if choice.upper() in ["A", "ALL"]:
        evaluate_all_test_signals(model_pkg, model_type)
    else:
        resolved = resolve_signal_path(choice)
        if resolved:
            print_single_prediction(resolved, model_pkg, model_type)
        else:
            print(f"\n[!] Error: '{choice}' is not a recognized signal file or index.")
            print("[i] Usage examples:")
            print("    python predict.py 1")
            print("    python predict.py test_signals/eeg_signal_03.csv")
            print("    python predict.py --all")


def main():
    model_pkg, model_type = load_best_model()

    if len(sys.argv) == 1:
        # Check if stdin is interactive
        if sys.stdin.isatty():
            interactive_menu(model_pkg, model_type)
        else:
            # Non-interactive default to signal 1
            def_path = os.path.join(curr_dir, "test_signals", "eeg_signal_01.csv")
            print_single_prediction(def_path, model_pkg, model_type)
        return

    arg = sys.argv[1].strip()

    if arg in ["--all", "-a", "all", "ALL"]:
        evaluate_all_test_signals(model_pkg, model_type)
        return

    resolved = resolve_signal_path(arg)
    if resolved:
        print_single_prediction(resolved, model_pkg, model_type)
    else:
        print(f"\n[!] Error: Input '{arg}' is neither a recognized EEG signal file nor a signal index (1-9).")
        print("[i] How to use:")
        print("    python predict.py 1                          (Quick-select signal 1)")
        print("    python predict.py test_signals/eeg_signal_04.csv")
        print("    python predict.py \"C:\\path\\to\\patient_record.csv\"")
        print("    python predict.py --all                      (Batch evaluate all signals)")
        print("    python predict.py                            (Interactive selection menu)\n")


if __name__ == "__main__":
    main()
