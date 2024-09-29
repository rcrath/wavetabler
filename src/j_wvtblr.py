# j_wvtblr.py

import os
import resampy
import numpy as np
import soundfile as sf
import math
from datetime import datetime
import matplotlib.pyplot as plt
import aa_common  # Import aa_common to access all functions and globals
import re

# Ensure that wavecycle_size = 2048 and frame_count = 256 are defined in aa_common
wavecycle_size = aa_common.wavecycle_size
frame_count = aa_common.frame_count

# Consolidate into a single variable for total samples required (frame_count * wavecycle_size)
fixed_length = wavecycle_size * frame_count


selected_segment = None

# Functions
def concatenate_files(input_folder, output_file):
    all_frames = []
    for filename in sorted(os.listdir(input_folder)):
        if filename.endswith('.wav'):
            file_path = os.path.join(input_folder, filename)
            data, sr = sf.read(file_path)
            all_frames.append(data)
    
    if all_frames:
        wavetable_data = np.concatenate(all_frames, axis=0)
        sf.write(output_file, wavetable_data, sr, subtype='FLOAT')
        return output_file, sr
    else:
        raise ValueError("No valid .wav files found for concatenation.")

def apply_padding_if_needed(data, target_length, amplitude_tolerance_db):
    """Apply padding to the data if it's shorter than the target length."""
    current_length = len(data)
    if current_length < target_length:
        needed_samples = target_length - current_length
        padding = generate_drunken_walk(needed_samples, amplitude_tolerance_db)
        data_with_padding = np.concatenate([data, padding])
    else:
        data_with_padding = data
    return data_with_padding

def generate_drunken_walk(length, amplitude_db):
    """Generate a 'drunken walk' signal with a specified amplitude in dB."""
    # Convert amplitude from dB to a linear scale
    linear_amplitude = 10 ** (amplitude_db / 20.0)
    
    # Generate random steps, then perform a cumulative sum to simulate a 'walk'
    steps = np.random.uniform(low=-linear_amplitude, high=linear_amplitude, size=length)
    drunken_walk = np.cumsum(steps)
    
    # Ensure the signal stays within the desired amplitude range
    drunken_walk = np.clip(drunken_walk, -linear_amplitude, linear_amplitude)
    
    return drunken_walk

def process_and_pad_wavetables(concat_file_path, output_folder, output_base_name):
    # Read the concatenated file
    data, sr = sf.read(concat_file_path)

    # If the concatenated file is shorter than 2048*256 samples, pad it
    data_padded = apply_padding_if_needed(data, fixed_length, amplitude_tolerance_db=-60)

    # Save the processed wavetable
    output_file_path = os.path.join(output_folder, f"{output_base_name}_wavetable.wav")
    sf.write(output_file_path, data_padded, sr, subtype='FLOAT')
    # print(f"Wavetable saved to {output_file_path} with {len(data_padded)} samples.")

