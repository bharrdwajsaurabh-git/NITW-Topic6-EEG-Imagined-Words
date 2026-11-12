"""
predict.py
==========
Offline Single-Epoch CLI Decoder for Imagined-Speech EEG Research Prototype.
Designed for NIT Warangal CS26001 Project Topic 6.

Remediated audit items (Flaws #19-#23, #28-#30):
  - Uses canonical `eeg_preprocessing.load_eeg_epoch_file` + `preprocess_epoch` identical to training
  - Rejects incomplete (<128 samples), NaN/Inf, wrong-channel, wrong-fs inputs cleanly (zero edge padding)
  - Supports calibrated posteriors (`CalibratedManifoldStacker`) and clearly distinguishes calibrated
    probabilities from un-calibrated heuristic neighbor vote scores
  - Reports offline per-epoch breakdown latency (I/O, preprocess, features, classification) rather
    than claiming real-time hardware acquisition loop latency
  - Zero silent exception swallowing
"""

import os
import sys
import time
import json
import pickle
import argparse
import numpy as np

curr_dir = os.path.dirname(os.path.abspath(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)
src_dir = os.path.join(curr_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eeg_preprocessing import (
    CHANNEL_NAMES,
    CLASS_MAP,
    SAMPLING_RATE,
    SAMPLES_PER_EPOCH,
    load_eeg_epoch_file,
    preprocess_epoch,
)
from eeg_features import (
    extract_trial_features,
    extract_single_trial_6band_from_raw,
    extract_single_trial_v3_from_raw,
    _spd_tangent_batch,
)


def resolve_signal_path(user_input: str) -> str:
    """Maps numeric shortcut 1-9, filename, or explicit path to a verified signal file path."""
    user_input = user_input.strip().strip('"').strip("'")
    if user_input.isdigit():
        idx = int(user_input)
        for ext in (".csv", ".npy"):
            for base in (os.path.join(curr_dir, "test_signals"), "test_signals"):
                cand = os.path.join(base, f"eeg_signal_{idx:02d}{ext}")
                if os.path.exists(cand):
                    return cand

    for cand in (
        user_input,
        os.path.join(curr_dir, "test_signals", user_input),
        os.path.join("test_signals", user_input),
    ):
        if os.path.exists(cand):
            return cand

    for ext in (".csv", ".tsv", ".txt", ".npy"):
        for cand in (os.path.join(curr_dir, "test_signals", user_input + ext), user_input + ext):
            if os.path.exists(cand):
                return cand
    return None


def load_raw_eeg_file(file_path: str, sampling_rate_hz: float = None) -> np.ndarray:
    """
    Strictly validates and loads a 14-channel, >=128-sample EEG epoch file via canonical `eeg_preprocessing`.
    Never pads short arrays or drops numeric row 0. Returns float32 (14, 128).
    """
    raw = load_eeg_epoch_file(
        file_path,
        expected_fs=SAMPLING_RATE,
        min_samples=SAMPLES_PER_EPOCH,
        allow_longer=False,
        sampling_rate_hz=sampling_rate_hz,
    )
    return preprocess_epoch(raw, expected_channels=14, min_samples=SAMPLES_PER_EPOCH)


def load_best_model():
    """Loads the active audited model bundle (v4 Fold-Tangent Calibrated Stacker prioritized)."""
    improved_path = os.path.join(curr_dir, "results", "best_improved_ensemble.pkl")
    if os.path.exists(improved_path):
        with open(improved_path, "rb") as f:
            pkg = pickle.load(f)
        return pkg, "improved"
    legacy_path = os.path.join(curr_dir, "results", "legacy_720_archive", "best_ml_pipeline.pkl")
    if os.path.exists(legacy_path):
        with open(legacy_path, "rb") as f:
            pkg = pickle.load(f)
        return pkg, "legacy_baseline"
    raise FileNotFoundError(
        f"No trained model bundle found at '{improved_path}'. Run 'python improved_pipeline.py' first."
    )


def predict_signal(signal: np.ndarray, model_pkg: dict, model_type: str, return_breakdown: bool = False):
    """
    Runs canonical preprocessing parity, feature extraction, and classification.
    Returns:
      pred_word, score_pct, probs, total_ms (and optionally breakdown dict if return_breakdown=True).
    """
    t0 = time.perf_counter()
    proc_sig = preprocess_epoch(signal, expected_channels=14, min_samples=SAMPLES_PER_EPOCH)
    t1 = time.perf_counter()

    if model_type == "improved":
        scaler = model_pkg["scaler"]
        ensemble = model_pkg["ensemble"]
        mode = model_pkg.get("mode", "")

        if mode == "mdrc_aga_v4_fold_tangent_calibrated":
            ext = model_pkg["tangent_extractor"]
            aga = model_pkg["aga"]
            feats = ext.transform(proc_sig[None, :, :])
            f_opt = aga.transform(scaler.transform(feats))
            t2 = time.perf_counter()
            probs = ensemble.predict_proba(f_opt)[0]
        elif mode == "mdrc_aga_v3_13b_speech10":
            feats = extract_single_trial_v3_from_raw(proc_sig, fs=SAMPLING_RATE)
            f_scaled = scaler.transform(feats)
            scale_w = model_pkg.get("scale_weights")
            block_dims = model_pkg.get("block_dims", (630, 735, 330))
            if scale_w is not None:
                f_opt = f_scaled.copy()
                s = 0
                for dim, w in zip(block_dims, scale_w):
                    f_opt[:, s : s + dim] *= float(w)
                    s += dim
            else:
                f_opt = f_scaled
            t2 = time.perf_counter()
            probs = ensemble.predict_proba(f_opt)[0]
        else:
            f_riem = _spd_tangent_batch(proc_sig[None, :, :])
            base_f, _ = extract_trial_features(proc_sig, CHANNEL_NAMES, fs=SAMPLING_RATE, detrend=True)
            f_fused = np.hstack([base_f.reshape(1, -1), f_riem])
            f_scaled = scaler.transform(f_fused)
            f_opt = model_pkg["aga"].transform(f_scaled)
            t2 = time.perf_counter()
            probs = ensemble.predict_proba(f_opt)[0]
    else:
        base_f, _ = extract_trial_features(proc_sig, CHANNEL_NAMES, fs=SAMPLING_RATE, detrend=True)
        f_scaled = model_pkg["scaler"].transform(base_f.reshape(1, -1))
        sel = model_pkg.get("selector")
        f_opt = sel.transform(f_scaled) if sel is not None else f_scaled
        t2 = time.perf_counter()
        probs = model_pkg["classifier"].predict_proba(f_opt)[0]

    t3 = time.perf_counter()
    pred_idx = int(np.argmax(probs))
    pred_word = CLASS_MAP[pred_idx]
    score_pct = float(probs[pred_idx] * 100.0)
    total_ms = (t3 - t0) * 1000.0

    if return_breakdown:
        breakdown = {
            "preprocess_ms": round((t1 - t0) * 1000.0, 2),
            "feature_extract_ms": round((t2 - t1) * 1000.0, 2),
            "classify_ms": round((t3 - t2) * 1000.0, 2),
            "total_offline_epoch_ms": round(total_ms, 2),
            "is_calibrated": bool(model_pkg.get("is_calibrated_probabilities", getattr(model_pkg.get("ensemble"), "is_calibrated_probabilities", False))),
        }
        return pred_word, score_pct, probs, total_ms, breakdown
    return pred_word, score_pct, probs, total_ms


def plot_prediction_result(
    signal: np.ndarray,
    pred_word: str,
    score_pct: float,
    probs: np.ndarray,
    is_calibrated: bool = True,
    save_path: str = "results/sample_prediction.png",
):
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.4, 1.0]})

    n_channels, n_samples = signal.shape
    t = np.linspace(0, 1.0, n_samples)
    ch_span = float(np.median(np.ptp(signal, axis=1)))
    step = max(25.0, ch_span * 1.15)
    offsets = np.arange(n_channels) * step

    for ch in range(n_channels):
        ax1.plot(t, signal[ch] + offsets[ch], lw=1.1, label=CHANNEL_NAMES[ch])
    ax1.set_yticks(offsets)
    ax1.set_yticklabels(CHANNEL_NAMES, fontsize=9)
    ax1.set_xlabel("Time (seconds)", fontsize=11)
    ax1.set_ylabel("Electrodes (10-20 Montage)", fontsize=11)
    ax1.set_title("Detrended Input EEG Epoch (14 Channels @ 128 Hz)", fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.25)

    classes = [CLASS_MAP[i] for i in range(len(probs))]
    colors = ["#2b5c8f" if c != pred_word else "#e63946" for c in classes]
    prob_label = "Calibrated Class Posterior (%)" if is_calibrated else "Un-calibrated Vote Share (%)"

    y_pos = np.arange(len(classes))
    bars = ax2.barh(y_pos, probs * 100, color=colors, edgecolor="black", alpha=0.85)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(classes, fontsize=10)
    ax2.set_xlabel(prob_label, fontsize=11)
    ax2.set_title(f"Decoded: '{pred_word}' ({score_pct:.1f}%)", fontsize=13, fontweight="bold", color="#e63946")
    ax2.set_xlim(0, 100)
    ax2.grid(True, axis="x", alpha=0.3)

    for bar, p in zip(bars, probs):
        if p * 100 > 3.0:
            ax2.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2, f"{p*100:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def load_ground_truth_registry(reg_path: str = None) -> dict:
    """Loads ground truth registry mapping filename to word with explicit parse error reporting."""
    if reg_path is None:
        reg_path = os.path.join(curr_dir, "test_signals", "ground_truth_registry.json")
    registry = {}
    if not os.path.exists(reg_path):
        return registry
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
            registry[k] = v.get("true_word", v.get("word", "Unknown")) if isinstance(v, dict) else str(v)
    return registry


