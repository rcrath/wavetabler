

# debug.py

import os
import soundfile as sf
import numpy as np
import re
from aa_common import is_rising_from_zero, is_rising_to_zero

# Define the threshold in amplitude (equivalent to -60 dB)
THRESHOLD_DB = -60
THRESHOLD_AMPLITUDE = 10 ** (THRESHOLD_DB / 20.0)

# Helper functions
# temporary
def is_rising_from_zero_debug(data, threshold_amplitude=THRESHOLD_AMPLITUDE, min_rising_samples=3):
    # Helper function to convert amplitude to decibels
    def amplitude_to_db(amplitude):
        return 20 * np.log10(amplitude) if amplitude > 0 else float('-inf')

    # Summarize the first few samples in terms of amplitude and decibel range
    first_samples = data[:min(len(data), 4)]  # Get the first four (or fewer if data is shorter) samples
    min_amp = np.min(first_samples)
    max_amp = np.max(first_samples)
    min_db = amplitude_to_db(abs(min_amp))
    max_db = amplitude_to_db(abs(max_amp))

    # Print a summary
    # print(f"Summary of first four samples: Amplitude range [{min_amp:.6f}, {max_amp:.6f}], Decibel range [{min_db:.2f} dB, {max_db:.2f} dB]")

    # Check if the first sample is within the threshold
    if abs(data[0]) > threshold_amplitude:
        return False, data[:min_rising_samples]

    # Check if the signal is rising from zero
    for i in range(1, min_rising_samples + 1):
        if data[i] <= 0 or data[i] <= data[i - 1]:
            return False, data[:min_rising_samples]

    return True, data[:min_rising_samples]

def check_for_zero_samples(data, num_samples=10):
    # Check the first and last few samples for zeros
    first_samples = data[:num_samples]
    last_samples = data[-num_samples:]
    
    print(f"First {num_samples} samples: {first_samples}")
    print(f"Last {num_samples} samples: {last_samples}")
    
    first_zero_count = np.sum(first_samples == 0)
    last_zero_count = np.sum(last_samples == 0)
    
    print(f"Number of zeros in the first {num_samples} samples: {first_zero_count}")
    print(f"Number of zeros in the last {num_samples} samples: {last_zero_count}")


def amplitude_to_db(amplitude):
    return 20 * np.log10(amplitude) if amplitude > 0 else float('-inf')

def calculate_amplitude_stats(samples):
    samples = np.abs(samples)
    avg_amplitude = np.mean(samples)
    max_amplitude = np.max(samples)
    avg_db = amplitude_to_db(avg_amplitude)
    max_db = amplitude_to_db(max_amplitude)
    return avg_db, max_db

def check_192k_file(file_path):
    try:
        info = sf.info(file_path)
        return info.samplerate == 192000 and info.subtype == 'FLOAT'
    except Exception as e:
        return False

def check_frame_length(frames_folder):
    incorrect_length_files = []
    for file in os.listdir(frames_folder):
        file_path = os.path.join(frames_folder, file)
        if os.path.isfile(file_path) and file.endswith('.wav'):
            data, _ = sf.read(file_path)
            if len(data) != 2048:
                incorrect_length_files.append((file, len(data)))
    return incorrect_length_files

def check_concat_length_and_threshold(file_path):
    try:
        data, _ = sf.read(file_path)
        if len(data) % 2048 != 0:
            return False, "Not divisible by 2048 samples"
        for i in range(2048, len(data), 2048):
            if abs(data[i]) > THRESHOLD_AMPLITUDE:
                return False, f"Sample {i} exceeds -60 dB threshold"
        return True, "OK"
    except Exception as e:
        return False, str(e)

def count_files_with_regex(folder, pattern):
    matched_files = [f for f in os.listdir(folder) if pattern.match(f)]
    return len(matched_files), matched_files

