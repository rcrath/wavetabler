# e_seg.py

import os
import numpy as np
import soundfile as sf
import aa_common

# Local version of is_rising_zero_crossing for segmentation
def is_rising_zero_crossing_seg(data, index):
    """Check if there is a valid rising zero-crossing at the given index."""
    if data[index - 1] < 0 and data[index] >= 0:
        if np.all(data[index - 8:index] < 0) and np.all(data[index:index + 8] > 0):
            return True
    return False

def run_segment(file_path):
    """
    This function segments the audio file into wavecycle segments based on zero-crossings and saves them.
    It skips any segment shorter than 64 samples.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}. Ensure the file is not deleted.")

    # Read the file (keep original sample rate and bit depth)
    data, samplerate = sf.read(file_path)
    base = os.path.splitext(os.path.basename(file_path))[0]
    tmp_folder = aa_common.get_tmp_folder()

    # Create the 'seg' subfolder inside the tmp folder
    seg_folder = os.path.join(tmp_folder, "seg")
    os.makedirs(seg_folder, exist_ok=True)  # Ensure the 'seg' folder exists

    segment_sizes = []  # Initialize the list to hold segment sizes
    prev_start_index = 0  # Start from the beginning
    in_segment = False
    segment_limit = 524288  # Limit for max segment size
    min_segment_size = 64  # Set the minimum segment size

    # print(f"Segmenting {file_path} . . .")

    # Loop through data to segment based on zero-crossings
    for i in range(1, len(data)):
        if not in_segment and aa_common.is_rising_from_zero(data[i:i + 8]):
            # Start of a new segment
            in_segment = True
            prev_start_index = i
            # print(f"Segment started at index {i}")

        if in_segment and is_rising_zero_crossing_seg(data, i):
            # End of the current segment
            wave_cycle = data[prev_start_index:i]
            if len(wave_cycle) >= min_segment_size:  # Only save segments with at least 64 samples
                segment_name = f"{base}_seg_{len(segment_sizes):04d}.wav"
                segment_sizes.append((segment_name, len(wave_cycle)))

                # Save the segment
                sf.write(os.path.join(seg_folder, segment_name), wave_cycle, samplerate)
                # print(f"Segment saved: {segment_name}, length: {len(wave_cycle)}")
            else:
                print(f"Skipped short segment at index {prev_start_index}: length={len(wave_cycle)}")
                continue
            # Prepare for the next segment
            in_segment = False

    # Handle any remaining data at the end of the file
    if in_segment and aa_common.is_rising_to_zero(data[prev_start_index:]):
        wave_cycle = data[prev_start_index:]
        if len(wave_cycle) >= min_segment_size:  # Only save segments with more than 64 samples
            segment_name = f"{base}_seg_{len(segment_sizes):04d}.wav"
            segment_sizes.append((segment_name, len(wave_cycle)))

            # Save the final segment
            sf.write(os.path.join(seg_folder, segment_name), wave_cycle, samplerate)
            # print(f"Final segment saved: {segment_name}, length: {len(wave_cycle)}")
        else:
            # print(f"Skipped saving final segment: too short (length={len(wave_cycle)})")
            pass
    print(f"Segmentation complete. Total segments: {len(segment_sizes)}")
    return segment_sizes

# Validation Process
def validate_all_segments(seg_folder):
    """
    Validate all the segments in the seg folder by checking if each segment starts
    and ends with a valid zero-crossing.
    """
    for segment_file in os.listdir(seg_folder):
        segment_path = os.path.join(seg_folder, segment_file)
        if segment_path.endswith(".wav"):
            if not check_segment_file(segment_path):
                # (f"Segment {segment_file} failed validation.")
                return False  # If any segment fails, return false

    print("All segments passed validation.")
    return True

def check_segment_file(segment_path):
    """Check if a given segment file is valid based on rising zero-crossings."""
    data, _ = sf.read(segment_path)

    # Check for rising from zero at the start
    if len(data) < 8:
        print(f"Segment {segment_path} is too short to validate.")
        return False

    if not aa_common.is_rising_from_zero(data[:8]):
        print(f"Segment {segment_path} failed: no valid rising-from-zero at the start.")
        return False

    # Check for rising to zero at the end
    if not aa_common.is_rising_to_zero(data[-8:]):
        print(f"Segment {segment_path} failed: no valid rising-to-zero at the end.")
        return False

    return True

def run(processed_files):
    """
    Process each file in the processed_files list to segment them and then validate the segments.
    """
    tmp_folder = aa_common.get_tmp_folder()
    seg_folder = os.path.join(tmp_folder, "seg")

    segment_sizes = []

    # Use the files from the src folder inside tmp
    for file_path in processed_files:
        full_path = os.path.normpath(os.path.join(tmp_folder, "src", os.path.basename(file_path)))
        new_segment_sizes = []

        if os.path.exists(full_path):
            new_segment_sizes = run_segment(full_path)

        # Track the segment sizes and sample counts
        for segment_name, sample_count in new_segment_sizes:
            aa_common.set_wavecycle_samples(segment_name, sample_count)

        segment_sizes.extend(new_segment_sizes)

    # Validate all the segments
    if not validate_all_segments(seg_folder):
        print("Segment validation failed. Please check the invalid segments.")

    # Store segment sizes for later use
    aa_common.set_all_segment_sizes(segment_sizes)
