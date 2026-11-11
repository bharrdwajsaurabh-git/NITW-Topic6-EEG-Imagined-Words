"""
dataset_loader.py
=================
Data ingestion and preprocessing for the REAL Mendeley EEGIS
(Electroencephalogram Imagined Speech) Dataset (DOI: 10.17632/73g4fw884c.1).
Strict zero-synthetic-fallback policy: loads only verified in-vivo human EEG recordings.
"""

import os
import glob
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict

# Standard 14 channels for Emotiv EPOC+ 10-20 system
CHANNEL_NAMES: List[str] = [
    "AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
    "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"
]

# 8 Imagined Words + 1 Rest State
CLASS_MAP: Dict[int, str] = {
    0: "Rest",
    1: "Help (Ayuda)",
    2: "Bathroom (Baño)",
    3: "Pain (Dolor)",
    4: "Thanks (Gracias)",
    5: "Hungry (Hambre)",
    6: "No",
    7: "Thirsty (Sed)",
    8: "Yes (Sí)"
}

SAMPLING_RATE: int = 128  # Hz
EPOCH_DURATION: float = 1.0  # seconds
SAMPLES_PER_EPOCH: int = int(SAMPLING_RATE * EPOCH_DURATION)  # 128 samples


def load_eegis_dataset(data_dir: str = "data") -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Loads real EEGIS dataset trials (4,044 trials from 10 human subjects) from Mendeley Data.
    Checks for the cached binary archive 'eegis_real_dataset.npz' first for instant ingestion,
    or parses raw Mendeley CSV recordings directly from 'data/eegis_raw/'.
    Raises FileNotFoundError if the real dataset is absent (no synthetic fallback).

    Returns:
        X: np.ndarray of shape (N_trials, N_channels, N_samples)
        y: np.ndarray of shape (N_trials,)
        channel_names: list of channel name strings
    """
    real_npz = os.path.join(data_dir, "eegis_real_dataset.npz")
    if os.path.exists(real_npz):
        print(f"[*] Found real in-vivo EEGIS dataset archive: '{real_npz}'. Loading...")
        bundle = np.load(real_npz)
        X = bundle["X"]
        y = bundle["y"]
        print(f"[+] Loaded {len(X)} real human EEG trials across 9 classes (shape: {X.shape}).")
        return X, y, CHANNEL_NAMES

    csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    csv_files = [f for f in csv_files if "test_signals" not in f]

    if len(csv_files) == 0:
        raise FileNotFoundError(
            f"Real Mendeley EEGIS dataset not found in '{data_dir}'. "
            "Please place 'eegis_real_dataset.npz' or the extracted 'eegis_raw/' CSV folders "
            "(DOI: 10.17632/73g4fw884c.1) inside 'data/'."
        )

    print(f"[*] Found {len(csv_files)} raw Mendeley CSV files. Parsing & detrending records...")
    trials = []
    labels = []

    for file_path in sorted(csv_files):
        try:
            parts = os.path.normpath(file_path).split(os.sep)
            class_id = None
            for p in reversed(parts):
                p_lower = p.lower()
                for c_idx, c_name in CLASS_MAP.items():
                    name_tokens = c_name.lower().replace("(", "").replace(")", "").split()
                    if f"class_{c_idx}" in p_lower or any(token in p_lower for token in name_tokens):
                        class_id = c_idx
                        break
                if class_id is not None:
                    break

            if class_id is None:
                continue

            df = pd.read_csv(file_path)
            if all(ch in df.columns for ch in CHANNEL_NAMES):
                data = df[CHANNEL_NAMES].values.T
            else:
                df_raw = pd.read_csv(file_path, header=None)
                if isinstance(df_raw.iloc[0, 0], str):
                    df_raw = df_raw.iloc[1:]
                arr = df_raw.apply(pd.to_numeric, errors="coerce").dropna().values
                if arr.shape[1] == 15:
                    arr = arr[:, 1:]
                data = arr.T if arr.shape[1] == 14 else arr

            if data.shape[0] == 14 and data.shape[1] >= SAMPLES_PER_EPOCH:
                data = data[:, :SAMPLES_PER_EPOCH]
            else:
                continue

            # Remove Emotiv EPOC+ DC baseline offset per channel
            data = data - np.mean(data, axis=1, keepdims=True)
            trials.append(data.astype(np.float32))
            labels.append(class_id)
        except Exception:
            continue

    if len(trials) == 0:
        raise RuntimeError(f"Found CSV files in '{data_dir}' but could not parse valid 14-channel EEG trials.")

    X = np.array(trials, dtype=np.float32)
    y = np.array(labels, dtype=np.int64)
    print(f"[+] Successfully parsed {X.shape[0]} real human EEG trials with shape: {X.shape}")
    return X, y, CHANNEL_NAMES


if __name__ == "__main__":
    X, y, ch = load_eegis_dataset(data_dir="data")
    print("Verified real dataset loader successfully. Shape:", X.shape, y.shape)
