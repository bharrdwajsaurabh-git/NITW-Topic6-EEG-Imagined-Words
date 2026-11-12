"""
eeg_features.py
===============
Unified Multi-Domain, Filter-Bank SPD, True Fold-Fitted Riemannian Tangent Space,
and Filter-Bank CSP (FBCSP) Feature Extraction Engine.

Remediated audit items:
  - Uses unified `CANONICAL_BAND_CUTOFFS` & `preprocess_epoch` from `eeg_preprocessing.py`
    (fixes alpha/beta/gamma discrepancy and train-vs-inference parity; Flaws #14, #19)
  - Separates identity-centered Log-Euclidean SPD (`extract_log_euclidean_*`) from
    TRUE training-fold Riemannian Tangent Space (`RiemannianTangentSpace` centered at
    fold-only reference C_ref = expm(mean(logm(C_train))), Flaw #5)
  - Supports mutually exclusive `non_overlapping` 7 sub-bands by default alongside
    `overlapping` 7 sub-bands for controlled ablation (Flaw #15)
  - Supports electrode montage masks (`speech10`, `all14`, `left7`, `occipital4`) to test
    rather than assume "Broca-Wernicke" scalp-localization claims (Flaw #17)
  - Includes continuous-block filter-before-slice & Filter-Bank CSP (`FilterBankCSP`) +
    Minimum Distance to Mean (`MDMClassifier`) helpers (Flaws #16, #26)
"""

import numpy as np
from scipy import signal, stats
from typing import List, Tuple, Dict, Optional

from eeg_preprocessing import (
    CHANNEL_NAMES,
    SAMPLING_RATE,
    SAMPLES_PER_EPOCH,
    CANONICAL_BAND_CUTOFFS,
    SUB7_CUTOFFS_NONOVERLAP,
    SUB7_CUTOFFS_OVERLAP,
    preprocess_epoch,
)

# Canonical 5-band definitions aligned identically with Mendeley EEGIS (Flaw #14)
FREQUENCY_BANDS: Dict[str, Tuple[float, float]] = CANONICAL_BAND_CUTOFFS

# Montage index definitions inside canonical 14-channel Emotiv EPOC+ layout:
# ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
SPEECH_10_IDX: List[int] = [0, 1, 2, 3, 4, 5, 9, 10, 11, 12]
LEFT_7_IDX: List[int] = [0, 1, 2, 3, 4, 5, 6]
RIGHT_7_IDX: List[int] = [7, 8, 9, 10, 11, 12, 13]
OCCIPITAL_PARIETAL_4_IDX: List[int] = [5, 6, 7, 8]
ALL_14_IDX: List[int] = list(range(14))

MONTAGE_MASKS: Dict[str, List[int]] = {
    "all14": ALL_14_IDX,
    "speech10": SPEECH_10_IDX,
    "left7": LEFT_7_IDX,
    "occipital4": OCCIPITAL_PARIETAL_4_IDX,
}

# Default to non-overlapping fine sub-bands; keep overlapping alias for controlled ablation
SUB7_CUTOFFS: List[Tuple[float, float]] = SUB7_CUTOFFS_NONOVERLAP


# ---------------------------------------------------------------------------
# 1. Baseline Paper Statistical + Hjorth + Welch PSD Features (322-D)
# ---------------------------------------------------------------------------

def compute_hjorth_parameters(x: np.ndarray) -> Tuple[float, float, float]:
    """Computes Hjorth Activity, Mobility, and Complexity for a 1D signal."""
    first_deriv = np.diff(x)
    second_deriv = np.diff(first_deriv)

    var_zero = float(np.var(x))
    var_d1 = float(np.var(first_deriv))
    var_d2 = float(np.var(second_deriv))

    activity = var_zero
    mobility = float(np.sqrt(var_d1 / (var_zero + 1e-12)))
    mobility_d1 = float(np.sqrt(var_d2 / (var_d1 + 1e-12)))
    complexity = float(mobility_d1 / (mobility + 1e-12))
    return activity, mobility, complexity


