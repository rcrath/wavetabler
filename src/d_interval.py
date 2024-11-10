# d_interval.py

import numpy as np
from scipy.signal import find_peaks
from scipy.stats import mode
import matplotlib.pyplot as plt
import soundfile as sf
import argparse

def autocorr(x):
    no_dc_x = (x - np.mean(x))  # Remove DC offset
    acorr = np.correlate(no_dc_x, no_dc_x, mode='full')  # Full autocorrelation
    norm_acorr = (acorr / np.max(abs(acorr)))[-len(x):]  # Normalize and use second half
    return norm_acorr

def extract_best_interval(norm_acorr):
    # Optimized peak detection using additional parameters
    peaks, _ = find_peaks(norm_acorr, prominence=0.5, distance=10, height=0.1)  # Adjusted parameters
    if len(peaks) < 2:
        print("Insufficient peaks found for interval analysis.")
        return None, 0

    # Calculate intervals between consecutive peaks
    intervals = np.diff(peaks)
    
    # Find the mode of the intervals (most common interval)
    mode_result = mode(intervals)
    best_interval = mode_result.mode[0] if isinstance(mode_result.mode, np.ndarray) else mode_result.mode
    count = mode_result.count[0] if isinstance(mode_result.count, np.ndarray) else mode_result.count
    confidence = count / len(intervals) if len(intervals) > 0 else 0

    if best_interval is not None:
        print(f"Best interval: {best_interval} samples (mode of intervals), Confidence: {confidence:.2f}")
    else:
        print("Could not determine a best interval.")

    return best_interval, confidence

def calculate_pitch(best_interval, sample_rate):
    if best_interval is None or best_interval <= 0:
        return None
    # Calculate frequency in Hz
    frequency = sample_rate / best_interval
    print(f"Frequency: {frequency:.2f} Hz")
    return frequency

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Input audio file path")
parser.add_argument('input_audio_path', help="Path to the input audio file")
args = parser.parse_args()

try:
    # Load the audio file and get the sample rate
    x, sample_rate = sf.read(args.input_audio_path)
    
    # If the audio has more than one channel, take the first channel
    if x.ndim > 1:
        x = x[:, 0]
except Exception as e:
    print(f"Error reading audio file: {e}")
    exit()

acf = autocorr(x)
best_interval, confidence = extract_best_interval(acf)

# Calculate the pitch frequency using the sample rate and best interval
frequency = calculate_pitch(best_interval, sample_rate)

# Plotting the autocorrelation and the peaks for visualization
plt.figure(figsize=(10, 5))
plt.plot(acf, label='Autocorrelation')
if best_interval:
    peaks, _ = find_peaks(acf, prominence=0.5, distance=10, height=0.1)  # Using the same parameters for visualization
    plt.scatter(peaks, acf[peaks], color='red', label='Peaks', zorder=5)
plt.title("Autocorrelation with Peaks")
plt.xlabel("Sample Index")
plt.ylabel("Normalized Amplitude")
plt.legend()
plt.show()

# Output the sample rate, best interval, confidence, and frequency
print(f"Sample rate: {sample_rate} Hz")
best_interval, confidence, sample_rate, frequency
