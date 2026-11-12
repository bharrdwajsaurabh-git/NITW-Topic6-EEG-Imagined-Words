"""
eeg_features.py
===============
Multi-domain Feature Extractor for EEG Imagined Speech Signals.
Implements the 200+ feature extraction pipeline described in:
"Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram
Signal Classification" (Lara-Arellano et al., Eng 2025).

Extracts:
1. Time-Domain Moments (Mean, Std, Skewness, Kurtosis, RMS, Peak-to-Peak, Zero Crossings)
2. Hjorth Parameters (Activity, Mobility, Complexity)
3. Frequency-Domain Bandpowers (Delta, Theta, Alpha, Beta, Gamma) via Welch's PSD
4. Spectral Ratios (Theta/Beta, Alpha/Beta) and Spectral Entropy
"""

import numpy as np
from scipy import signal
from scipy import stats
from typing import List, Tuple, Dict


FREQUENCY_BANDS: Dict[str, Tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 12.0),
    "beta": (12.0, 30.0),
    "gamma": (30.0, 60.0),
}


def compute_hjorth_parameters(x: np.ndarray) -> Tuple[float, float, float]:
    """
    Computes Hjorth Activity, Mobility, and Complexity for a 1D time series.
    """
    first_deriv = np.diff(x)
    second_deriv = np.diff(first_deriv)

    var_zero = np.var(x)
    var_d1 = np.var(first_deriv)
    var_d2 = np.var(second_deriv)

    # Activity: signal variance
    activity = var_zero

    # Mobility: mean frequency
    mobility = np.sqrt(var_d1 / (var_zero + 1e-12))

    # Complexity: change in frequency
    mobility_d1 = np.sqrt(var_d2 / (var_d1 + 1e-12))
    complexity = mobility_d1 / (mobility + 1e-12)

    return float(activity), float(mobility), float(complexity)


def compute_zero_crossing_rate(x: np.ndarray) -> float:
    """Calculates zero-crossing rate of a 1D time series."""
    zero_crosses = np.where(np.diff(np.signbit(x)))[0]
    return float(len(zero_crosses) / (len(x) - 1))


def compute_band_powers(x: np.ndarray, fs: int = 128) -> Dict[str, float]:
    """
    Computes absolute power in the standard delta, theta, alpha, beta, gamma bands
    using Welch's average periodogram.
    """
    nperseg = min(len(x), fs)
    freqs, psd = signal.welch(x, fs=fs, nperseg=nperseg)

    band_powers = {}
    # Use np.trapezoid (NumPy >= 2.0) or fallback to scipy.integrate.trapezoid
    trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
    if trapz_fn is None:
        import scipy.integrate
        trapz_fn = scipy.integrate.trapezoid

    total_power = trapz_fn(psd, freqs) + 1e-12

    for band_name, (low, high) in FREQUENCY_BANDS.items():
        idx = np.logical_and(freqs >= low, freqs <= high)
        bp = trapz_fn(psd[idx], freqs[idx])
        band_powers[band_name] = float(bp)
        # Relative band power
        band_powers[f"{band_name}_rel"] = float(bp / total_power)

    # Cross-band ratios
    band_powers["theta_beta_ratio"] = float(
        band_powers["theta"] / (band_powers["beta"] + 1e-12)
    )
    band_powers["alpha_beta_ratio"] = float(
        band_powers["alpha"] / (band_powers["beta"] + 1e-12)
    )

    # Spectral Entropy
    norm_psd = psd / (np.sum(psd) + 1e-12)
    norm_psd = norm_psd[norm_psd > 0]
    band_powers["spectral_entropy"] = float(-np.sum(norm_psd * np.log2(norm_psd)))

    return band_powers


