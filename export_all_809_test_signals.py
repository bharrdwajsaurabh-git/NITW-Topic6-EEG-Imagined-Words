"""
export_all_809_test_signals.py
==============================
Exports ALL 809 held-out test signals (the full 20% test partition of the 4,044-trial
Mendeley EEGIS dataset) into `test_signals/` as standalone 14-channel @ 128 Hz CSV files
along with ground_truth_registry.json.
"""

import os
import sys
import json
import numpy as np
from sklearn.model_selection import train_test_split

curr_dir = os.path.dirname(os.path.abspath(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)

from eeg_preprocessing import CHANNEL_NAMES, CLASS_MAP, SAMPLING_RATE

def main():
    print("=" * 80)
    print("  EXPORTING ALL 809 HELD-OUT TEST SIGNALS (FULL 20% TEST SET SPLIT)")
    print("=" * 80)

    data_path = os.path.join(curr_dir, "data", "eegis_6band_real.npz")
    d = np.load(data_path, allow_pickle=True)
    X, y = d["X"], d["y"]
    n_samples = len(y)

    train_idx, test_idx = train_test_split(
        np.arange(n_samples), test_size=0.20, random_state=42, stratify=y
    )
    n_test = len(test_idx)
    print(f"[*] Found {n_test} held-out test trials (20% of {n_samples}).")

    sig_dir = os.path.join(curr_dir, "test_signals")
    os.makedirs(sig_dir, exist_ok=True)

    registry = []
    print(f"[*] Writing {n_test} CSV and NPY files to '{sig_dir}'...")

    for i, g_idx in enumerate(test_idx, 1):
        raw_signal = X[g_idx, 0, :, :].copy()  # (14, 128) in uV
        c = int(y[g_idx])
        word = CLASS_MAP[c]

        sig_id_3d = f"eeg_signal_{i:03d}"
        csv_path_3d = os.path.join(sig_dir, f"{sig_id_3d}.csv")
        npy_path_3d = os.path.join(sig_dir, f"{sig_id_3d}.npy")

        # Save CSV (128 rows x 14 channels) with header
        np.savetxt(csv_path_3d, raw_signal.T, delimiter=",", header=",".join(CHANNEL_NAMES), comments="")
        np.save(npy_path_3d, raw_signal)

        # For the first 9, also save as 2-digit eeg_signal_01..09 for backwards compatibility
        if i <= 9:
            sig_id_2d = f"eeg_signal_{i:02d}"
            csv_path_2d = os.path.join(sig_dir, f"{sig_id_2d}.csv")
            npy_path_2d = os.path.join(sig_dir, f"{sig_id_2d}.npy")
            np.savetxt(csv_path_2d, raw_signal.T, delimiter=",", header=",".join(CHANNEL_NAMES), comments="")
            np.save(npy_path_2d, raw_signal)

        item_meta = {
            "signal_id": sig_id_3d,
            "test_index": i,
            "file_csv": f"test_signals/{sig_id_3d}.csv",
            "file_npy": f"test_signals/{sig_id_3d}.npy",
            "true_class_id": c,
            "true_word": word,
            "dataset_source": "EEGIS Mendeley Database (DOI: 10.17632/73g4fw884c.1)",
            "sampling_rate_hz": SAMPLING_RATE,
            "duration_sec": 1.0,
            "voltage_range_uv": [round(float(np.min(raw_signal)), 2), round(float(np.max(raw_signal)), 2)],
        }
        registry.append(item_meta)

    # Save complete ground truth registry
    reg_path = os.path.join(sig_dir, "ground_truth_registry.json")
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print(f"[+] Successfully wrote all {n_test} test signals and updated '{reg_path}'.")
    print(f"    - First signal: test_signals/eeg_signal_001.csv ({registry[0]['true_word']})")
    print(f"    - Last signal:  test_signals/eeg_signal_{n_test:03d}.csv ({registry[-1]['true_word']})")
    print("=" * 80)

if __name__ == "__main__":
    main()
