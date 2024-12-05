
# j_wvtblr.py

import os
import resampy
import numpy as np
import soundfile as sf
import math
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import re

# Local default values for wavecycle size and frame count
wavecycle_size = 2048
frame_count = 256
WAVETABLE_SIZE = wavecycle_size * frame_count

# Consolidate into a single variable for total samples required (frame_count * wavecycle_size)
fixed_length = wavecycle_size * frame_count

selected_segment = None

wavetables_folder = os.path.join(os.getcwd(), 'wavetables')
os.makedirs(wavetables_folder, exist_ok=True)

# Functions
def pick_on_click(event, data, sr, fig, ax, total_samples, fixed_length, wavecycle_size):
    global selected_segment  # Store the selected segment globally for later use

    if event.inaxes != ax:
        return  # Ignore clicks outside the plot

    clicked_sample_index = int(event.xdata * sr)

    # If the file is smaller than fixed_length, pad with a drunken walk
    if total_samples < fixed_length:
        print(f"File is too short: {total_samples} samples. Padding to {fixed_length} samples.")
        padding = generate_drunken_walk(fixed_length - total_samples, amplitude_db=-60)
        selected_segment = np.concatenate([data, padding])
        return

    # Handle clicks near the start of the graph (select the first fixed_length samples)
    if clicked_sample_index < wavecycle_size / 2:
        nearest_interval = 0
        selected_segment = data[:fixed_length]
        print(f"Selected the first {fixed_length} samples.")
    
    # Handle clicks near the end of the graph (select the last fixed_length samples)
    elif clicked_sample_index > total_samples - fixed_length:
        nearest_interval = total_samples - fixed_length
        selected_segment = data[nearest_interval:]
        print(f"Selected the last {fixed_length} samples.")
    
    # Handle clicks inside the graph (move to the nearest wavecycle interval)
    else:
        nearest_interval = int(round(clicked_sample_index / wavecycle_size)) * wavecycle_size
        if nearest_interval + fixed_length > total_samples:
            nearest_interval = total_samples - fixed_length  # Shift to make sure it doesn't overflow
        selected_segment = data[nearest_interval:nearest_interval + fixed_length]
        print(f"Selected samples from {nearest_interval} to {nearest_interval + fixed_length}.")

    # Remove previous highlights and update the graph
    while len(ax.lines) > 1:
        ax.lines[-1].remove()  # Remove the last line

    # Highlight the new selected segment
    highlight_time = np.linspace(nearest_interval / sr, (nearest_interval + fixed_length) / sr, fixed_length)
    ax.plot(highlight_time, selected_segment[:fixed_length], color='orange', label="Selected Segment", linewidth=2)
    ax.legend()
    fig.canvas.draw()


def pick_on_proceed(event, data, sr, base, concat_folder, suffix_two):
    global selected_segment

    if selected_segment is not None:
        # Save the selected segment
        save_pick(selected_segment, sr, base, wavetables_folder, suffix_two)
        print(f"Proceeding with the selected segment.")
        plt.close('all')  # Close the plot after saving
    else:
        print("No segment selected. Proceeding without saving.")
        plt.close('all')


def pick_on_cancel(event):
    print("Selection canceled. No changes made.")
    plt.close('all')  # Close the plot