def print_single_prediction(file_path: str, model_pkg: dict, model_type: str, fs_arg: float = None):
    t_io0 = time.perf_counter()
    signal = load_raw_eeg_file(file_path, sampling_rate_hz=fs_arg)
    io_ms = (time.perf_counter() - t_io0) * 1000.0
    pred_word, score_pct, probs, inf_ms, bd = predict_signal(signal, model_pkg, model_type, return_breakdown=True)

    registry = load_ground_truth_registry()
    ground_truth = registry.get(os.path.basename(file_path))
    score_kind = "Calibrated Posterior" if bd["is_calibrated"] else "Un-calibrated Vote Score"

    print("\n" + "=" * 78)
    print("  NIT WARANGAL — OFFLINE EEG IMAGINED-WORD DECODER (RESEARCH PROTOTYPE)")
    print(f"  Engine Mode: {model_pkg.get('mode', 'custom')} (Held-out Test Split | Stage 2 MDRC-AGA)")
    print("=" * 78)
    print(f"[*] Input File:             {file_path}")
    print(f"[*] Electrodes Verified:    14 channels ({', '.join(CHANNEL_NAMES[:5])}...)")
    print(f"[*] Epoch Shape:            14 x 128 (1.0 s @ 128 Hz; zero-mean DC detrended)")
    print(f"[*] Voltage Range (uV):     [{np.min(signal):.2f}, {np.max(signal):.2f}]")
    print("-" * 78)
    if ground_truth:
        match_str = "[MATCH]" if ground_truth == pred_word else "[MISMATCH]"
        print(f"[>] Registry Reference:     '{ground_truth}'")
        print(f"[>] Predicted Class:        '{pred_word}' ({score_pct:.2f}% {score_kind}) {match_str}")
    else:
        print(f"[>] Predicted Class:        '{pred_word}' ({score_pct:.2f}% {score_kind})")
    print(
        f"[*] Offline Epoch Latency:  Load+Validate={io_ms:.1f} ms | Features={bd['feature_extract_ms']:.1f} ms | "
        f"Classify={bd['classify_ms']:.1f} ms (Compute={inf_ms:.1f} ms)"
    )
    print("-" * 78)
    print(f"{score_kind.upper()} DISTRIBUTION (9 Vocabulary Targets):")
    for i in range(len(CLASS_MAP)):
        w_name = CLASS_MAP[i]
        p_val = probs[i] * 100.0
        bar_str = ("#" if w_name == pred_word else "=") * int(p_val / 2.5)
        marker = " <== PREDICTED" if w_name == pred_word else ""
        print(f"  {w_name:<18} [{bar_str:<40}] {p_val:5.1f}%{marker}")
    print("=" * 78)

    save_fig = os.path.join(curr_dir, "results", "sample_prediction.png")
    plot_prediction_result(signal, pred_word, score_pct, probs, is_calibrated=bd["is_calibrated"], save_path=save_fig)
    print(f"[+] Offline epoch plot saved to '{save_fig}'\n")


