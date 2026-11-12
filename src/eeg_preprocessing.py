"""
eeg_preprocessing.py
====================
Canonical, shared EEG ingestion, validation, and preprocessing module for BOTH
training (`dataset_loader.py`, pipelines) and offline inference (`predict.py`, `eeg_gui_tester.py`).

Fixes audit items:
  - Identical preprocessing path across training and inference (Flaw #19)
  - Rejects incomplete (<128 samples), non-finite, wrong-channel, swapped-header,
    or wrong-sampling-rate inputs with explicit ValueError messages; zero silent edge padding (Flaws #20, #22)
  - Explicitly distinguishes headered CSVs (reordering columns by CHANNEL_NAMES and stripping
    only a confirmed index column) vs headerless CSVs (never losing sample row 0) (Flaw #21)
  - Unifies Mendeley EEGIS bandpass frequency definitions across all scripts (Flaw #14)
"""

import os
import csv
import hashlib
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional

CODE_VERSION: str = "2.0.0-audit-remediated"

CHANNEL_NAMES: List[str] = [
    "AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
    "O2", "P8", "T8", "FC6", "F4", "F8", "AF4",
]

CLASS_MAP: Dict[int, str] = {
    0: "Rest",
    1: "Help (Ayuda)",
    2: "Bathroom (Baño)",
    3: "Pain (Dolor)",
    4: "Thanks (Gracias)",
    5: "Hungry (Hambre)",
    6: "No",
    7: "Thirsty (Sed)",
    8: "Yes (Sí)",
}

SAMPLING_RATE: int = 128
EPOCH_DURATION: float = 1.0
SAMPLES_PER_EPOCH: int = 128

BAND_NAMES: List[str] = ["raw", "delta", "theta", "alpha", "beta", "gamma"]

# Unified canonical bandpass cutoffs matching Mendeley EEGIS readme.txt
CANONICAL_BAND_CUTOFFS: Dict[str, Tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 40.0),
}

# Mutually exclusive non-overlapping 7 fine sub-bands covering 4-40 Hz
SUB7_CUTOFFS_NONOVERLAP: List[Tuple[float, float]] = [
    (4.0, 6.0),
    (6.0, 8.0),
    (8.0, 10.5),
    (10.5, 13.0),
    (13.0, 20.0),
    (20.0, 30.0),
    (30.0, 40.0),
]

# Legacy overlapping sub-bands (kept strictly for controlled ablation against non-overlapping)
SUB7_CUTOFFS_OVERLAP: List[Tuple[float, float]] = [
    (4.0, 6.5),
    (6.5, 9.5),
    (9.5, 13.0),
    (13.0, 20.0),
    (20.0, 30.0),
    (25.0, 35.0),
    (30.0, 40.0),
]


