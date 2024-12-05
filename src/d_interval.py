# d_interval.py

import numpy as np
import soundfile as sf
import os
import aa_common  # Import aa_common for common functions and paths
from scipy.stats import mode
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

def autocorr(data):
    """Calculate the autocorrelation of the given data."""
    n = len(data)
    result = np.correlate(data, data, mode='full')
    return result[n-1:]

def find_relevant_peaks(autocorr):
    """Find relevant peaks in the autocorrelation data."""
    peaks = np.where((autocorr[1:] > 0) & (autocorr[:-1] <= 0))[0]
    # print(f"Peaks found: {peaks}")
    return peaks

def extract_best_interval(autocorr):
    """Extract the best interval using peak detection and calculate the mode interval."""
    # Normalize the autocorrelation to prepare for peak detection
    norm_acorr = autocorr / np.max(autocorr)

    # Optimized peak detection using additional parameters
    peaks, _ = find_peaks(norm_acorr, prominence=0.5, distance=10, height=0.1)  # Adjusted parameters
    if len(peaks) < 2:
        print("Insufficient peaks found for interval analysis.")
        return 0, 0  # Return zero values if not enough peaks are found

    # Calculate intervals between consecutive peaks
    intervals = np.diff(peaks)
    
    # Find the mode of the intervals (most common interval)
    mode_result = mode(intervals)
    best_interval = mode_result.mode[0] if isinstance(mode_result.mode, np.ndarray) else mode_result.mode
    count = mode_result.count[0] if isinstance(mode_result.count, np.ndarray) else mode_result.count
    confidence = count / len(intervals) if len(intervals) > 0 else 0
    # Calculate how many intervals are within ±5 samples of the mode interval
    nearby_count = np.sum(np.abs(intervals - best_interval) <= 10)
    # Calculate the tolerance range as 1% of the mode interval
    # mode_tolerance = best_interval * 0.01

    if best_interval is not None:
        print(f"Best interval: {best_interval} samples (mode of intervals), Confidence: {confidence:.2f}")
    else:
        print("Could not determine a best interval.")

    return best_interval, count, confidence, nearby_count

def plot_segment_size_distribution(intervals, best_interval):
    """Plot the distribution of segment sizes and mark the mode interval."""
    # Calculate the counts for each unique interval size
    unique_intervals, counts = np.unique(intervals, return_counts=True)
    
    # Plot the distribution
    plt.figure(figsize=(10, 6))
    plt.bar(unique_intervals, counts, color='lightblue', edgecolor='black')
    plt.axvline(best_interval, color='red', linestyle='--', label=f"Mode: {best_interval} samples")
    plt.xlabel("Segment Size (Samples)")
    plt.ylabel("Count")
    plt.title("Distribution of Segment Sizes\nLook for a clearly prominent mode: \nthe more prominent, the more certain the results. \nClose to continue.", fontsize=10)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    # Add explanatory text
    # plt.text(0.5, -0.15, "Look for a clearly prominent mode: the more prominent, the more certain the results. Close to continue.",
    #         wrap=True, horizontalalignment='center', fontsize=10, color='gray', transform=plt.gcf().transFigure)
    plt.show()

def segment_and_save(data, sample_rate, peaks, seg_folder, base):
    segment_count = 0
    segments = []
    all_segmented_files = []
    segment_sizes = []

    # Function to find a rising zero crossing starting from a specific point and searching forward
    def find_rising_zero_crossing_forward(start_index):
        for i in range(start_index, len(data) - 1):
            if data[i] <= 0 < data[i + 1]:
                return i
        return start_index  # Fallback to the original index if no zero crossing is found

    # Function to find a rising zero crossing starting from a specific point and searching backward
    def find_rising_zero_crossing_backward(start_index):
        for i in range(start_index, 0, -1):
            if data[i - 1] < 0 <= data[i]:
                return i
        return 0  # Fallback to the beginning of the file if no zero crossing is found

    # Ensure the seg_folder exists
    if not os.path.exists(seg_folder):
        os.makedirs(seg_folder)

    for i in range(len(peaks) - 1):
        start_peak = peaks[i]
        next_peak = peaks[i + 1]
        interval = next_peak - start_peak

        # Find the previous rising zero crossing for the start
        start = find_rising_zero_crossing_backward(start_peak)

        # Calculate the initial end point
        end = start + interval

        # Adjust the end point to the next rising zero crossing if possible
        end = find_rising_zero_crossing_forward(end)

        if start < len(data) and end <= len(data):
            segment = data[start:end]
            segments.append(segment)

            # Save the segment
            segment_path = os.path.join(seg_folder, f"{base}_seg_{segment_count:04d}.wav")
            sf.write(segment_path, segment, sample_rate)
            all_segmented_files.append(segment_path)

            # Collect segment details
            segment_sizes.append((f"{base}_seg_{segment_count:04d}.wav", len(segment)))
            segment_count += 1

    return all_segmented_files, segment_sizes


    # Silence the first and last segments
    if segments:
        segments[0] = np.zeros_like(segments[0])
        segments[-1] = np.zeros_like(segments[-1])

    # Return both the segmented file paths and segment details
    return all_segmented_files, segment_sizes

def run(processed_files):
    """Main function to process the given files and segment them using autocorrelation."""

    all_segment_sizes = []  # Collect all segment details

    for file_path in processed_files:
        data, sample_rate = sf.read(file_path)
        autocorr_result = autocorr(data)
        
        # Calculate mode interval, count, and confidence using the updated method
        mode_interval, count, confidence, nearby_count = extract_best_interval(autocorr_result)
        frequency_hz = sample_rate / mode_interval if mode_interval > 0 else 0
        # Store mode_interval in aa_common using set_mode_interval
        aa_common.set_mode_interval(mode_interval)

        base = os.path.splitext(os.path.basename(file_path))[0]  # Extract base name
        seg_folder = os.path.join(aa_common.tmp_folder, "seg")
        # Call segment_and_save and collect the segmented file paths and segment sizes
        segmented_files, segment_sizes = segment_and_save(data, sample_rate, find_relevant_peaks(autocorr_result), seg_folder, base)
        all_segment_sizes.extend(segment_sizes)  # Collect segment details
        # print(f"segment_sizes: {segment_sizes}")
        # print(f"all_segment_sizes: {all_segment_sizes}")


        # plot_segment_size_distribution(np.diff(find_relevant_peaks(autocorr_result)), mode_interval)

    # Construct the wavecycle_samples dictionary
    wavecycle_samples = {segment_name: sample_count for segment_name, sample_count in all_segment_sizes}

    # Loop through the dictionary and set each segment name and sample count
    for segment_name, sample_count in wavecycle_samples.items():
        aa_common.set_wavecycle_samples(segment_name, sample_count)


    # Print for debugging purposes
    # print(f"wavecycle_samples from d_interval: {wavecycle_samples}")
    # print("go to f_sort")


