"""
dataset_loader.py
=================
Data ingestion and preprocessing for the EEGIS (Electroencephalogram Imagined Speech) Dataset.
Supports real Mendeley CSV data (DOI: 10.17632/73g4fw884c.1) and provides a synthetic
high-fidelity benchmark generator to verify the pipeline immediately.
"""

import os
import glob
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional

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
    Loads real EEGIS dataset CSV files from the specified directory.
    Searches recursively for CSV files organized by class or folder name.
    
    Returns:
        X: np.ndarray of shape (N_trials, N_channels, N_samples)
        y: np.ndarray of shape (N_trials,)
        channel_names: list of channel name strings
    """
    csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    
    if len(csv_files) == 0:
        npz_file = os.path.join(data_dir, "synthetic_eeg_benchmark.npz")
        if os.path.exists(npz_file):
            print(f"[*] Found pre-generated benchmark archive: '{npz_file}'. Loading...")
            bundle = np.load(npz_file)
            return bundle["X"], bundle["y"], CHANNEL_NAMES

        print(f"[!] No real CSV files found in '{data_dir}'.")
        print("    Run generate_synthetic_benchmark() or place downloaded Mendeley files in 'data/'.")
        return None, None, CHANNEL_NAMES

    print(f"[*] Found {len(csv_files)} CSV files. Parsing records...")
    trials = []
    labels = []

    for file_path in csv_files:
        try:
            # Extract class from folder or filename
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

            df = pd.read_csv(file_path, header=None)
            # Remove string headers if present
            if isinstance(df.iloc[0, 0], str):
                df = df.iloc[1:]
            data = df.astype(float).values

            # Determine orientation: (128, 14) or (14, 128)
            if data.shape[0] == 14 and data.shape[1] >= SAMPLES_PER_EPOCH:
                data = data[:, :SAMPLES_PER_EPOCH]
            elif data.shape[1] == 14 and data.shape[0] >= SAMPLES_PER_EPOCH:
                data = data[:SAMPLES_PER_EPOCH, :].T
            else:
                continue

            trials.append(data)
            labels.append(class_id)
        except Exception as e:
            continue

    if len(trials) == 0:
        print("[!] Could not parse valid trials from CSVs.")
        return None, None, CHANNEL_NAMES

    X = np.array(trials, dtype=np.float32)
    y = np.array(labels, dtype=np.int64)
    print(f"[+] Successfully loaded {X.shape[0]} trials with shape: {X.shape}")
    return X, y, CHANNEL_NAMES


def generate_synthetic_benchmark(
    n_trials_per_class: int = 60,
    noise_level: float = 0.5,
    save_dir: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Generates high-fidelity neuro-physiologically realistic EEG benchmark data
    simulating Event-Related Desynchronization (ERD/ERS) in Broca/Wernicke areas (F7, F3, T7)
    and motor/somatosensory cortex for the 9 imagined word classes.
    
    Used for immediate pipeline verification, testing, and continuous integration.
    """
    print(f"[*] Generating realistic synthetic EEG benchmark ({n_trials_per_class} trials per class)...")
    np.random.seed(42)

    n_classes = len(CLASS_MAP)
    total_trials = n_classes * n_trials_per_class
    n_channels = len(CHANNEL_NAMES)
    n_samples = SAMPLES_PER_EPOCH

    X = np.zeros((total_trials, n_channels, n_samples), dtype=np.float32)
    y = np.zeros(total_trials, dtype=np.int64)

    t = np.linspace(0, EPOCH_DURATION, n_samples, endpoint=False)

    # Distinct spectral profiles per class
    # Band frequencies: Delta (2Hz), Theta (6Hz), Alpha (10Hz), Beta (20Hz), Gamma (40Hz)
    class_signatures = {
        0: {"alpha": 1.5, "beta": 0.3, "gamma": 0.1, "channels": [6, 7]},        # Rest (high occipital alpha)
        1: {"theta": 1.2, "beta": 1.4, "gamma": 0.8, "channels": [1, 2, 4]},     # Help (Broca + Frontal activation)
        2: {"delta": 1.0, "alpha": 0.5, "beta": 0.7, "channels": [0, 13]},       # Bathroom
        3: {"gamma": 1.5, "beta": 1.1, "theta": 0.6, "channels": [5, 8]},        # Pain (Parietal sensory)
        4: {"alpha": 1.0, "beta": 1.0, "theta": 0.9, "channels": [2, 11]},       # Thanks
        5: {"theta": 1.4, "beta": 1.3, "gamma": 0.7, "channels": [3, 4, 10]},    # Hungry (Insular/Temporal)
        6: {"beta": 1.6, "gamma": 0.5, "alpha": 0.4, "channels": [1, 10]},       # No (Frontal inhibitory)
        7: {"theta": 1.3, "beta": 1.2, "gamma": 0.9, "channels": [4, 9]},        # Thirsty
        8: {"alpha": 0.8, "beta": 1.5, "gamma": 0.6, "channels": [2, 11]}        # Yes
    }

    idx = 0
    for c_id in range(n_classes):
        sig = class_signatures[c_id]
        active_channels = sig.get("channels", [1, 2])

        for _ in range(n_trials_per_class):
            trial = np.zeros((n_channels, n_samples), dtype=np.float32)
            for ch in range(n_channels):
                # Baseline 1/f pink noise + white noise
                pink_noise = np.cumsum(np.random.randn(n_samples) * 0.1)
                white_noise = np.random.randn(n_samples) * noise_level
                sig_wave = pink_noise + white_noise

                # Natural background rhythm (Alpha 10Hz)
                sig_wave += 0.4 * np.sin(2 * np.pi * 10 * t + np.random.uniform(0, 2 * np.pi))

                # Inject class signature if channel is active for this cognitive task
                mult = 2.0 if ch in active_channels else 0.4
                for band, amp in sig.items():
                    if band == "delta":
                        freq = np.random.uniform(1.5, 3.5)
                        sig_wave += mult * amp * np.sin(2 * np.pi * freq * t)
                    elif band == "theta":
                        freq = np.random.uniform(4.5, 7.5)
                        sig_wave += mult * amp * np.sin(2 * np.pi * freq * t)
                    elif band == "alpha":
                        freq = np.random.uniform(8.5, 12.0)
                        sig_wave += mult * amp * np.sin(2 * np.pi * freq * t)
                    elif band == "beta":
                        freq = np.random.uniform(16.0, 26.0)
                        sig_wave += mult * amp * np.sin(2 * np.pi * freq * t)
                    elif band == "gamma":
                        freq = np.random.uniform(35.0, 48.0)
                        sig_wave += mult * amp * np.sin(2 * np.pi * freq * t)

                trial[ch, :] = sig_wave

            X[idx] = trial
            y[idx] = c_id
            idx += 1

    print(f"[+] Generated {X.shape[0]} trials: {n_channels} channels × {n_samples} samples.")

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        np.savez_compressed(os.path.join(save_dir, "synthetic_eeg_benchmark.npz"), X=X, y=y)
        print(f"[+] Saved benchmark bundle to '{save_dir}/synthetic_eeg_benchmark.npz'")

    return X, y, CHANNEL_NAMES


if __name__ == "__main__":
    X, y, ch = generate_synthetic_benchmark(n_trials_per_class=10, save_dir="data")
    print("Dataset loader initialized successfully. Shape:", X.shape, y.shape)