def save_pick(segment_data, sr, base, wavetables_folder, _two):
    """
    Save the selected segment to the wavetables directory located at the top level.
    
    Parameters:
    - segment_data: Numpy array of the selected audio segment.
    - sr: Sample rate.
    - base: Base name for the file.
    - wavetables_folder: The folder where the wavetable file should be saved.
    - suffix: Additional suffix for the filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(wavetables_folder, exist_ok=True)  # Ensure wavetables folder exists
    suffix_two = "pick"
    output_file = os.path.join(wavetables_folder, f"{base}_{timestamp}_{suffix_two}.wav")
    
    try:
        sf.write(output_file, segment_data, sr, subtype='FLOAT')
        print(f"Saved selection to {output_file}")
        return True
    except Exception as e:
        print(f"Failed to save the selection: {e}")
        return False


def plot_concat(concat_file_path, fixed_length, sr, base, concat_folder, suffix_one):
    global selected_segment  # Global to store the selected segment
    
    data, sr = sf.read(concat_file_path)
    total_samples = len(data)
    time = np.linspace(0, len(data) / sr, num=len(data))

    fig, ax = plt.subplots(figsize=(15, 5))

    # Plot the full data waveform
    ax.plot(time, data, label="Concatenated Wavetable")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Select a Segment (Nearest 524,288 Samples)")
    ax.legend()

    # Add Proceed and Cancel buttons
    ax_proceed = plt.axes([0.7, 0.01, 0.1, 0.05])
    ax_cancel = plt.axes([0.81, 0.01, 0.1, 0.05])
    btn_proceed = Button(ax_proceed, 'Proceed')
    btn_cancel = Button(ax_cancel, 'Cancel')

    # Button actions
    btn_proceed.on_clicked(lambda event: pick_on_proceed(event, data, sr, base, concat_folder, suffix_one))
    btn_cancel.on_clicked(pick_on_cancel)

    # Connect the click event for segment selection
    fig.canvas.mpl_connect('button_press_event', lambda event: pick_on_click(event, data, sr, fig, ax, total_samples, fixed_length, wavecycle_size))

    plt.show()


    # Event handler for clicks
    def on_click(event):
        global selected_segment
        if event.inaxes != ax:
            # Click outside the plot area
            # Determine if it's near the start or end
            if event.xdata < 0.1 * time[-1]:
                selected_segment = data[:fixed_length]
                print("Selected the first 524,288 samples.")
            elif event.xdata > 0.9 * time[-1]:
                selected_segment = data[-fixed_length:]
                print("Selected the last 524,288 samples.")
            else:
                # Round to the nearest 524,288 interval
                nearest_index = int(round(event.xdata * sr / fixed_length)) * fixed_length
                nearest_index = max(0, min(nearest_index, total_samples - fixed_length))
                selected_segment = data[nearest_index:nearest_index + fixed_length]
                print(f"Selected samples from {nearest_index} to {nearest_index + fixed_length}.")
        else:
            # Click inside the plot area
            sample_index = int(event.xdata * sr)
            nearest_interval = int(round(sample_index / fixed_length)) * fixed_length
            if nearest_interval < fixed_length / 2:
                nearest_interval = 0
            elif nearest_interval > total_samples - fixed_length / 2:
                nearest_interval = total_samples - fixed_length
            else:
                # Ensure it's aligned to the 524,288 interval
                nearest_interval = int(round(nearest_interval / fixed_length)) * fixed_length

            # Clamp the index to valid range
            nearest_interval = max(0, min(nearest_interval, total_samples - fixed_length))
            selected_segment = data[nearest_interval:nearest_interval + fixed_length]
            print(f"Selected samples from {nearest_interval} to {nearest_interval + fixed_length}.")

        # Highlight the selected segment
        while len(ax.lines) > 1:
            ax.lines.pop()  # Remove previous highlights, keeping the original plot line
        segment_time = np.linspace(0, fixed_length / sr, num=fixed_length)
        if data.ndim == 2:
            ax.plot(segment_time, selected_segment[:, 0], color='orange', label="Selected Left Channel", linewidth=2)
            ax.plot(segment_time, selected_segment[:, 1], color='orange', label="Selected Right Channel", linewidth=2)
        else:
            ax.plot(segment_time, selected_segment, color='orange', label="Selected Segment", linewidth=2)
        ax.legend()
        fig.canvas.draw()

    # Button event handlers
    def on_proceed_clicked(event):
        global selected_segment
        if selected_segment is not None:
            success = save_pick(selected_segment, sr, concat_file_path)
            if success:
                plt.close(fig)
                print("Proceeding with the selected segment.")
            else:
                print("Failed to save the selection.")
        else:
            print("No segment selected. Please select a segment first.")

    def on_cancel_clicked(event):
        global selected_segment
        selected_segment = None
        plt.close(fig)
        print("Selection canceled. Proceeding with the full waveform.")

    # Connect the events
    fig.canvas.mpl_connect('button_press_event', on_click)
    btn_proceed.on_clicked(on_proceed_clicked)
    btn_cancel.on_clicked(on_cancel_clicked)

    plt.show()

def concatenate_files(frames_folder, base, from_frames, channel_files, concat_folder):
    # Check if there are any files to concatenate
    if not from_frames or not channel_files:
        print("No frame files found to concatenate.")
        return None

    concatenated_files = {}
    sample_rate = None

    # Iterate over each channel and concatenate the corresponding files
    for channel_name, file_path in channel_files.items():
        data_list = []

        # Get all frame files for the current channel
        matching_files = [file for file in from_frames if channel_name in file]
        matching_files.sort()  # Sort files to maintain the correct order

        for file in matching_files:
            data, sr = sf.read(file, dtype='float32')
            if sample_rate is None:
                sample_rate = sr  # Set the sample rate from the first file
            data_list.append(data)

        # Concatenate the data arrays for the current channel
        concatenated_data = np.concatenate(data_list)
        
        # Define the output path for the concatenated file
        output_file_path = os.path.join(concat_folder, f"{base}_{channel_name}.wav")
        sf.write(output_file_path, concatenated_data, sample_rate)
        concatenated_files[channel_name] = output_file_path

    return concatenated_files, sample_rate

def regex_channel_files(frames_folder, base):
    from_frames = []  # List to store all matching frame file paths
    channel_files = {}  # Dictionary to store file paths by channel name

    # Define a regex pattern to match the filenames
    pattern = re.compile(rf"^{re.escape(base)}(_Mid|_Side|_Left|_Right|_Mono)_seg_\d{{4}}\w*\.wav$")

    # Iterate through the files in the frames folder
    for file_name in os.listdir(frames_folder):
        if pattern.match(file_name):
            # Construct the full file path
            file_path = os.path.join(frames_folder, file_name)
            from_frames.append(file_path)

            # Extract the channel name from the filename
            channel_name_match = re.search(r"_(Mid|Side|Left|Right|Mono)", file_name)
            if channel_name_match:
                channel_name = channel_name_match.group(1)
                channel_files[channel_name] = file_path

    # Ensure that from_frames and channel_files are valid
    if not from_frames or not channel_files:
        print("No matching frame files found in the frames folder.")
        return None, None

    return from_frames, channel_files


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
    linear_amplitude = 10 ** (amplitude_db / 20.0)
    steps = np.random.uniform(low=-linear_amplitude, high=linear_amplitude, size=length)
    drunken_walk = np.cumsum(steps)
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

def split_and_save_wav_with_correct_padding(data, output_folder, base_name, suffix_one, timestamp, wavetable_type):

    sr = 192000
    segment_length = len(data)
    num_frames_per_file = 2048 * 256

    # Calculate the number of full wavetable files that can be created
    num_full_files = segment_length // num_frames_per_file

    for i in range(num_full_files):
        counter = f"{i+1:02d}"
        start_sample = i * num_frames_per_file
        end_sample = start_sample + num_frames_per_file
        segment = data[start_sample:end_sample]
        output_file_name = f"{base_name}_{timestamp}{suffix_one}_{wavetable_type}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)
        sf.write(output_file_path, segment, sr, subtype='FLOAT')

    remainder = segment_length % num_frames_per_file
    if remainder > 0:
        padding_needed = num_frames_per_file - remainder
        last_segment = np.concatenate([data[-remainder:], np.zeros(padding_needed)])
        counter = f"{num_full_files + 1:02d}"
        output_file_name = f"{base_name}_{timestamp}{suffix_one}_{wavetable_type}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)
        sf.write(output_file_path, last_segment, sr, subtype='FLOAT')
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
            return False

        # Ensure it's a rising zero-crossing
        if sample_value <= prev_sample_value:
            return False

    return True

def run(atk_deleted, dev_deleted, normal_deleted):
    from aa_common import get_base, get_tmp_folder, input_with_defaults
    
    tmp_folder = get_tmp_folder()
    frames_folder = os.path.join(tmp_folder, "frames")
    concat_folder = os.path.join(tmp_folder, "concat")
    base = get_base()

    print(f"frames_folder: {frames_folder}")
    print(f"concat_folder: {concat_folder}")
    print(f"base: {base}")

    # Collect frame files and channel-specific file paths
    from_frames, channel_files = regex_channel_files(frames_folder, base)

    if not from_frames or not channel_files:
        print("No matching frame files found or no channel files identified.")
        return

    print(f"channel_files: {channel_files}")

    # Call concatenate_files to process and group files by channel
    concatenated_files, sr_frames = concatenate_files(frames_folder, base, from_frames, channel_files, concat_folder)

    if not concatenated_files:
        print("No concatenated files were created.")
        return

    print(f"Concatenated files: {concatenated_files}")

    # Proceed with wavetable creation options
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    options = input_with_defaults(
        "Choose wavetable creation method (you can choose multiple, e.g., 1,2 or 1-3):\n"
        "1. Fit whole within 256*frames divisible by 2048 samples (default)\n"
        "2. Arbitrarily cut into chunks\n"
        "3. Select and save\n"
        "Press Enter to select option 1: ").strip()

    if not options or not re.match(r'^[1-3, -]+$', options):
        options = "1"

    selected_options = set()
    for part in options.split(','):
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                selected_options.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                selected_options.add(int(part))
            except ValueError:
                continue

    suffix_one = "_fit"
    if 1 in selected_options:
        # Process each channel's concatenated file for option 1
        for channel_name, concat_file_path in concatenated_files.items():
            fitted_wavetable_path = os.path.join(
                wavetables_folder, f"{base}_{channel_name}_{timestamp}{suffix_one}.wav"
            )
            create_wavetable_from_concat(concat_file_path, fitted_wavetable_path)

    if 2 in selected_options:
        suffix_one = "_chunk"
        # Process each channel's concatenated file for option 2
        for channel_name, concat_file_path in concatenated_files.items():
            data_frames, sr_frames = sf.read(concat_file_path, dtype='float32')
            data_frames_padded = apply_padding_if_needed(data_frames, fixed_length, -60)
            split_and_save_wav_with_correct_padding(
                data_frames_padded,
                wavetables_folder,
                f"{base}_{channel_name}",
                suffix_one,
                timestamp,
                "chunk"
            )

    if 3 in selected_options:
        suffix_one = "_pick"
        # Process each channel's concatenated file for option 3
        for channel_name, concat_file_path in concatenated_files.items():
            plot_concat(
                concat_file_path,
                fixed_length=fixed_length,
                sr=sr_frames,
                base=f"{base}_{channel_name}",
                suffix_one=suffix_one
            )

            picked_wavetable_path = os.path.join(
                wavetables_folder, f"{base}_{channel_name}_{timestamp}{suffix_one}.wav"
            )

            # Save picked segment if selected
            if selected_segment is not None:
                save_pick(
                    selected_segment,
                    sr_frames,
                    f"{base}_{channel_name}_{timestamp}{suffix_one}",
                    wavetables_folder,
                    "pick"
                )
                print(f"Saved selection to: {picked_wavetable_path}")
                print("Proceeding with the selected segment.")

            # Reset `selected_segment` after processing
            selected_segment = None

    if not selected_options & {1, 2, 3}:
        print("Invalid option(s)")

    # Validate and check generated wavetables
    for wav_file in os.listdir(wavetables_folder):
        if wav_file.endswith('.wav'):
            file_path = os.path.join(wavetables_folder, wav_file)
            check_wavetable(file_path)

    print(f"\nYour wavetables are in {wavetables_folder}\n")