def compute_zero_crossing_rate(x: np.ndarray) -> float:
    """Calculates zero-crossing rate of a 1D time series."""
    zero_crosses = np.where(np.diff(np.signbit(x)))[0]
    return float(len(zero_crosses) / max(len(x) - 1, 1))


def compute_band_powers(x: np.ndarray, fs: int = SAMPLING_RATE) -> Dict[str, float]:
    """
    Computes absolute and relative Welch PSD band powers using CANONICAL_BAND_CUTOFFS
    (alpha 8-13 Hz, beta 13-30 Hz, gamma 30-40 Hz).
    """
    nperseg = min(len(x), fs)
    freqs, psd = signal.welch(x, fs=fs, nperseg=nperseg)

    trapz_fn = getattr(np, "trapezoid", None)
    if trapz_fn is None:
        import scipy.integrate
        trapz_fn = scipy.integrate.trapezoid

    band_powers: Dict[str, float] = {}
    total_power = float(trapz_fn(psd, freqs)) + 1e-12

    for band_name, (low, high) in FREQUENCY_BANDS.items():
        idx = np.logical_and(freqs >= low, freqs <= high)
        bp = float(trapz_fn(psd[idx], freqs[idx])) if np.any(idx) else 0.0
        band_powers[band_name] = bp
        band_powers[f"{band_name}_rel"] = float(bp / total_power)

    band_powers["theta_beta_ratio"] = float(band_powers["theta"] / (band_powers["beta"] + 1e-12))
    band_powers["alpha_beta_ratio"] = float(band_powers["alpha"] / (band_powers["beta"] + 1e-12))

    norm_psd = psd / (np.sum(psd) + 1e-12)
    norm_psd = norm_psd[norm_psd > 0]
    band_powers["spectral_entropy"] = float(-np.sum(norm_psd * np.log2(norm_psd))) if len(norm_psd) else 0.0
    return band_powers