def run_debug(current_folder=None):
    if current_folder:
        tmp_folder = os.path.join(current_folder, 'tmp')
    else:
        base_folder = os.getcwd()
        tmp_folders = [f for f in os.listdir(base_folder) if os.path.isdir(f)]
        
        print("\nAvailable folders:")
        for idx, folder in enumerate(tmp_folders):
            print(f"{idx + 1}. {folder}")

        choice = input("\nSelect a folder to check: ").strip()
        try:
            selected_folder = tmp_folders[int(choice) - 1]
        except (IndexError, ValueError):
            print("Invalid selection. Exiting.")
            return

        tmp_folder = os.path.join(base_folder, selected_folder, 'tmp')

    if not os.path.exists(tmp_folder):
        print("The selected folder does not contain a 'tmp' folder.")
        return

    seg_folder = os.path.join(tmp_folder, 'seg')  # Define the seg folder

    if not os.path.exists(seg_folder):
        print("The selected folder does not contain a 'seg' folder.")
        return

    report = []

    # Count segment files matching the regex in the seg folder
    pattern = re.compile(r"(.+seg_\d{4})(?:_dev|_atk)?\.wav", re.IGNORECASE)
    num_segment_files, segment_files = count_files_with_regex(seg_folder, pattern)
    report.append("\nSegment files:")
    report.append(f"Total segment files: {num_segment_files}")

    fail_rising_from_zero = 0
    fail_rising_to_zero = 0
    total_failed_rising_from_samples = []
    total_failed_rising_to_samples = []

    for seg_file in segment_files:
        file_path = os.path.join(seg_folder, seg_file)
        data, _ = sf.read(file_path)
        
        # Check if it starts with rising from zero
        rising_from_result, rising_from_samples = is_rising_from_zero_debug(data)
        if rising_from_result is None or not rising_from_result:
            fail_rising_from_zero += 1
            if isinstance(rising_from_samples, (list, np.ndarray)):  # Check if it's iterable
                total_failed_rising_from_samples.extend(np.abs(rising_from_samples))  # Accumulate failed samples
        
        # Check if it ends with rising to zero
        rising_to_result, rising_to_samples = is_rising_to_zero(data)
        if rising_to_result is None or not rising_to_result.all():  # Handle the None and array case here
            fail_rising_to_zero += 1
            if isinstance(rising_to_samples, (list, np.ndarray)):  # Check if it's iterable
                total_failed_rising_to_samples.extend(np.abs(rising_to_samples))  # Accumulate failed samples

    # Calculate dB stats for failed "rising from zero" and "rising to zero" samples
    if total_failed_rising_from_samples:
        avg_failed_rising_from_db = amplitude_to_db(np.mean(total_failed_rising_from_samples))
        max_failed_rising_from_db = amplitude_to_db(np.max(total_failed_rising_from_samples))
    else:
        avg_failed_rising_from_db = float('nan')
        max_failed_rising_from_db = float('nan')

    if total_failed_rising_to_samples:
        avg_failed_rising_to_db = amplitude_to_db(np.mean(total_failed_rising_to_samples))
        max_failed_rising_to_db = amplitude_to_db(np.max(total_failed_rising_to_samples))
    else:
        avg_failed_rising_to_db = float('nan')
        max_failed_rising_to_db = float('nan')

    # Append results to the report
    report.append(f"Files failing 'rising from zero' test: {fail_rising_from_zero}")
    report.append(f"Files failing 'rising to zero' test: {fail_rising_to_zero}")
    
    report.append(f"\nAverage amplitude of failed 'rising from zero' samples: {avg_failed_rising_from_db:.2f} dB")
    report.append(f"Highest amplitude of failed 'rising from zero' samples: {max_failed_rising_from_db:.2f} dB")
    report.append(f"Average amplitude of failed 'rising to zero' samples: {avg_failed_rising_to_db:.2f} dB")
    report.append(f"Highest amplitude of failed 'rising to zero' samples: {max_failed_rising_to_db:.2f} dB")

    # Print the final report
    print("\n=== Debug Report ===")
    for line in report:
        print(line)


if __name__ == "__main__":
    run_debug()