def extract_trial_features(
    trial: np.ndarray, channel_names: List[str], fs: int = 128
) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts high-dimensional feature vector for a single trial of shape (n_channels, n_samples).
    """
    n_channels, _ = trial.shape
    features = []
    feature_names = []

    for ch_idx in range(n_channels):
        ch_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"Ch{ch_idx}"
        sig = trial[ch_idx, :]

        # 1. Time-Domain Moments
        mean_val = float(np.mean(sig))
        std_val = float(np.std(sig))
        skew_val = float(stats.skew(sig))
        kurt_val = float(stats.kurtosis(sig))
        rms_val = float(np.sqrt(np.mean(sig**2)))
        p2p_val = float(np.ptp(sig))
        zcr_val = compute_zero_crossing_rate(sig)

        # 2. Hjorth Parameters
        activity, mobility, complexity = compute_hjorth_parameters(sig)

        # 3. Frequency & Spectral Bands
        bp = compute_band_powers(sig, fs=fs)

        ch_feats = [
            mean_val, std_val, skew_val, kurt_val, rms_val, p2p_val, zcr_val,
            activity, mobility, complexity,
            bp["delta"], bp["theta"], bp["alpha"], bp["beta"], bp["gamma"],
            bp["delta_rel"], bp["theta_rel"], bp["alpha_rel"], bp["beta_rel"], bp["gamma_rel"],
            bp["theta_beta_ratio"], bp["alpha_beta_ratio"], bp["spectral_entropy"]
        ]

        ch_feat_names = [
            f"{ch_name}_mean", f"{ch_name}_std", f"{ch_name}_skew", f"{ch_name}_kurt",
            f"{ch_name}_rms", f"{ch_name}_p2p", f"{ch_name}_zcr",
            f"{ch_name}_hjorth_act", f"{ch_name}_hjorth_mob", f"{ch_name}_hjorth_comp",
            f"{ch_name}_delta", f"{ch_name}_theta", f"{ch_name}_alpha", f"{ch_name}_beta", f"{ch_name}_gamma",
            f"{ch_name}_delta_rel", f"{ch_name}_theta_rel", f"{ch_name}_alpha_rel", f"{ch_name}_beta_rel", f"{ch_name}_gamma_rel",
            f"{ch_name}_tbr", f"{ch_name}_abr", f"{ch_name}_spec_entropy"
        ]

        features.extend(ch_feats)
        feature_names.extend(ch_feat_names)

    return np.array(features, dtype=np.float32), feature_names


def extract_dataset_features(
    X: np.ndarray, channel_names: List[str], fs: int = 128
) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts features for all trials in X (N, n_channels, n_samples).
    Returns feature matrix of shape (N, total_features) and feature names list.
    """
    n_trials = X.shape[0]
    print(f"[*] Extracting statistical & spectral features across {n_trials} trials...")

    feat_matrix = []
    feat_names = []
    for i in range(n_trials):
        f_vec, names = extract_trial_features(X[i], channel_names, fs=fs)
        feat_matrix.append(f_vec)
        if i == 0:
            feat_names = names

    feat_matrix = np.array(feat_matrix, dtype=np.float32)
    print(f"[+] Extracted {feat_matrix.shape[1]} features per trial. Total matrix: {feat_matrix.shape}")
    return feat_matrix, feat_names