def _is_float_token(tok: str) -> bool:
    s = tok.strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _detect_csv_header(file_path: str, sep: str) -> Tuple[bool, List[str]]:
    """Inspects the first non-empty line to distinguish headered vs headerless numeric tables."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            tokens = next(csv.reader([stripped], delimiter=sep))
            tokens_clean = [t.strip() for t in tokens]
            non_empty = [t for t in tokens_clean if t != ""]
            if not non_empty:
                raise ValueError(f"Empty first data row in '{file_path}'.")
            # Leading empty token like ',AF3,F7,...' or non-numeric column label -> headered
            has_header = (tokens_clean[0] == "") or any(not _is_float_token(t) for t in non_empty)
            return has_header, tokens_clean
    raise ValueError(f"File '{file_path}' contains no rows.")


def _validate_confirmed_index_col(col: np.ndarray, file_path: str) -> None:
    """Confirms a leading 15th column is a valid integer index sequence rather than shifted electrode data."""
    n = len(col)
    if not np.all(np.isfinite(col)):
        raise ValueError(f"Non-finite values in leading column of '{file_path}'.")
    is_int_like = np.all(np.abs(col - np.round(col)) < 1e-6)
    is_monotonic_step = n <= 1 or (np.all(np.diff(col) == 1) and int(round(col[0])) in (0, 1))
    if not (is_int_like and is_monotonic_step):
        raise ValueError(
            f"Ambiguous 15-column data in '{file_path}': column 0 is not a confirmed 0..N-1 / 1..N sample index."
        )


def _parse_text_eeg(file_path: str, sep: str) -> np.ndarray:
    """Parses headered or headerless EEG CSV/TSV into canonical (14, T) float64 array without losing row 0."""
    has_header, raw_header = _detect_csv_header(file_path, sep)

    if has_header:
        df = pd.read_csv(file_path, sep=sep, header=0)
        cols = [str(c).strip() for c in df.columns]
        df.columns = cols

        named_ch = [c for c in cols if c in CHANNEL_NAMES]
        if named_ch:
            missing = [ch for ch in CHANNEL_NAMES if ch not in cols]
            extra_eeg = [c for c in cols if c not in CHANNEL_NAMES and not (c == "" or c.lower().startswith("unnamed") or c.lower() in ("index", "sample", "time", "t"))]
            if missing or len(named_ch) != 14:
                raise ValueError(
                    f"Channel header mismatch in '{file_path}': missing={missing}, found={named_ch}. Expected exact 14 Emotiv EPOC+ channels."
                )
            if extra_eeg:
                raise ValueError(
                    f"Unexpected non-index columns {extra_eeg} alongside 14 EEG channels in '{file_path}'."
                )
            sub_df = df[CHANNEL_NAMES]
            arr = _coerce_finite_numeric_df(sub_df, file_path)
            return arr.T

        # Headered without recognized CHANNEL_NAMES: require explicit 14 columns or confirmed unnamed index + 14
        arr = _coerce_finite_numeric_df(df, file_path)
        if arr.shape[1] == 15 and (cols[0] == "" or cols[0].lower().startswith("unnamed") or cols[0].lower() in ("index", "sample")):
            _validate_confirmed_index_col(arr[:, 0], file_path)
            return arr[:, 1:].T
        if arr.shape[1] == 14:
            return arr.T
        if arr.shape[0] == 14 and arr.shape[1] >= SAMPLES_PER_EPOCH:
            return arr
        raise ValueError(
            f"Unrecognized headered EEG table shape {arr.shape} with columns {cols} in '{file_path}'. Expected 14 named Emotiv channels."
        )

    # Strictly headerless CSV: header=None preserves sample row 0
    df = pd.read_csv(file_path, sep=sep, header=None)
    arr = _coerce_finite_numeric_df(df, file_path)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D EEG matrix in '{file_path}', got {arr.ndim}D.")
    if arr.shape[1] == 15:
        _validate_confirmed_index_col(arr[:, 0], file_path)
        return arr[:, 1:].T
    if arr.shape[1] == 14:
        return arr.T
    if arr.shape[0] == 14:
        return arr
    raise ValueError(
        f"Unrecognized headerless shape {arr.shape} in '{file_path}'. Expected 14 channels x >=128 samples (or transposed)."
    )


def _coerce_finite_numeric_df(df: pd.DataFrame, file_path: str) -> np.ndarray:
    if df.empty:
        raise ValueError(f"EEG file '{file_path}' has 0 data rows.")
    if all(pd.api.types.is_numeric_dtype(dt) for dt in df.dtypes):
        if df.isna().any().any():
            bad_count = int(df.isna().sum().sum())
            raise ValueError(f"EEG file '{file_path}' contains {bad_count} non-numeric or NaN values.")
        arr = df.to_numpy(dtype=np.float64)
    else:
        numeric_df = df.apply(pd.to_numeric, errors="coerce")
        if numeric_df.isna().any().any():
            bad_count = int(numeric_df.isna().sum().sum())
            raise ValueError(f"EEG file '{file_path}' contains {bad_count} non-numeric or NaN values.")
        arr = numeric_df.to_numpy(dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"EEG file '{file_path}' contains Inf/-Inf values.")
    return arr


def load_eeg_epoch_file(
    file_path: str,
    expected_fs: int = SAMPLING_RATE,
    min_samples: int = SAMPLES_PER_EPOCH,
    allow_longer: bool = False,
    sampling_rate_hz: Optional[float] = None,
    max_abs_uv: float = 20000.0,
) -> np.ndarray:
    """
    Strictly validates and loads a raw 14-channel EEG epoch file (.csv, .tsv, .txt, .npy).
    - Preserves row 0 on headerless files
    - Reorders columns to CHANNEL_NAMES on named-header CSVs
    - Strips column 0 only if confirmed as sample index
    - Rejects incomplete (<min_samples), wrong-channel (!=14), NaN/Inf, extreme-unit, or wrong-fs inputs
    Returns raw float64 array of shape (14, T) (sliced to min_samples unless allow_longer=True).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"EEG signal file not found: '{file_path}'")

    if sampling_rate_hz is not None and float(sampling_rate_hz) != float(expected_fs):
        raise ValueError(
            f"Unsupported sampling rate {sampling_rate_hz} Hz for '{file_path}'. Expected {expected_fs} Hz."
        )

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".csv", ".tsv", ".txt"):
        sep = "\t" if ext == ".tsv" else ","
        if ext == ".txt":
            # Detect whitespace vs comma on first line
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline()
            sep = "," if "," in first_line else r"\s+"
        sig = _parse_text_eeg(file_path, sep=sep)
    elif ext == ".npy":
        arr = np.load(file_path, allow_pickle=False)
        arr = np.squeeze(arr)
        if arr.ndim != 2:
            raise ValueError(f"Expected 2D array in '{file_path}', got shape {arr.shape}.")
        if arr.shape[0] == 14:
            sig = arr.astype(np.float64)
        elif arr.shape[1] == 14:
            sig = arr.T.astype(np.float64)
        else:
            raise ValueError(f"Invalid channel count in '{file_path}': shape {arr.shape} (expected 14 channels).")
    else:
        raise ValueError(f"Unsupported signal format '{ext}'. Expected .csv, .tsv, .txt, or .npy.")

    if sig.shape[0] != 14:
        raise ValueError(f"Expected exactly 14 EEG channels in '{file_path}', got {sig.shape[0]}.")
    if sig.shape[1] < min_samples:
        raise ValueError(
            f"Incomplete EEG epoch in '{file_path}': got {sig.shape[1]} samples, require >= {min_samples} samples ({min_samples / expected_fs:.2f}s @ {expected_fs} Hz). Silent edge-padding is disabled."
        )
    if not np.all(np.isfinite(sig)):
        raise ValueError(f"Non-finite (NaN/Inf) EEG samples detected in '{file_path}'.")

    # Unit plausibility guard against mis-scaled Volt vs microvolt or corrupted overflow
    centered_span = float(np.max(np.abs(sig - np.mean(sig, axis=1, keepdims=True))))
    if centered_span > max_abs_uv:
        raise ValueError(
            f"Implausible centered voltage amplitude ({centered_span:.1f} > {max_abs_uv:.1f} uV) in '{file_path}'."
        )

    if not allow_longer and sig.shape[1] > min_samples:
        sig = sig[:, :min_samples]

    return np.ascontiguousarray(sig, dtype=np.float64)


def preprocess_epoch(raw_signal: np.ndarray, expected_channels: int = 14, min_samples: int = SAMPLES_PER_EPOCH) -> np.ndarray:
    """
    Canonical DC baseline detrending used identically in training and offline inference.
    Accepts shape (14, T), validates shape and finiteness, subtracts per-channel mean, returns float32 (14, T).
    """
    arr = np.asarray(raw_signal, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != expected_channels or arr.shape[1] < min_samples:
        raise ValueError(f"Expected shape ({expected_channels}, >={min_samples}), got {arr.shape}.")
    if not np.all(np.isfinite(arr)):
        raise ValueError("Cannot preprocess signal containing NaN or Inf values.")
    detrended = arr - np.mean(arr, axis=1, keepdims=True)
    return detrended.astype(np.float32)


def sha256_file(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
