# d_interval.py

import numpy as np
import soundfile as sf
import os
import k_clean  # Import k_clean to handle the cleanup
import aa_common  # Import aa_common for common functions and paths

def autocorr(data):
    """Calculate the autocorrelation of the given data."""
    n = len(data)
    result = np.correlate(data, data, mode='full')
    return result[n-1:]

def find_relevant_peaks(autocorr):
    """Find relevant peaks in the autocorrelation data."""
    peaks = np.where((autocorr[1:] > 0) & (autocorr[:-1] <= 0))[0]
    return peaks

def segment_and_save(data, sample_rate, peaks, seg_folder, base):
    """Segment the data at the given peaks and save to the seg folder with proper naming."""
    segment_count = 0
    segments = []

    # Shift phase by -90 degrees (negative quarter of a period)
    phase_shift = int(sample_rate * 0.5)
    # phase_shift = 0

    # Create segments based on phase-shifted peaks
    for i in range(1, len(peaks)):
        start = peaks[i-1] + phase_shift
        end = peaks[i] + phase_shift
        if start < len(data) and end <= len(data):
            segments.append(data[start:end])

    # Silence the first and last segments
    if segments:
        segments[0] = np.zeros_like(segments[0])
        segments[-1] = np.zeros_like(segments[-1])

    # Save each segment with the naming convention {base}_seg_nnnn.wav
    if not os.path.exists(seg_folder):
        os.makedirs(seg_folder)  # Create the seg folder if it doesn't exist

    for idx, segment in enumerate(segments):
        segment_path = os.path.join(seg_folder, f"{base}_seg_{segment_count:04d}.wav")
        sf.write(segment_path, segment, sample_rate)
        # print(f"Saved segment {segment_count} to {segment_path}")
        segment_count += 1


def run(processed_files):
    """Main function to process the given files and segment them using autocorrelation."""
    for file_path in processed_files:
        data, sample_rate = sf.read(file_path)
        autocorr_result = autocorr(data)
        peaks = find_relevant_peaks(autocorr_result)

        print(f"File: {file_path}")
        print(f"Found {len(peaks)} relevant peaks for segmentation.")

        base = os.path.splitext(os.path.basename(file_path))[0]  # Extract base name
        seg_folder = os.path.join(aa_common.tmp_folder, "seg")
        segment_and_save(data, sample_rate, peaks, seg_folder, base)

    # Proceed to k_clean after processing
    # k_clean.run()
