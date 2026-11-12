"""
dataset_loader.py
=================
Canonical data ingestion, provenance tracking, cache integrity verification, and
block reconstruction for the REAL Mendeley EEGIS Dataset (DOI: 10.17632/73g4fw884c.1).

Remediated audit items:
  - Uses shared `eeg_preprocessing.py` for CSV header/channel/NaN/Inf/length validation (Flaws #19-#22)
  - Eliminates silent `except Exception: continue` blocks; logs structured errors in
    `results/dataset_audit_report.json` (Flaw #23)
  - Explicitly records Mendeley anonymization (`subject_ids="anonymized_unrecoverable"`,
    `subject_ids_recoverable=False`) instead of guessing participant IDs (Flaw #2)
  - Computes 8s utterance `block_ids` (0..336) and within-block `chunk_ids` (0..11), verifies
    exact 48-sample overlap between consecutive chunks (80-sample stride -> 1008-sample continuous block)
  - Validates `.npz` caches with cryptographic `.meta.json` sidecars (Flaw #24)
"""

import os
import glob
import json
import hashlib
import numpy as np
from typing import Tuple, List, Dict, Optional, Any

from eeg_preprocessing import (
    CODE_VERSION,
    CHANNEL_NAMES,
    CLASS_MAP,
    SAMPLING_RATE,
    EPOCH_DURATION,
    SAMPLES_PER_EPOCH,
    BAND_NAMES,
    CANONICAL_BAND_CUTOFFS,
    load_eeg_epoch_file,
    preprocess_epoch,
    sha256_file,
)

# Unified alias for backward compatibility
BAND_CUTOFFS: Dict[str, Tuple[float, float]] = CANONICAL_BAND_CUTOFFS
UNRECOVERABLE_SUBJECT_LABEL: str = "anonymized_unrecoverable"
DATASET_DOI: str = "10.17632/73g4fw884c.1"


def _find_mendeley_tree_root(data_dir: str) -> Optional[str]:
    base_dir = os.path.dirname(os.path.abspath(data_dir))
    candidates = [
        os.path.join(base_dir, "dataset", "EEGIS - Electroencephalogram Imagined Speech dataset"),
        os.path.join(base_dir, "dataset"),
        os.path.join(data_dir, "EEGIS - Electroencephalogram Imagined Speech dataset"),
        r"D:\EEG_Imagined_Speech\dataset\EEGIS - Electroencephalogram Imagined Speech dataset",
    ]
    for cand in candidates:
        if all(os.path.isdir(os.path.join(cand, b)) for b in BAND_NAMES):
            return cand
    return None


def _find_real_csv_files(data_dir: str) -> List[str]:
    """Locate raw real-EEGIS class CSV files from data_dir or sibling dataset/ folder."""
    base_dir = os.path.dirname(os.path.abspath(data_dir)) if os.path.isabs(data_dir) else "."
    candidate_roots = [
        os.path.join(data_dir, "eegis_raw"),
        os.path.join(base_dir, "dataset", "EEGIS - Electroencephalogram Imagined Speech dataset", "raw"),
        os.path.join(base_dir, "dataset", "raw"),
        r"D:\EEG_Imagined_Speech\dataset\EEGIS - Electroencephalogram Imagined Speech dataset\raw",
        data_dir,
        os.path.join(base_dir, "dataset"),
    ]
    band_dirs = {f"{os.sep}{b}{os.sep}" for b in ("alpha", "beta", "delta", "theta", "gamma")}
    for root in candidate_roots:
        if not os.path.isdir(root):
            continue
        files = glob.glob(os.path.join(root, "**", "*.csv"), recursive=True)
        files = [f for f in files if "test_signals" not in f]
        if root.endswith(f"{os.sep}dataset") or root == os.path.join(base_dir, "dataset"):
            files = [f for f in files if not any(bd in f.lower() for bd in band_dirs)]
        if files:
            print(f"[*] Discovered {len(files)} raw real EEGIS CSV files in '{root}'.")
            return sorted(files)
    return []