def extract_trial_features(
    trial: np.ndarray,
    channel_names: List[str] = CHANNEL_NAMES,
    fs: int = SAMPLING_RATE,
    detrend: bool = True,
) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts 322 statistical/Hjorth/Welch features for a single trial (14, T).
    Applies canonical `preprocess_epoch` when `detrend=True` so training and offline inference match.
    """
    arr = preprocess_epoch(trial, expected_channels=trial.shape[0], min_samples=min(trial.shape[1], SAMPLES_PER_EPOCH)) if detrend else np.asarray(trial, dtype=np.float32)
    n_channels = arr.shape[0]
    features: List[float] = []
    feature_names: List[str] = []

    for ch_idx in range(n_channels):
        ch_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"Ch{ch_idx}"
        sig = arr[ch_idx, :].astype(np.float64)

        mean_val = float(np.mean(sig))
        std_val = float(np.std(sig))
        skew_val = float(stats.skew(sig)) if std_val > 1e-12 else 0.0
        kurt_val = float(stats.kurtosis(sig)) if std_val > 1e-12 else 0.0
        rms_val = float(np.sqrt(np.mean(sig ** 2)))
        p2p_val = float(np.ptp(sig))
        zcr_val = compute_zero_crossing_rate(sig)
        activity, mobility, complexity = compute_hjorth_parameters(sig)
        bp = compute_band_powers(sig, fs=fs)

        ch_feats = [
            mean_val, std_val, skew_val, kurt_val, rms_val, p2p_val, zcr_val,
            activity, mobility, complexity,
            bp["delta"], bp["theta"], bp["alpha"], bp["beta"], bp["gamma"],
            bp["delta_rel"], bp["theta_rel"], bp["alpha_rel"], bp["beta_rel"], bp["gamma_rel"],
            bp["theta_beta_ratio"], bp["alpha_beta_ratio"], bp["spectral_entropy"],
        ]
        ch_feat_names = [
            f"{ch_name}_mean", f"{ch_name}_std", f"{ch_name}_skew", f"{ch_name}_kurt",
            f"{ch_name}_rms", f"{ch_name}_p2p", f"{ch_name}_zcr",
            f"{ch_name}_hjorth_act", f"{ch_name}_hjorth_mob", f"{ch_name}_hjorth_comp",
            f"{ch_name}_delta", f"{ch_name}_theta", f"{ch_name}_alpha", f"{ch_name}_beta", f"{ch_name}_gamma",
            f"{ch_name}_delta_rel", f"{ch_name}_theta_rel", f"{ch_name}_alpha_rel", f"{ch_name}_beta_rel", f"{ch_name}_gamma_rel",
            f"{ch_name}_tbr", f"{ch_name}_abr", f"{ch_name}_spec_entropy",
        ]
        features.extend(ch_feats)
        feature_names.extend(ch_feat_names)

    return np.nan_to_num(np.array(features, dtype=np.float32)), feature_names


def extract_dataset_features(
    X: np.ndarray, channel_names: List[str] = CHANNEL_NAMES, fs: int = SAMPLING_RATE, detrend: bool = True
) -> Tuple[np.ndarray, List[str]]:
    """Extracts 322 baseline paper features across dataset (N, C, T)."""
    n_trials = X.shape[0]
    feat_matrix = []
    feat_names: List[str] = []
    for i in range(n_trials):
        f_vec, names = extract_trial_features(X[i], channel_names=channel_names, fs=fs, detrend=detrend)
        feat_matrix.append(f_vec)
        if i == 0:
            feat_names = names
    return np.array(feat_matrix, dtype=np.float32), feat_names


# ---------------------------------------------------------------------------
# 2. SPD Covariance, Log-Euclidean (Identity Ref) & True Tangent Space (Fold C_ref)
# ---------------------------------------------------------------------------

def compute_spd_covariances(sig_n_c_t: np.ndarray, reg: float = 1e-4, trace_norm: bool = True) -> np.ndarray:
    """
    Computes regularized Symmetric Positive Definite (SPD) spatial covariance matrices
    of shape (N, C, C) from signals (N, C, T).
    """
    arr = np.asarray(sig_n_c_t, dtype=np.float64)
    n_trials, n_ch, n_t = arr.shape
    centered = arr - np.mean(arr, axis=2, keepdims=True)
    covs = np.einsum("nct,ndt->ncd", centered, centered) / float(max(n_t - 1, 1))
    covs += reg * np.eye(n_ch, dtype=np.float64)[None, :, :]
    if trace_norm:
        traces = np.trace(covs, axis1=1, axis2=2) / float(n_ch)
        covs = covs / (traces[:, None, None] + 1e-12)
    return covs


def _sym_matrix_power(mat: np.ndarray, power: float, min_eig: float = 1e-7) -> np.ndarray:
    ev, evec = np.linalg.eigh(mat)
    ev = np.maximum(ev, min_eig)
    return (evec * (ev ** power)) @ evec.T


def _sym_logm(mat: np.ndarray, min_eig: float = 1e-7) -> np.ndarray:
    ev, evec = np.linalg.eigh(mat)
    ev = np.maximum(ev, min_eig)
    return (evec * np.log(ev)) @ evec.T


def _sym_expm(mat: np.ndarray) -> np.ndarray:
    ev, evec = np.linalg.eigh(mat)
    ev = np.clip(ev, -30.0, 30.0)
    return (evec * np.exp(ev)) @ evec.T


def _sym_logm_batch(mats: np.ndarray, min_eig: float = 1e-7) -> np.ndarray:
    """Vectorized batch matrix logarithm for symmetric (N, C, C) matrices."""
    ev, evec = np.linalg.eigh(mats)
    ev = np.maximum(ev, min_eig)
    return (evec * np.log(ev)[:, None, :]) @ np.swapaxes(evec, -1, -2)


def _vec_upper_tri(mats: np.ndarray, l2_norm: bool = True) -> np.ndarray:
    n_trials, n_ch, _ = mats.shape
    iu = np.triu_indices(n_ch)
    off = iu[0] != iu[1]
    vecs = mats[:, iu[0], iu[1]].astype(np.float64)
    vecs[:, off] *= np.sqrt(2.0)
    if l2_norm:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / (norms + 1e-12)
    return vecs.astype(np.float32)


class RiemannianTangentSpace:
    """
    True Training-Fold Riemannian Tangent Space Projector (Barachant et al., 2012/2013):
      - `fit(covs_train)`: computes the SPD Log-Euclidean mean reference matrix
        C_ref = expm(mean(logm(C_train))) strictly on training data (zero test leakage).
      - `transform(covs)`: projects each SPD matrix C into T_{C_ref}(M) via
        logm(C_ref^{-1/2} @ C @ C_ref^{-1/2}) and upper-triangular sqrt(2) vectorization.
    """

    def __init__(self, reg: float = 1e-4, l2_norm: bool = True):
        self.reg = float(reg)
        self.l2_norm = bool(l2_norm)
        self.c_ref_: Optional[np.ndarray] = None
        self.c_ref_inv_sqrt_: Optional[np.ndarray] = None

    def fit(self, covs_train: np.ndarray) -> "RiemannianTangentSpace":
        logs = _sym_logm_batch(covs_train)
        log_mean = np.mean(logs, axis=0)
        self.c_ref_ = _sym_expm(log_mean)
        self.c_ref_inv_sqrt_ = _sym_matrix_power(self.c_ref_, -0.5)
        return self

    def transform(self, covs: np.ndarray) -> np.ndarray:
        if self.c_ref_inv_sqrt_ is None:
            raise RuntimeError("RiemannianTangentSpace must be fitted on training covariances before transform().")
        w = self.c_ref_inv_sqrt_
        whitened = w[None, :, :] @ covs @ w[None, :, :]
        whitened = 0.5 * (whitened + np.swapaxes(whitened, -1, -2))
        logs = _sym_logm_batch(whitened)
        return _vec_upper_tri(logs, l2_norm=self.l2_norm)

    def fit_transform(self, covs_train: np.ndarray) -> np.ndarray:
        return self.fit(covs_train).transform(covs_train)


class MDMClassifier:
    """
    Minimum Distance to Mean (MDM) SPD Riemannian classifier over Log-Euclidean distances
    (fits per-class Log-Euclidean barycenters on training covariances only).
    """

    def __init__(self, reg: float = 1e-4):
        self.reg = float(reg)
        self.classes_: Optional[np.ndarray] = None
        self.log_means_: Optional[np.ndarray] = None

    def fit(self, covs_train: np.ndarray, y_train: np.ndarray) -> "MDMClassifier":
        self.classes_ = np.unique(y_train)
        log_covs = _sym_logm_batch(covs_train)
        self.log_means_ = np.array(
            [np.mean(log_covs[y_train == c], axis=0) for c in self.classes_], dtype=np.float64
        )
        return self

    def decision_function(self, covs: np.ndarray) -> np.ndarray:
        if self.log_means_ is None:
            raise RuntimeError("MDMClassifier must be fitted first.")
        log_covs = _sym_logm_batch(covs)
        diff = log_covs[:, None, :, :] - self.log_means_[None, :, :, :]
        dists = np.linalg.norm(diff, axis=(2, 3))
        return -dists

    def predict(self, covs: np.ndarray) -> np.ndarray:
        scores = self.decision_function(covs)
        return self.classes_[np.argmax(scores, axis=1)]


def bandpass_filter_bank(
    signals: np.ndarray, cutoffs: List[Tuple[float, float]], fs: int = SAMPLING_RATE, order: int = 4
) -> List[np.ndarray]:
    """Applies zero-phase Butterworth bandpass filters across a list of (low, high) Hz tuples."""
    arr = np.asarray(signals, dtype=np.float64)
    arr = arr - np.mean(arr, axis=-1, keepdims=True)
    out = []
    for lo, hi in cutoffs:
        b_coef, a_coef = signal.butter(order, [lo, hi], btype="band", fs=float(fs))
        padlen = min(3 * (max(len(a_coef), len(b_coef)) - 1), arr.shape[-1] - 1)
        out.append(signal.filtfilt(b_coef, a_coef, arr, axis=-1, padlen=padlen))
    return out


class MultiScaleTangentExtractor:
    """
    Configurable multi-scale SPD covariance & tangent-space feature extractor supporting:
      - `geometry='tangent_fold'`: True training-fold C_ref Riemannian tangent space
      - `geometry='log_euclid_identity'`: Identity-centered log-covariance features (legacy fast approximation)
      - `subband_mode='non_overlapping'` vs `'overlapping'` (Flaw #15)
      - `local_montage`: `'speech10'`, `'all14'`, `'left7'`, `'occipital4'` (Flaw #17)
    `block_dims_` stores the exact dimensionality of the 3 blocks: (base_6band, fine_7band, montage_6band).
    """

    def __init__(
        self,
        geometry: str = "tangent_fold",
        subband_mode: str = "non_overlapping",
        local_montage: str = "speech10",
        fs: int = SAMPLING_RATE,
        reg: float = 1e-4,
        l2_norm: bool = True,
    ):
        if geometry not in ("tangent_fold", "log_euclid_identity"):
            raise ValueError(f"Invalid geometry '{geometry}'.")
        if subband_mode not in ("non_overlapping", "overlapping"):
            raise ValueError(f"Invalid subband_mode '{subband_mode}'.")
        if local_montage not in MONTAGE_MASKS:
            raise ValueError(f"Unknown local_montage '{local_montage}'.")

        self.geometry = geometry
        self.subband_mode = subband_mode
        self.local_montage = local_montage
        self.montage_idx = MONTAGE_MASKS[local_montage]
        self.fs = int(fs)
        self.reg = float(reg)
        self.l2_norm = bool(l2_norm)
        self.subband_cutoffs = (
            SUB7_CUTOFFS_NONOVERLAP if subband_mode == "non_overlapping" else SUB7_CUTOFFS_OVERLAP
        )
        self.projectors_: Optional[List[Optional[RiemannianTangentSpace]]] = None
        self.block_dims_: Tuple[int, int, int] = (0, 0, 0)

    def _prepare_band_tensors(self, X_raw: np.ndarray, X_6b: Optional[np.ndarray] = None) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray]]:
        raw0 = np.asarray(X_raw, dtype=np.float64)
        raw0 = raw0 - np.mean(raw0, axis=-1, keepdims=True)
        if X_6b is not None:
            b6_list = [X_6b[:, b].astype(np.float64) for b in range(X_6b.shape[1])]
        else:
            canonical_list = [CANONICAL_BAND_CUTOFFS[k] for k in ("delta", "theta", "alpha", "beta", "gamma")]
            b6_list = [raw0] + bandpass_filter_bank(raw0, canonical_list, fs=self.fs)

        sub7_list = bandpass_filter_bank(raw0, self.subband_cutoffs, fs=self.fs)
        local_list = [xb[:, self.montage_idx, :] for xb in b6_list]
        return b6_list, sub7_list, local_list

    def precompute_view_covariances(
        self, X_raw: np.ndarray, X_6b: Optional[np.ndarray] = None
    ) -> Tuple[List[np.ndarray], Tuple[int, int, int]]:
        """
        Computes per-trial regularized trace-normed SPD covariance tensors `(N, C_v, C_v)`
        for all multi-scale views independently per epoch (zero cross-trial leakage).
        """
        b6_list, sub7_list, local_list = self._prepare_band_tensors(X_raw, X_6b)
        all_views = b6_list + sub7_list + local_list
        n_b6 = len(b6_list) * (b6_list[0].shape[1] * (b6_list[0].shape[1] + 1) // 2)
        n_s7 = len(sub7_list) * (sub7_list[0].shape[1] * (sub7_list[0].shape[1] + 1) // 2)
        n_loc = len(local_list) * (len(self.montage_idx) * (len(self.montage_idx) + 1) // 2)
        bdims = (n_b6, n_s7, n_loc)
        covs_list = [compute_spd_covariances(v, reg=self.reg, trace_norm=True) for v in all_views]
        return covs_list, bdims

    def fit_from_covs(
        self, covs_list_train: List[np.ndarray], block_dims: Tuple[int, int, int]
    ) -> "MultiScaleTangentExtractor":
        self.block_dims_ = block_dims
        if self.geometry == "tangent_fold":
            self.projectors_ = [
                RiemannianTangentSpace(reg=self.reg, l2_norm=self.l2_norm).fit(covs)
                for covs in covs_list_train
            ]
        else:
            self.projectors_ = [None] * len(covs_list_train)
        return self

    def transform_from_covs(self, covs_list: List[np.ndarray]) -> np.ndarray:
        if self.projectors_ is None:
            raise RuntimeError("MultiScaleTangentExtractor must be fitted before transform_from_covs().")
        feats = []
        for covs, proj in zip(covs_list, self.projectors_):
            if self.geometry == "tangent_fold" and proj is not None:
                feats.append(proj.transform(covs))
            else:
                logs = _sym_logm_batch(covs)
                feats.append(_vec_upper_tri(logs, l2_norm=self.l2_norm))
        return np.nan_to_num(np.hstack(feats)).astype(np.float32)

    def fit(self, X_raw_train: np.ndarray, X_6b_train: Optional[np.ndarray] = None) -> "MultiScaleTangentExtractor":
        covs_list, bdims = self.precompute_view_covariances(X_raw_train, X_6b_train)
        return self.fit_from_covs(covs_list, bdims)

    def transform(self, X_raw: np.ndarray, X_6b: Optional[np.ndarray] = None) -> np.ndarray:
        covs_list, _ = self.precompute_view_covariances(X_raw, X_6b)
        return self.transform_from_covs(covs_list)

    def fit_transform(self, X_raw_train: np.ndarray, X_6b_train: Optional[np.ndarray] = None) -> np.ndarray:
        covs_list, bdims = self.precompute_view_covariances(X_raw_train, X_6b_train)
        return self.fit_from_covs(covs_list, bdims).transform_from_covs(covs_list)


# ---------------------------------------------------------------------------
# 3. Identity-Centered Log-Euclidean Helpers & Backward-Compatible Wrappers
# ---------------------------------------------------------------------------

def extract_log_euclidean_spd_vector(sig_ch_by_t: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """
    Computes trace-normalized identity-centered Log-Euclidean SPD representation
    vec(logm(C_norm)) for a single (C, T) epoch.
    Note: Reference point is identity I, NOT training-fold Fréchet mean C_ref.
    """
    covs = compute_spd_covariances(sig_ch_by_t[None, :, :], reg=reg, trace_norm=True)
    log_c = _sym_logm(covs[0])[None, :, :]
    return _vec_upper_tri(log_c, l2_norm=True)[0]


def _spd_tangent_vector(sig_ch_by_t: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """Backward-compatible alias for `extract_log_euclidean_spd_vector`."""
    return extract_log_euclidean_spd_vector(sig_ch_by_t, reg=reg)


def _spd_tangent_batch(sig_n_c_t: np.ndarray, reg: float = 1e-4) -> np.ndarray:
    """Batch identity-centered Log-Euclidean SPD representation for (N, C, T)."""
    covs = compute_spd_covariances(sig_n_c_t, reg=reg, trace_norm=True)
    logs = _sym_logm_batch(covs)
    return _vec_upper_tri(logs, l2_norm=True)


def extract_6band_riemannian_features(X_6band: np.ndarray) -> np.ndarray:
    """
    Extracts identity-centered 6-band Filter-Bank Log-Euclidean SPD vectors -> (N, 630).
    Use `MultiScaleTangentExtractor(geometry='tangent_fold')` for fold-fitted tangent space.
    """
    parts = [_spd_tangent_batch(X_6band[:, b], reg=1e-4) for b in range(X_6band.shape[1])]
    return np.nan_to_num(np.hstack(parts)).astype(np.float32)


def extract_single_trial_6band_from_raw(raw_signal: np.ndarray, fs: int = SAMPLING_RATE) -> np.ndarray:
    """Canonical single-trial 6-band Log-Euclidean SPD vector (1, 630)."""
    sig_proc = preprocess_epoch(raw_signal, expected_channels=raw_signal.shape[0], min_samples=SAMPLES_PER_EPOCH).astype(np.float64)
    canonical_list = [CANONICAL_BAND_CUTOFFS[k] for k in ("delta", "theta", "alpha", "beta", "gamma")]
    bands = [sig_proc] + [b[0] for b in bandpass_filter_bank(sig_proc[None, :, :], canonical_list, fs=fs)]
    return np.concatenate([_spd_tangent_vector(xb) for xb in bands]).reshape(1, -1).astype(np.float32)


def extract_mdrc_v3_features(
    X_6band: np.ndarray,
    F_riem6: Optional[np.ndarray] = None,
    fs: int = SAMPLING_RATE,
    subband_mode: str = "non_overlapping",
    local_montage: str = "speech10",
) -> np.ndarray:
    """
    Extracts identity-centered 1,695-dim Multi-Scale Log-Euclidean SPD features:
      Block 0: Canonical 6-band 14-ch (630D)
      Block 1: Fine 7-band 14-ch (`non_overlapping` default or `overlapping`) (735D)
      Block 2: Local montage 6-band (330D for 10 channels; 630D for all14; 168D for left7; 60D for occ4)
    """
    if F_riem6 is None:
        F_riem6 = extract_6band_riemannian_features(X_6band)
    cutoffs = SUB7_CUTOFFS_NONOVERLAP if subband_mode == "non_overlapping" else SUB7_CUTOFFS_OVERLAP
    montage_idx = MONTAGE_MASKS[local_montage]
    raw0 = X_6band[:, 0].astype(np.float64)
    sub_parts = [_spd_tangent_batch(xb, reg=1e-4) for xb in bandpass_filter_bank(raw0, cutoffs, fs=fs)]
    F_sub7 = np.hstack(sub_parts)
    F_loc = np.hstack([_spd_tangent_batch(X_6band[:, b, montage_idx, :], reg=1e-4) for b in range(X_6band.shape[1])])
    return np.nan_to_num(np.hstack([F_riem6, F_sub7, F_loc])).astype(np.float32)


def extract_single_trial_v3_from_raw(
    raw_signal: np.ndarray,
    fs: int = SAMPLING_RATE,
    subband_mode: str = "non_overlapping",
    local_montage: str = "speech10",
) -> np.ndarray:
    """Canonical single-trial multi-scale Log-Euclidean SPD extraction matching `extract_mdrc_v3_features`."""
    sig_proc = preprocess_epoch(raw_signal, expected_channels=raw_signal.shape[0], min_samples=SAMPLES_PER_EPOCH).astype(np.float64)
    canonical_list = [CANONICAL_BAND_CUTOFFS[k] for k in ("delta", "theta", "alpha", "beta", "gamma")]
    bands_6 = [sig_proc] + [b[0] for b in bandpass_filter_bank(sig_proc[None, :, :], canonical_list, fs=fs)]
    cutoffs = SUB7_CUTOFFS_NONOVERLAP if subband_mode == "non_overlapping" else SUB7_CUTOFFS_OVERLAP
    sub_7 = [b[0] for b in bandpass_filter_bank(sig_proc[None, :, :], cutoffs, fs=fs)]
    montage_idx = MONTAGE_MASKS[local_montage]
    v_6b = np.concatenate([_spd_tangent_vector(xb) for xb in bands_6])
    v_sub7 = np.concatenate([_spd_tangent_vector(xb) for xb in sub_7])
    v_loc = np.concatenate([_spd_tangent_vector(xb[montage_idx, :]) for xb in bands_6])
    return np.nan_to_num(np.concatenate([v_6b, v_sub7, v_loc])).reshape(1, -1).astype(np.float32)


# ---------------------------------------------------------------------------
# 4. Filter-Bank Common Spatial Patterns (FBCSP) (Train-Fold Fit Only — Flaw #26)
# ---------------------------------------------------------------------------

class FilterBankCSP:
    """
    Multiclass One-vs-Rest Filter-Bank Common Spatial Patterns (FBCSP) log-variance extractor.
    Spatial filters are fitted strictly inside training folds (zero CV leakage).
    """

    def __init__(
        self,
        n_components: int = 2,
        cutoffs: Optional[List[Tuple[float, float]]] = None,
        fs: int = SAMPLING_RATE,
        reg: float = 1e-4,
    ):
        self.n_components = int(n_components)
        self.cutoffs = cutoffs or [
            (0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 40.0)
        ]
        self.fs = int(fs)
        self.reg = float(reg)
        self.filters_: List[np.ndarray] = []

    def fit(self, X_raw_train: np.ndarray, y_train: np.ndarray) -> "FilterBankCSP":
        from scipy.linalg import eigh

        classes = np.unique(y_train)
        filtered = bandpass_filter_bank(X_raw_train, self.cutoffs, fs=self.fs)
        self.filters_ = []
        n_ch = X_raw_train.shape[1]
        for xb in filtered:
            covs = compute_spd_covariances(xb, reg=self.reg, trace_norm=True)
            band_filters = []
            for c in classes:
                c_pos = np.mean(covs[y_train == c], axis=0)
                c_neg = np.mean(covs[y_train != c], axis=0)
                c_tot = c_pos + c_neg + 1e-6 * np.eye(n_ch)
                evals, evecs = eigh(c_pos, c_tot)
                order = np.argsort(np.abs(evals - 0.5))[::-1]
                band_filters.append(evecs[:, order[: self.n_components]].T)
            self.filters_.append(np.vstack(band_filters))
        return self

    def transform(self, X_raw: np.ndarray) -> np.ndarray:
        if not self.filters_:
            raise RuntimeError("FilterBankCSP must be fitted before transform().")
        filtered = bandpass_filter_bank(X_raw, self.cutoffs, fs=self.fs)
        feats = []
        for xb, W in zip(filtered, self.filters_):
            proj = np.einsum("fc,nct->nft", W, xb)
            var = np.var(proj, axis=2) + 1e-12
            log_var = np.log(var / np.sum(var, axis=1, keepdims=True))
            feats.append(log_var)
        return np.nan_to_num(np.hstack(feats)).astype(np.float32)

    def fit_transform(self, X_raw_train: np.ndarray, y_train: np.ndarray) -> np.ndarray:
        return self.fit(X_raw_train, y_train).transform(X_raw_train)


if __name__ == "__main__":
    rng = np.random.RandomState(42)
    dummy = rng.randn(16, 14, 128).astype(np.float32)
    y_d = np.arange(16) % 4
    ts_ext = MultiScaleTangentExtractor(geometry="tangent_fold", subband_mode="non_overlapping").fit(dummy)
    F_ts = ts_ext.transform(dummy)
    fbcsp = FilterBankCSP(n_components=2).fit_transform(dummy, y_d)
    print("Verified MultiScaleTangentExtractor shape:", F_ts.shape, "blocks:", ts_ext.block_dims_)
    print("Verified FilterBankCSP shape:", fbcsp.shape)