def evaluate_all_test_signals(model_pkg: dict, model_type: str, fs_arg: float = None):
    sig_dir = os.path.join(curr_dir, "test_signals")
    csv_files = [os.path.join(sig_dir, f) for f in sorted(os.listdir(sig_dir)) if f.endswith(".csv")] if os.path.exists(sig_dir) else []
    if not csv_files:
        print("[!] No .csv files found in 'test_signals/'.")
        return

    registry = load_ground_truth_registry()
    is_cal = bool(model_pkg.get("is_calibrated_probabilities", False))
    score_col = "Cal.Prob%" if is_cal else "VoteScore%"

    print("\n" + "=" * 82)
    print("  NIT WARANGAL — OFFLINE 9-SIGNAL DEMO (HELD-OUT 20% TEST SET SPLIT)")
    print("  NOTE: 1 sample per class from held-out test split; 14 channels @ 128 Hz.")
    print("=" * 82)
    print(f"{'#':<4} {'Signal File':<20} {'Reference':<18} {'Predicted':<18} {score_col:<10} {'ComputeMs':<9} {'Status'}")
    print("-" * 82)

    correct, latencies = 0, []
    for idx, fpath in enumerate(csv_files, 1):
        fname = os.path.basename(fpath)
        sig = load_raw_eeg_file(fpath, sampling_rate_hz=fs_arg)
        pred_word, score_pct, _, lat = predict_signal(sig, model_pkg, model_type)
        latencies.append(lat)
        gt = registry.get(fname, "Unknown")
        is_match = gt == pred_word
        if is_match:
            correct += 1
        print(f"{idx:<4} {fname:<20} {gt:<18} {pred_word:<18} {score_pct:<10.1f} {lat:<9.1f} {'[MATCH]' if is_match else '[MISMATCH]'}")

    print("=" * 82)
    print(f"[*] 9-File Offline Format Check: {correct}/{len(csv_files)} Matched ({correct/len(csv_files)*100:.1f}%) | Mean Compute: {np.mean(latencies):.1f} ms/epoch")
    print("=" * 82 + "\n")


