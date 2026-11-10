"""
test_eeg_signal.py
==================
Signal-Driven Real-Time Inference Tester for EEG Imagined Words BCI.
Designed for NIT Warangal BCI Project Topic 6.

Demonstrates model prediction directly from raw biological EEG signals:
- Accepts raw EEG signal files (.csv or .npy) containing 14 electrode voltages.
- Zero manual class prompts or terminal text labels.
- Computes signal telemetry, runs feature extraction & model inference.
- Outputs decoded patient thought, confidence gauge, probability bars, and latency.
- Validates against medical ground truth registry.

Usage:
    python test_eeg_signal.py 1                          # Test signal 1
    python test_eeg_signal.py test_signals/eeg_signal_03.csv
    python test_eeg_signal.py eeg_signal_05.npy
    python test_eeg_signal.py --all                      # Test all 9 benchmark signals
    python test_eeg_signal.py                            # Interactive menu
"""

import os
import sys

# Ensure src/ and current dir are in Python path
curr_dir = os.path.dirname(os.path.abspath(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)
src_dir = os.path.join(curr_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from predict import (
    load_best_model,
    load_raw_eeg_file,
    predict_signal,
    print_single_prediction,
    evaluate_all_test_signals,
    resolve_signal_path,
    interactive_menu,
    main
)

def test_eeg_signal(file_path: str):
    """Programmatic entry point to test any EEG signal file."""
    model_pkg, model_type = load_best_model()
    resolved = resolve_signal_path(file_path)
    if resolved:
        print_single_prediction(resolved, model_pkg, model_type)
    else:
        raise FileNotFoundError(f"EEG signal file '{file_path}' could not be resolved.")

if __name__ == "__main__":
    main()