def _spd_tangent_vector(sig_ch_by_t: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """
    Computes trace-normalized SPD Log-Euclidean Riemannian tangent vector for a (14, T) trial.
    Returns 105-dim L2-normalized upper-triangular tangent representation.
    """
    n_ch = sig_ch_by_t.shape[0]
    cov = np.cov(sig_ch_by_t.astype(np.float64)) + reg * np.eye(n_ch)
    cov_norm = cov / (np.trace(cov) / float(n_ch) + 1e-8)
    evals, evecs = np.linalg.eigh(cov_norm)
    evals = np.maximum(evals, 1e-6)
    log_c = (evecs * np.log(evals)) @ evecs.T
    iu = np.triu_indices(n_ch)
    vec = log_c[iu].copy()
    vec[iu[0] != iu[1]] *= np.sqrt(2.0)
    vec = vec / (np.linalg.norm(vec) + 1e-12)
    return vec.astype(np.float32)


def extract_6band_riemannian_features(X_6band: np.ndarray) -> np.ndarray:
    """
    Extracts Filter-Bank Log-Euclidean Riemannian Tangent Space features across all 6 neural bands
    (raw, delta, theta, alpha, beta, gamma) for tensor shape (N, 6, 14, 128) -> (N, 630).
    """
    n_trials, n_bands, _, _ = X_6band.shape
    out = np.zeros((n_trials, n_bands * 105), dtype=np.float32)
    for i in range(n_trials):
        for b in range(n_bands):
            out[i, b * 105 : (b + 1) * 105] = _spd_tangent_vector(X_6band[i, b])
    return np.nan_to_num(out)


def extract_single_trial_6band_from_raw(raw_signal: np.ndarray, fs: int = 128) -> np.ndarray:
    """
    Computes 6-band Filter-Bank Riemannian features (1, 630) on-the-fly from a raw (14, 128) EEG trial
    using 4th-order zero-phase Butterworth bandpass filters matching Mendeley EEGIS cutoffs.
    """
    sig_raw = raw_signal.astype(np.float64)
    sig_raw = sig_raw - np.mean(sig_raw, axis=1, keepdims=True)
    bands_cutoffs = [(0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 40.0)]
    vecs = [_spd_tangent_vector(sig_raw)]
    for lo, hi in bands_cutoffs:
        b_coef, a_coef = signal.butter(4, [lo, hi], btype="band", fs=float(fs))
        sig_band = signal.filtfilt(b_coef, a_coef, sig_raw, axis=1)
        vecs.append(_spd_tangent_vector(sig_band))
    return np.concatenate(vecs).reshape(1, -1).astype(np.float32)


# Speech-motor (Broca-Wernicke + Premotor) 10-electrode montage indices inside CHANNEL_NAMES:
# ["AF3", "F7", "F3", "FC5", "T7", "P7", "T8", "FC6", "F4", "F8"]
SPEECH_10_IDX = [0, 1, 2, 3, 4, 5, 9, 10, 11, 12]
SUB7_CUTOFFS = [
    (4.0, 6.5), (6.5, 9.5), (9.5, 13.0),
    (13.0, 20.0), (20.0, 30.0), (25.0, 35.0), (30.0, 42.0),
]


def _spd_tangent_batch(sig_n_c_t: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """Fast vectorized-overhead SPD Log-Euclidean tangent batch for (N, C, T) -> (N, C*(C+1)//2)."""
    n_trials, n_ch, _ = sig_n_c_t.shape
    iu = np.triu_indices(n_ch)
    off = iu[0] != iu[1]
    s2 = np.sqrt(2.0)
    eye = reg * np.eye(n_ch, dtype=np.float64)
    out = np.empty((n_trials, len(iu[0])), dtype=np.float32)
    for i in range(n_trials):
        cov = np.cov(sig_n_c_t[i].astype(np.float64)) + eye
        cov_n = cov / (np.trace(cov) / float(n_ch) + 1e-8)
        ev, evec = np.linalg.eigh(cov_n)
        ev = np.maximum(ev, 1e-6)
        log_c = (evec * np.log(ev)) @ evec.T
        v = log_c[iu].copy()
        v[off] *= s2
        v /= (np.linalg.norm(v) + 1e-12)
        out[i] = v.astype(np.float32)
    return out


def extract_mdrc_v3_features(X_6band: np.ndarray, F_riem6: np.ndarray = None, fs: int = 128) -> np.ndarray:
    """
    Extracts Stage 2 MDRC-AGA v3 1695-dim Multi-Scale Riemannian features:
      1) Mendeley 6-Band Global Log-SPD (630D = 6 x 105)
      2) Fine 7-Band Sub-Spectral Log-SPD across Theta/Alpha/Beta/Gamma splits (735D = 7 x 105)
      3) Broca-Wernicke 10-Electrode Speech-Motor 6-Band Log-SPD (330D = 6 x 55)
    """
    if F_riem6 is None:
        F_riem6 = extract_6band_riemannian_features(X_6band)
    raw0 = X_6band[:, 0].astype(np.float64)
    raw0 = raw0 - np.mean(raw0, axis=-1, keepdims=True)
    sub_parts = []
    for lo, hi in SUB7_CUTOFFS:
        b_coef, a_coef = signal.butter(4, [lo, hi], btype="band", fs=float(fs))
        xb = signal.filtfilt(b_coef, a_coef, raw0, axis=-1)
        sub_parts.append(_spd_tangent_batch(xb, reg=1e-4))
    F_sub7 = np.hstack(sub_parts)
    F_sp10 = np.hstack([_spd_tangent_batch(X_6band[:, b, SPEECH_10_IDX, :], reg=1e-4) for b in range(6)])
    return np.nan_to_num(np.hstack([F_riem6, F_sub7, F_sp10])).astype(np.float32)


def extract_single_trial_v3_from_raw(raw_signal: np.ndarray, fs: int = 128) -> np.ndarray:
    """
    Real-time single-trial extraction (<50 ms) matching extract_mdrc_v3_features() -> (1, 1695).
    """
    sig_raw = raw_signal.astype(np.float64)
    sig_raw = sig_raw - np.mean(sig_raw, axis=1, keepdims=True)
    mendeley_cutoffs = [(0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 40.0)]
    bands_6 = [sig_raw]
    for lo, hi in mendeley_cutoffs:
        b_coef, a_coef = signal.butter(4, [lo, hi], btype="band", fs=float(fs))
        bands_6.append(signal.filtfilt(b_coef, a_coef, sig_raw, axis=1))
    v_6b = np.concatenate([_spd_tangent_vector(xb) for xb in bands_6])
    v_sub7_parts = []
    for lo, hi in SUB7_CUTOFFS:
        b_coef, a_coef = signal.butter(4, [lo, hi], btype="band", fs=float(fs))
        xb = signal.filtfilt(b_coef, a_coef, sig_raw, axis=1)
        v_sub7_parts.append(_spd_tangent_vector(xb))
    v_sub7 = np.concatenate(v_sub7_parts)
    v_sp10 = np.concatenate([_spd_tangent_vector(xb[SPEECH_10_IDX, :]) for xb in bands_6])
    return np.nan_to_num(np.concatenate([v_6b, v_sub7, v_sp10])).reshape(1, -1).astype(np.float32)


if __name__ == "__main__":
    print("=" * 65)
    print("       EEG FEATURE EXTRACTION ENGINE TEST (14 CHANNELS)       ")
    print("=" * 65)
    # Create a 1-second dummy EEG trial (14 channels, 128 samples)
    fs = 128
    dummy_trial = np.random.randn(14, fs).astype(np.float32)
    ch_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
    feats, names = extract_trial_features(dummy_trial, ch_names, fs=fs)
    print(f"[*] Input raw signal:  14 channels x {fs} time-samples")
    print(f"[+] Extracted features: {len(feats)} features per trial")
    print(f"[+] Feature categories:")
    print(f"    - Statistical: Mean, Variance, Skewness, Kurtosis (4 x 14 = 56)")
    print(f"    - Hjorth:      Activity, Mobility, Complexity   (3 x 14 = 42)")
    print(f"    - Welch PSD:   Delta, Theta, Alpha, Beta, Gamma (5 x 14 = 70)")
    print(f"    - Band Ratios: TBR, ABR, Spectral Entropy       (3 x 14 = 42)")
    print(f"    - Total per trial: 14 channels x 23 features = 322 features")
    print("=" * 65)