def interactive_menu(model_pkg: dict, model_type: str):
    """Interactive CLI selector for offline demo EEG files."""
    sig_dir = os.path.join(curr_dir, "test_signals")
    files = [f for f in sorted(os.listdir(sig_dir)) if f.endswith(".csv")] if os.path.exists(sig_dir) else []
    print("\n" + "=" * 78)
    print("  NIT WARANGAL — OFFLINE EEG IMAGINED-WORD DECODER MENU")
    print("=" * 78)
    for i, fname in enumerate(files, 1):
        print(f"  [{i}] test_signals/{fname}")
    print("  [A] Run ALL offline demo files in batch mode")
    try:
        choice = input("Enter choice (1-9, A, or file path) [Default: 1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"
    if choice.upper() in ("A", "ALL"):
        evaluate_all_test_signals(model_pkg, model_type)
    else:
        resolved = resolve_signal_path(choice)
        if resolved:
            print_single_prediction(resolved, model_pkg, model_type)
        else:
            print(f"[!] Error: Signal '{choice}' not found.")


def main():
    parser = argparse.ArgumentParser(description="Offline Imagined-Word EEG Epoch Decoder")
    parser.add_argument("target", nargs="?", default=None, help="Signal index (1-9), file path, or --all")
    parser.add_argument("--all", "-a", action="store_true", help="Evaluate all test_signals/*.csv")
    parser.add_argument("--fs", type=float, default=None, help="Declared sampling rate (must be 128 Hz)")
    args = parser.parse_args()

    model_pkg, model_type = load_best_model()
    if args.all or (args.target and args.target.strip().lower() in ("--all", "-a", "all")):
        evaluate_all_test_signals(model_pkg, model_type, fs_arg=args.fs)
        return

    target = args.target
    if target is None:
        target = "1"
    resolved = resolve_signal_path(target)
    if resolved:
        print_single_prediction(resolved, model_pkg, model_type, fs_arg=args.fs)
    else:
        print(f"[!] Error: Signal '{target}' not found.")
        sys.exit(2)


if __name__ == "__main__":
    main()
