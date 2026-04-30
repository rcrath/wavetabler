import os
import time
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, correlate
from tqdm import tqdm
import aa_common
from aa_common import (
    get_base, get_wavecycle_samples, set_wavecycle_samples, set_wavecycle_samples_target, input_with_defaults, get_tmp_folder, calculate_mode_wavecycle_length, set_all_segment_sizes, find_nearest_zero_crossing
)


def segment_by_period(path, period):
    """
    Cut the audio at `path` into ~period-sample wavecycles, snapping each cut
    to the nearest zero crossing for clean boundaries. Saves each segment to
    tmp/seg/<basename>_seg_NNNN.wav and registers it in aa_common.

    This is what autocorrelation mode does instead of e_seg's per-cycle
    zero-crossing detection: trust the autocorr-derived period and chop.
    """
    seg_folder = os.path.join(get_tmp_folder(), "seg")
    os.makedirs(seg_folder, exist_ok=True)

    data, sample_rate = sf.read(path)
    if data.ndim > 1:
        data = data[:, 0]

    file_base = os.path.splitext(os.path.basename(path))[0]
    snap_window = max(8, min(64, period // 8))  # ~12% of period, capped at 64

    # Estimate count up front so tqdm shows real progress
    estimated = max(1, len(data) // period)

    segment_sizes = []
    pos = 0
    seg_index = 0
    pbar = tqdm(total=estimated, desc="  segmenting by period", unit="seg", leave=False)
    while pos + period < len(data):
        target = pos + period
        end = find_nearest_zero_crossing(data, target, window=snap_window)
        # Guard against snap producing a non-progressing or out-of-bounds end
        if end <= pos or end > len(data):
            end = min(target, len(data))

        seg = data[pos:end]
        seg_name = f"{file_base}_seg_{seg_index:04d}.wav"
        sf.write(os.path.join(seg_folder, seg_name), seg, sample_rate, subtype='FLOAT')
        segment_sizes.append((seg_name, len(seg)))
        set_wavecycle_samples(seg_name, len(seg))
        aa_common.set_segment_position(seg_name, pos)
        pos = end
        seg_index += 1
        pbar.update(1)
    pbar.close()

    set_all_segment_sizes(segment_sizes)
    return seg_index


def autocorr(x):
    """
    FFT-based autocorrelation. O(N log N) instead of np.correlate's O(N^2) —
    matters because the upsampled input here is hundreds of thousands of
    samples. Numerically equivalent for peak-detection purposes.
    """
    x = x - np.mean(x)
    result = correlate(x, x, mode='full', method='fft')
    result = result[result.size // 2:]
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak
    return result

def run(processed_channel_files):
    # Reset accumulators so a re-run doesn't see stale entries.
    aa_common.clear_segment_positions()

    for path in processed_channel_files:
        print(f"Processing: {path}")

        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue

        try:
            data, sample_rate = sf.read(path)
        except Exception as e:
            print(f"Error reading file: {e}")
            continue

        if data.ndim > 1:
            data = data[:, 0]

        if np.max(np.abs(data)) > 0:
            data = data / np.max(np.abs(data))

        print(f"  computing autocorrelation ({len(data):,} samples)...", end='', flush=True)
        t0 = time.perf_counter()
        acf = autocorr(data)
        print(f" done ({time.perf_counter() - t0:.2f}s)")

        # Auto-falling prominence: start strict, ease off until peaks appear.
        # Pre-existing default was 1.0, which is mathematically impossible for a
        # normalized ACF (values in [-1, 1] can't have a prominence of 1.0).
        print("  finding peaks...", end='', flush=True)
        t0 = time.perf_counter()
        peak_idxs = []
        for prominence in (0.3, 0.1, 0.05):
            peak_idxs, _ = find_peaks(acf, prominence=prominence)
            if len(peak_idxs) > 1:
                break
        peak_intervals = np.diff(peak_idxs)
        print(f" {len(peak_intervals)} intervals at prominence={prominence} ({time.perf_counter() - t0:.2f}s)")

        if len(peak_intervals) == 0:
            print("Autocorrelation failed to detect a dominant period.")
            if np.all(data == 0):
                print("The input file appears to be silent. Skipping.")
                continue

            print(
                "  No clear period found at any tried prominence. This signal\n"
                "  likely doesn't have a stable single pitch (percussive,\n"
                "  noisy, or polyphonic). Try zero-crossing mode (method 1)\n"
                "  for inputs like this — autocorrelation needs a clear period.\n"
            )

            try:
                new_prominence = float(input_with_defaults(
                    "Enter a custom prominence to retry (e.g., 0.02), or empty to abort: ",
                    default="",
                ))
            except (ValueError, TypeError):
                print("  No retry value given. Skipping this file.")
                continue
            if not new_prominence:
                continue

            peak_idxs, _ = find_peaks(acf, prominence=new_prominence)
            peak_intervals = np.diff(peak_idxs)
            if len(peak_intervals) == 0:
                print("  Still no valid intervals. Skipping this file.")
                continue

        overall_mode = calculate_mode_wavecycle_length(peak_intervals)

        if overall_mode == 0:
            print("Could not determine a valid wavecycle length.")
            continue

        print(f"  period: {overall_mode} samples (avg {int(np.mean(peak_intervals))})")
        set_wavecycle_samples_target(overall_mode)

        # Actually segment the audio at period boundaries (snapped to zero crossings).
        # This is what autocorrelation mode is supposed to do — without this, no
        # segment files exist on disk and downstream phases (interpolate, build
        # wavetable) have nothing to work with.
        n_segs = segment_by_period(path, overall_mode)
        print(f"  segmented into {n_segs} wavecycles")