def _parse_class_id_from_path(file_path: str) -> Optional[int]:
    parts = os.path.normpath(file_path).split(os.sep)
    for p in reversed(parts):
        p_lower = p.lower()
        for c_idx in range(9):
            if f"class_{c_idx}" == p_lower or f"class_{c_idx}" in p_lower:
                return c_idx
        for c_idx, c_name in CLASS_MAP.items():
            name_tokens = c_name.lower().replace("(", "").replace(")", "").split()
            if any(token == p_lower for token in name_tokens):
                return c_idx
    return None


def _cache_meta_path(cache_path: str) -> str:
    return cache_path + ".meta.json"


def _write_cache_with_meta(
    cache_path: str,
    arrays: Dict[str, np.ndarray],
    extra_meta: Dict[str, Any],
) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
    np.savez_compressed(cache_path, **arrays)
    meta = {
        "code_version": CODE_VERSION,
        "dataset_doi": DATASET_DOI,
        "sampling_rate_hz": SAMPLING_RATE,
        "samples_per_epoch": SAMPLES_PER_EPOCH,
        "channel_names": CHANNEL_NAMES,
        "band_names": BAND_NAMES,
        "band_cutoffs": {k: list(v) for k, v in CANONICAL_BAND_CUTOFFS.items()},
        "subject_ids_recoverable": False,
        "subject_ids_policy": (
            "Mendeley EEGIS contains no participant/subject IDs in directories, filenames, or CSV headers; "
            "all entries are tagged 'anonymized_unrecoverable'."
        ),
        "npz_sha256": sha256_file(cache_path),
    }
    meta.update(extra_meta)
    with open(_cache_meta_path(cache_path), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def _validate_cache(cache_path: str, required_keys: List[str]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    meta_path = _cache_meta_path(cache_path)
    if not os.path.exists(cache_path):
        return False, None, "Cache .npz missing"
    if not os.path.exists(meta_path):
        return False, None, f"Cache metadata '{meta_path}' missing (stale/unverified cache)"
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as exc:
        return False, None, f"Unreadable metadata JSON: {exc}"

    if meta.get("code_version") != CODE_VERSION:
        return False, meta, f"Code version mismatch ({meta.get('code_version')} != {CODE_VERSION})"
    expected_cutoffs = {k: list(v) for k, v in CANONICAL_BAND_CUTOFFS.items()}
    if meta.get("band_cutoffs") != expected_cutoffs:
        return False, meta, "Band cutoff metadata mismatch"
    if meta.get("sampling_rate_hz") != SAMPLING_RATE or meta.get("samples_per_epoch") != SAMPLES_PER_EPOCH:
        return False, meta, "Sampling rate or epoch length metadata mismatch"
    actual_sha = sha256_file(cache_path)
    if actual_sha != meta.get("npz_sha256"):
        return False, meta, f"Cache SHA-256 mismatch ({actual_sha[:12]} != {str(meta.get('npz_sha256'))[:12]})"

    try:
        with np.load(cache_path, allow_pickle=False) as bundle:
            for k in required_keys:
                if k not in bundle:
                    return False, meta, f"Required key '{k}' missing from cache"
            if tuple(bundle["X"].shape) != tuple(meta.get("shape", ())):
                return False, meta, f"Shape mismatch ({bundle['X'].shape} != {meta.get('shape')})"
    except Exception as exc:
        return False, meta, f"Corrupt .npz archive: {exc}"

    return True, meta, "ok"


def _compute_overlap_diagnostics(
    raw_epochs: np.ndarray,
    block_ids: np.ndarray,
    chunk_ids: np.ndarray,
    overlap_samples: int = 48,
) -> Dict[str, Any]:
    """Verifies exact consecutive overlap across all chunks within every block."""
    within_diffs = []
    boundary_diffs = []
    n = len(raw_epochs)
    for i in range(n - 1):
        diff = float(np.max(np.abs(raw_epochs[i, :, -overlap_samples:] - raw_epochs[i + 1, :, :overlap_samples])))
        if block_ids[i] == block_ids[i + 1]:
            within_diffs.append(diff)
        elif chunk_ids[i] == 11 and chunk_ids[i + 1] == 0:
            boundary_diffs.append(diff)

    n_nonzero_within = int(sum(1 for d in within_diffs if d > 1e-3))
    return {
        "overlap_samples": overlap_samples,
        "stride_samples": SAMPLES_PER_EPOCH - overlap_samples,
        "continuous_block_samples": SAMPLES_PER_EPOCH + 11 * (SAMPLES_PER_EPOCH - overlap_samples),
        "within_block_pairs": len(within_diffs),
        "within_block_max_abs_diff": float(max(within_diffs)) if within_diffs else 0.0,
        "within_block_nonzero_discontinuities": n_nonzero_within,
        "between_block_mean_abs_diff": float(np.mean(boundary_diffs)) if boundary_diffs else 0.0,
    }


def _write_audit_and_manifest(
    base_dir: str,
    audit_report: Dict[str, Any],
    manifest_records: Optional[List[Dict[str, Any]]] = None,
) -> None:
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    audit_path = os.path.join(results_dir, "dataset_audit_report.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    if manifest_records is not None:
        manifest_path = os.path.join(results_dir, "dataset_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "code_version": CODE_VERSION,
                    "dataset_doi": DATASET_DOI,
                    "n_trials": len(manifest_records),
                    "subject_ids_recoverable": False,
                    "records": manifest_records,
                },
                f,
                indent=2,
            )


def load_eegis_dataset(data_dir: str = "data", verify_cache: bool = True) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Loads real EEGIS raw trials (4,044 x 14 x 128) using canonical `preprocess_epoch`.
    Never suppresses parse exceptions silently; writes audit diagnostics to `results/dataset_audit_report.json`.
    """
    real_npz = os.path.join(data_dir, "eegis_real_dataset.npz")
    if verify_cache:
        ok, meta, reason = _validate_cache(real_npz, ["X", "y"])
        if ok:
            with np.load(real_npz, allow_pickle=False) as bundle:
                X = bundle["X"].astype(np.float32)
                y = bundle["y"].astype(np.int64)
            print(f"[+] Loaded verified raw EEGIS archive '{real_npz}' ({X.shape}, sha={meta['npz_sha256'][:12]}).")
            return X, y, CHANNEL_NAMES
        elif os.path.exists(real_npz):
            print(f"[!] Ignoring unverified raw cache '{real_npz}': {reason}. Rebuilding...")

    csv_files = _find_real_csv_files(data_dir)
    if len(csv_files) == 0:
        raise FileNotFoundError(
            f"Real Mendeley EEGIS dataset not found in '{data_dir}' or 'dataset/'. "
            "Cannot rebuild unverified/missing cache without raw CSV tree."
        )

    trials, labels, rejected = [], [], []
    for file_path in csv_files:
        class_id = _parse_class_id_from_path(file_path)
        if class_id is None:
            rejected.append({"file": file_path, "error": "Unrecognized class folder/filename"})
            continue
        try:
            raw_ep = load_eeg_epoch_file(file_path, expected_fs=SAMPLING_RATE, min_samples=SAMPLES_PER_EPOCH)
            proc_ep = preprocess_epoch(raw_ep, expected_channels=14, min_samples=SAMPLES_PER_EPOCH)
            trials.append(proc_ep)
            labels.append(class_id)
        except Exception as exc:
            rejected.append({"file": file_path, "error": f"{type(exc).__name__}: {exc}"})

    base_dir = os.path.dirname(os.path.abspath(data_dir))
    _write_audit_and_manifest(
        base_dir,
        {
            "loader": "load_eegis_dataset",
            "code_version": CODE_VERSION,
            "discovered_files": len(csv_files),
            "accepted_trials": len(trials),
            "rejected_count": len(rejected),
            "rejected_files": rejected,
        },
    )
    if rejected:
        raise RuntimeError(
            f"Dataset ingestion halted: {len(rejected)} files failed strict validation. "
            f"First error: {rejected[0]}"
        )
    if len(trials) == 0:
        raise RuntimeError(f"No valid 14-channel trials discovered in '{data_dir}'.")

    X = np.array(trials, dtype=np.float32)
    y = np.array(labels, dtype=np.int64)
    _write_cache_with_meta(
        real_npz,
        {"X": X, "y": y},
        {"shape": list(X.shape), "n_trials": int(len(y)), "rejected_count": 0},
    )
    print(f"[+] Parsed & cached verified raw EEGIS dataset: {X.shape}")
    return X, y, CHANNEL_NAMES


def load_eegis_6band_with_provenance(
    data_dir: str = "data",
    verify_cache: bool = True,
    write_manifest: bool = True,
) -> Dict[str, Any]:
    """
    Canonical 6-band real EEGIS loader returning complete provenance:
      X: (4044, 6, 14, 128) float32
      y: (4044,) int64 class IDs 0..8
      block_ids: (4044,) int64 8s block group IDs (0..336)
      chunk_ids: (4044,) int64 within-block chunk indices (0..11)
      subject_ids: (4044,) str array filled with 'anonymized_unrecoverable'
      subject_ids_recoverable: False
      source_files: list of relative CSV paths
      raw_sha256s: list of SHA-256 digests of raw CSVs
      band_names: BAND_NAMES
      cache_meta: validated metadata dict
    """
    cache_6b = os.path.join(data_dir, "eegis_6band_real.npz")
    required_keys = ["X", "y", "groups", "chunk_ids", "raw_epochs_uncentered"]
    base_dir = os.path.dirname(os.path.abspath(data_dir))
    manifest_path = os.path.join(base_dir, "results", "dataset_manifest.json")

    if verify_cache:
        ok, meta, reason = _validate_cache(cache_6b, required_keys)
        if ok:
            with np.load(cache_6b, allow_pickle=False) as bundle:
                X_6b = bundle["X"].astype(np.float32)
                y = bundle["y"].astype(np.int64)
                block_ids = bundle["groups"].astype(np.int64)
                chunk_ids = bundle["chunk_ids"].astype(np.int64)
                raw_uncentered = bundle["raw_epochs_uncentered"].astype(np.float32)
                source_files = (
                    bundle["source_files"].tolist()
                    if "source_files" in bundle
                    else [f"trial_{i:04d}" for i in range(len(y))]
                )
                raw_sha256s = (
                    bundle["raw_sha256s"].tolist()
                    if "raw_sha256s" in bundle
                    else ["" for _ in range(len(y))]
                )
            print(f"[+] Loaded verified 6-band archive '{cache_6b}' ({X_6b.shape}, sha={meta['npz_sha256'][:12]}).")
            return {
                "X": X_6b,
                "y": y,
                "block_ids": block_ids,
                "chunk_ids": chunk_ids,
                "raw_epochs_uncentered": raw_uncentered,
                "subject_ids": np.full(len(y), UNRECOVERABLE_SUBJECT_LABEL, dtype=object),
                "subject_ids_recoverable": False,
                "source_files": source_files,
                "raw_sha256s": raw_sha256s,
                "band_names": BAND_NAMES,
                "cache_meta": meta,
            }
        elif os.path.exists(cache_6b):
            print(f"[!] 6-band cache '{cache_6b}' failed verification ({reason}). Rebuilding from source CSV tree...")

    mendeley_root = _find_mendeley_tree_root(data_dir)
    if mendeley_root is None:
        raise FileNotFoundError(
            f"Cannot build verified 6-band EEGIS cache: raw Mendeley CSV tree not found near '{data_dir}' or D:\\EEG_Imagined_Speech\\dataset."
        )

    print(f"[*] Parsing verified 6-band Mendeley EEGIS tree from '{mendeley_root}'...")
    X_list, y_list, block_list, chunk_list = [], [], [], []
    raw_uncentered_list, source_files, raw_sha256s = [], [], []
    rejected = []
    manifest_records = []
    group_counter = 0
    per_class_counts: Dict[str, int] = {}

    for c_idx in range(9):
        c_name = f"class_{c_idx}"
        raw_cls_dir = os.path.join(mendeley_root, "raw", c_name)
        if not os.path.isdir(raw_cls_dir):
            rejected.append({"file": raw_cls_dir, "error": "Missing raw class directory"})
            continue

        csv_files = sorted(
            [f for f in os.listdir(raw_cls_dir) if f.endswith(".csv")],
            key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 999999,
        )
        per_class_counts[CLASS_MAP[c_idx]] = len(csv_files)
        if len(csv_files) % 12 != 0:
            rejected.append({
                "file": raw_cls_dir,
                "error": f"Expected multiple of 12 chunks per 8s block in {c_name}, got {len(csv_files)}",
            })

        for idx, fname in enumerate(csv_files):
            trial_bands = []
            raw_sig_uncentered = None
            raw_hash = ""
            ok_trial = True
            for b_name in BAND_NAMES:
                fpath = os.path.join(mendeley_root, b_name, c_name, fname)
                try:
                    sig_raw = load_eeg_epoch_file(
                        fpath,
                        expected_fs=SAMPLING_RATE,
                        min_samples=SAMPLES_PER_EPOCH,
                        max_abs_uv=25000.0,
                    )
                    if b_name == "raw":
                        raw_sig_uncentered = sig_raw.astype(np.float32)
                        raw_hash = sha256_file(fpath)
                        sig_proc = preprocess_epoch(sig_raw, expected_channels=14, min_samples=SAMPLES_PER_EPOCH)
                    else:
                        sig_proc = sig_raw.astype(np.float32)
                    trial_bands.append(sig_proc)
                except Exception as exc:
                    rejected.append({"file": fpath, "error": f"{type(exc).__name__}: {exc}"})
                    ok_trial = False
                    break

            if not ok_trial:
                continue

            trial_idx = len(X_list)
            blk_id = group_counter + (idx // 12)
            chk_id = idx % 12
            rel_path = f"raw/{c_name}/{fname}"

            X_list.append(np.stack(trial_bands, axis=0))
            raw_uncentered_list.append(raw_sig_uncentered)
            y_list.append(c_idx)
            block_list.append(blk_id)
            chunk_list.append(chk_id)
            source_files.append(rel_path)
            raw_sha256s.append(raw_hash)

            manifest_records.append(
                {
                    "trial_idx": trial_idx,
                    "class_id": c_idx,
                    "class_name": CLASS_MAP[c_idx],
                    "block_id": blk_id,
                    "chunk_id": chk_id,
                    "subject_id": UNRECOVERABLE_SUBJECT_LABEL,
                    "source_file": rel_path,
                    "raw_sha256": raw_hash,
                }
            )
        group_counter += len(csv_files) // 12

    if rejected:
        _write_audit_and_manifest(
            base_dir,
            {
                "loader": "load_eegis_6band_with_provenance",
                "code_version": CODE_VERSION,
                "mendeley_root": mendeley_root,
                "accepted_trials": len(X_list),
                "rejected_count": len(rejected),
                "rejected_files": rejected,
            },
        )
        raise RuntimeError(f"Strict 6-band ingestion failed on {len(rejected)} files. First error: {rejected[0]}")

    X_6b = np.array(X_list, dtype=np.float32)
    raw_uncentered_arr = np.array(raw_uncentered_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    block_ids = np.array(block_list, dtype=np.int64)
    chunk_ids = np.array(chunk_list, dtype=np.int64)

    overlap_diag = _compute_overlap_diagnostics(raw_uncentered_arr, block_ids, chunk_ids, overlap_samples=48)
    if overlap_diag["within_block_nonzero_discontinuities"] != 0:
        raise RuntimeError(
            f"Block structure integrity check failed: {overlap_diag['within_block_nonzero_discontinuities']} discontinuities inside blocks."
        )

    manifest_hash = hashlib.sha256("|".join(raw_sha256s).encode("utf-8")).hexdigest()
    extra_meta = {
        "shape": list(X_6b.shape),
        "n_trials": int(len(y)),
        "n_blocks": int(len(np.unique(block_ids))),
        "chunks_per_block": 12,
        "per_class_counts": per_class_counts,
        "overlap_diagnostics": overlap_diag,
        "manifest_sha256": manifest_hash,
        "rejected_count": 0,
    }
    meta = _write_cache_with_meta(
        cache_6b,
        {
            "X": X_6b,
            "y": y,
            "groups": block_ids,
            "chunk_ids": chunk_ids,
            "raw_epochs_uncentered": raw_uncentered_arr,
            "source_files": np.array(source_files),
            "raw_sha256s": np.array(raw_sha256s),
        },
        extra_meta,
    )
    audit_report = {
        "loader": "load_eegis_6band_with_provenance",
        "code_version": CODE_VERSION,
        "dataset_doi": DATASET_DOI,
        "mendeley_root": mendeley_root,
        "accepted_trials": int(len(y)),
        "n_blocks": int(len(np.unique(block_ids))),
        "subject_ids_recoverable": False,
        "subject_ids_note": "No participant/subject identifiers exist in Mendeley EEGIS; zero synthetic subject IDs created.",
        "per_class_counts": per_class_counts,
        "overlap_diagnostics": overlap_diag,
        "manifest_sha256": manifest_hash,
        "rejected_count": 0,
        "rejected_files": [],
    }
    _write_audit_and_manifest(
        base_dir,
        audit_report,
        manifest_records if write_manifest else None,
    )
    print(
        f"[+] Cached verified 6-band dataset '{cache_6b}': {X_6b.shape}, "
        f"{extra_meta['n_blocks']} 8s blocks, 0 overlap discontinuities."
    )
    return {
        "X": X_6b,
        "y": y,
        "block_ids": block_ids,
        "chunk_ids": chunk_ids,
        "raw_epochs_uncentered": raw_uncentered_arr,
        "subject_ids": np.full(len(y), UNRECOVERABLE_SUBJECT_LABEL, dtype=object),
        "subject_ids_recoverable": False,
        "source_files": source_files,
        "raw_sha256s": raw_sha256s,
        "band_names": BAND_NAMES,
        "cache_meta": meta,
    }


def load_eegis_6band_dataset(data_dir: str = "data", verify_cache: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Backward-compatible 4-tuple wrapper around `load_eegis_6band_with_provenance`.
    Returns: (X_6b, y, block_ids, BAND_NAMES)
    """
    prov = load_eegis_6band_with_provenance(data_dir=data_dir, verify_cache=verify_cache, write_manifest=True)
    return prov["X"], prov["y"], prov["block_ids"], prov["band_names"]


def reconstruct_continuous_8s_blocks(
    raw_epochs: np.ndarray,
    y: np.ndarray,
    block_ids: np.ndarray,
    chunk_ids: np.ndarray,
    overlap_samples: int = 48,
    detrend: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Reconstructs stitch-verified continuous 8-second utterance recordings from overlapping 12-chunk blocks.
    With 128-sample chunks and 48-sample overlap (stride = 80 samples), each 12-chunk block produces
    a continuous (14, 1008) recording without chunk duplication across CV folds.
    """
    stride = SAMPLES_PER_EPOCH - overlap_samples
    unique_blocks = np.unique(block_ids)
    out_X, out_y, out_b = [], [], []
    for blk in unique_blocks:
        idx = np.where(block_ids == blk)[0]
        order = np.argsort(chunk_ids[idx])
        idx = idx[order]
        if len(idx) != 12 or not np.array_equal(chunk_ids[idx], np.arange(12)):
            raise ValueError(f"Block {blk} does not contain complete 0..11 chunk sequence.")
        parts = [raw_epochs[idx[0]].astype(np.float64)]
        for k in range(1, 12):
            prev = raw_epochs[idx[k - 1]]
            curr = raw_epochs[idx[k]]
            max_err = float(np.max(np.abs(prev[:, -overlap_samples:] - curr[:, :overlap_samples])))
            if max_err > 1e-3:
                raise ValueError(f"Block {blk} overlap mismatch between chunk {k-1} and {k}: {max_err}")
            parts.append(curr[:, overlap_samples:].astype(np.float64))
        full_block = np.concatenate(parts, axis=1)
        if detrend:
            full_block = full_block - np.mean(full_block, axis=1, keepdims=True)
        out_X.append(full_block.astype(np.float32))
        out_y.append(int(y[idx[0]]))
        out_b.append(int(blk))
    return np.stack(out_X, axis=0), np.array(out_y, dtype=np.int64), np.array(out_b, dtype=np.int64)


if __name__ == "__main__":
    prov = load_eegis_6band_with_provenance(data_dir="data", verify_cache=False, write_manifest=True)
    Xc, yc, bc = reconstruct_continuous_8s_blocks(
        prov["raw_epochs_uncentered"], prov["y"], prov["block_ids"], prov["chunk_ids"]
    )
    print("Verified 6-band provenance load:", prov["X"].shape, "blocks:", len(np.unique(prov["block_ids"])))
    print("Reconstructed continuous 8s blocks:", Xc.shape, "labels:", yc.shape)