def create_wavetable_from_concat(concat_file_path, output_wavetable_path):
    frame_length = 2048
    total_frames = 256
    total_samples_required = frame_length * total_frames

    # Load the concat file
    concat_data, sr = sf.read(concat_file_path)

    # General case: Keep halving the number of samples per wavecycle until it fits
    while len(concat_data) > total_samples_required:
        new_length = len(concat_data) // 2
        concat_data = resampy.resample(concat_data, sr, sr // 2, axis=-1)[:new_length]
    
    # Ensure the result is exactly 2048 * 256 samples long
    if len(concat_data) < total_samples_required:
        # Pad with silence if shorter
        padded_data = np.pad(concat_data, (0, total_samples_required - len(concat_data)), 'constant', constant_values=(0, 0))
    elif len(concat_data) > total_samples_required:
        # Truncate if longer (shouldn't happen with the above loop, but just in case)
        padded_data = concat_data[:total_samples_required]
    else:
        padded_data = concat_data

    # Save the padded data as the final wavetable
    sf.write(output_wavetable_path, padded_data, sr, subtype='FLOAT')
    # print(f"Wavetable saved to {output_wavetable_path} with {len(padded_data)} samples.")

def split_and_save_wav_with_correct_padding(data, output_folder, base_name, timestamp, wavetable_type):
    sr = 192000  # Assuming a fixed sample rate, adjust as needed
    segment_length = len(data)
    num_frames_per_file = 2048 * 256  # Serum-compatible wavetable size (524288 samples per file)
    
    # Calculate the number of full wavetable files that can be created
    num_full_files = segment_length // num_frames_per_file

    # Process each full file
    for i in range(num_full_files):
        counter = f"{i+1:02d}"  # Create a 2-digit counter starting from 01
        start_sample = i * num_frames_per_file
        end_sample = start_sample + num_frames_per_file
        segment = data[start_sample:end_sample]
        output_file_name = f"{base_name}_{timestamp}_{wavetable_type}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)
        sf.write(output_file_path, segment, sr, subtype='FLOAT')  # Save the chunk

    # Handle the last segment if there's a remainder, ensuring it also becomes 524288 samples long
    remainder = segment_length % num_frames_per_file
    if remainder > 0:
        # Pad only the remainder to make it a full file
        padding_needed = num_frames_per_file - remainder
        last_segment = np.concatenate([data[-remainder:], np.zeros(padding_needed)])  # Pad the last chunk
        counter = f"{num_full_files+1:02d}"  # Increment counter for the padded last chunk
        output_file_name = f"{base_name}_{timestamp}_{wavetable_type}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)
        sf.write(output_file_path, last_segment, sr, subtype='FLOAT')  # Save the padded last chunk

# Function to save the selected segment
def save_pick(data, sr, base, base_folder, suffix):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(base_folder, exist_ok=True)
    output_file = os.path.join(base_folder, f"{base}_{timestamp}_{suffix}.wav")
    sf.write(output_file, data, sr, subtype='FLOAT')
    print(f"Saved selection to {output_file}")


def check_wavetable(file_path):
    """Checks if the wavetable has the correct total length and every 2048th sample is near zero and rising."""
    data, sr = sf.read(file_path)
    total_samples_required = wavecycle_size * frame_count
    # Total samples check
    if len(data) != total_samples_required:
        print(f"Error: {os.path.basename(file_path)} has {len(data)} samples, expected {total_samples_required} samples.")
        return False

    # Check every 2048th sample
    for i in range(wavecycle_size, total_samples_required, wavecycle_size):
        sample_value = data[i]
        prev_sample_value = data[i - 1]

        # Ensure the sample is within -40 dB of zero
        if 20 * np.log10(max(abs(sample_value), 1e-10)) > -40:
            # print(f"Error: In file {os.path.basename(file_path)}, sample {i} is not within -40 dB of zero. Value: {sample_value}")
            pass
            return False

        # Ensure it's a rising zero-crossing
        if sample_value <= prev_sample_value:
            # print(f"Error: In file {os.path.basename(file_path)}, sample {i} is not rising. Current value: {sample_value}, Previous value: {prev_sample_value}")
            pass
            return False

    # print(f"{os.path.basename(file_path)} passed all tests.")
    pass
    return True

def run(atk_deleted, dev_deleted, normal_deleted):
    global selected_segment
    base = aa_common.get_base()
    tmp_folder = aa_common.get_tmp_folder()
    seg_folder = os.path.join(tmp_folder, 'seg')  # Adjusted to use seg_folder

    # Check and create the "wavetables" folder in the working directory
    wavetables_folder = os.path.join(os.getcwd(), 'wavetables')  # Create `wavetables` in the top-level directory
    os.makedirs(wavetables_folder, exist_ok=True)

    frames_folder = os.path.join(tmp_folder, 'frames')
    concat_folder = os.path.join(tmp_folder, 'concat')
    os.makedirs(concat_folder, exist_ok=True)
    
    output_file_frames = f"{base}_frames_all.wav"
    output_path_frames = os.path.join(concat_folder, output_file_frames)

    # Ensure correct reference to frames_folder
    output_path_frames, sr_frames = concatenate_files(frames_folder, output_path_frames)

    # Add suffix based on deletion choices
    suffix = ""
    if atk_deleted:
        suffix += "_-atk"
    if dev_deleted:
        suffix += "_-dev"
    if normal_deleted:
        suffix += "_-norm"

    # Generate the timestamp for file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # "fit" as the default (option 1)
    options = aa_common.input_with_defaults("Choose wavetable creation method (you can choose multiple, e.g., 1,2 or 1-3):\n"
                    "1. Fit whole within 256*frames divisible by 2048 samples (default)\n"
                    "2. Arbitrarily cut into chunks\n"
                    "3. Select and save\n"
                    "Press Enter to select option 1: ").strip()

    # Set default to "1" if the input is empty or invalid
    if not options or not re.match(r'^[1-3, -]+$', options):
        options = "1"  # Set default to Fit

    # Parse user input
    selected_options = set()
    for part in options.split(','):
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                selected_options.update(range(start, end + 1))
            except ValueError:
                continue  # Skip any invalid range input
        else:
            try:
                selected_options.add(int(part))
            except ValueError:
                continue  # Skip any invalid single number input


    # Process each selected option
    # Fit (now option 1)
    if 1 in selected_options:
        fitted_wavetable_path = os.path.join(wavetables_folder, f"{base}{suffix}_{timestamp}_fit.wav")
        create_wavetable_from_concat(output_path_frames, fitted_wavetable_path)

    # Chop (option 2: arbitrarily cut into chunks)
    if 2 in selected_options:
        timestamp_state = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load the concatenated frames file
        data_frames, sr_frames = sf.read(output_path_frames, dtype='float32')

        # Apply padding in memory if necessary, but do not write this padded file out
        data_frames_padded = apply_padding_if_needed(data_frames, fixed_length, -60)

        # Calculate the number of full chunked files
        num_full_files_frames = math.ceil(len(data_frames_padded) / fixed_length)

        # Split and save chunks (fixed-length files) to the wavetables folder
        split_and_save_wav_with_correct_padding(data_frames_padded, wavetables_folder, f"{base}{suffix}", timestamp_state, "chunk")


        print(f"File split and saved into wavetables starting at beginning: {wavetables_folder}")

    # Select and Save (now option 3)
    if 3 in selected_options:
        selection_made = False
        while not selection_made:
            aa_common.plot_wav_file_interactive(output_path_frames, fixed_length=fixed_length)  # Pass fixed_length here
            if aa_common.selected_segment is not None:
                save_pick(aa_common.selected_segment, sr_frames, f"{base}{suffix}", wavetables_folder, "pick")
                selection_made = True
            else:
                continue

    # Handle invalid options
    if not selected_options & {1, 2, 3}:
        print("Invalid option(s)")

    # Loop through all .wav files in the wavetables folder and check each one
    for wav_file in os.listdir(wavetables_folder):
        if wav_file.endswith('.wav'):
            file_path = os.path.join(wavetables_folder, wav_file)
            check_wavetable(file_path)

    print(f"\nYour wavetables are in {wavetables_folder}\n")
