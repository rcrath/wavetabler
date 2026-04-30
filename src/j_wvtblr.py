
# j_wvtblr.py

import os
import resampy
import numpy as np
import soundfile as sf
import math
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, SpanSelector
import re
from pathlib import Path
from struct import pack
import aa_common
from aa_common import add_serum_chunk


# Local default values for wavecycle size and frame count
wavecycle_size = 2048
frame_count = 256
WAVETABLE_SIZE = wavecycle_size * frame_count

# Consolidate into a single variable for total samples required (frame_count * wavecycle_size)
fixed_length = wavecycle_size * frame_count

selected_segment = None     # picked + fitted data, ready to write
selected_range = None       # (xmin_seconds, xmax_seconds) — set by SpanSelector

wavetables_folder = os.path.join(os.getcwd(), 'wavetables')
os.makedirs(wavetables_folder, exist_ok=True)


def fit_data_to_wavetable_size(data, sr):
    """
    Halve via resampy (when too long) / zero-pad (when too short) until data is
    exactly fixed_length samples. Same algorithm as create_wavetable_from_concat,
    extracted so the picker can reuse it on a user-selected range.
    """
    while len(data) > fixed_length:
        new_length = len(data) // 2
        data = resampy.resample(data, sr, sr // 2, axis=-1)[:new_length]
    if len(data) < fixed_length:
        return np.pad(data, (0, fixed_length - len(data)), 'constant', constant_values=(0, 0))
    if len(data) > fixed_length:
        return data[:fixed_length]
    return data

def pick_on_proceed(event, data, sr, base, suffix_two):
    """
    Apply the halve+pad fit to whatever range the user dragged out, then save.
    """
    global selected_range
    if selected_range is None:
        print("No range selected. Click and drag on the plot to select a range first.")
        return

    xmin, xmax = selected_range
    start = max(0, int(round(xmin * sr)))
    end = min(len(data), int(round(xmax * sr)))
    if end <= start:
        print("Empty range. Try dragging across a wider area.")
        return

    picked = data[start:end]
    fitted = fit_data_to_wavetable_size(picked, sr)
    print(f"Selected {end - start} samples → fitted to {fixed_length} ({len(fitted) - (end - start):+d} from pad/halve)")
    save_pick(fitted, sr, base, wavetables_folder, suffix_two)
    plt.close('all')


def pick_on_cancel(event):
    print("Selection canceled. No changes made.")
    plt.close('all')

def save_pick(segment_data, sr, base, wavetables_folder, _two):
    """
    Save the selected segment to the wavetables directory located at the top level.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(wavetables_folder, exist_ok=True)
    suffix_two = "pick"
    method_tag = aa_common.get_method_suffix()
    output_file = os.path.join(wavetables_folder, f"{base}{method_tag}_{timestamp}_{suffix_two}.wav")
    
    try:
        sf.write(output_file, segment_data, sr, subtype='FLOAT')
        
        # Add Serum-compatible chunk
        add_serum_chunk(Path(output_file))

        print(f"Saved selection to {output_file}")
        return True
    except Exception as e:
        print(f"Failed to save the selection: {e}")
        return False



def plot_concat(concat_file_path, fixed_length, sr, base, suffix_one):
    """
    Show the concatenated waveform and let the user click-and-drag to select a
    range. Any range works — fit_data_to_wavetable_size halves or pads to land
    on exactly fixed_length samples on save.
    """
    global selected_range
    selected_range = None  # Reset between channels

    data, sr = sf.read(concat_file_path)
    time = np.linspace(0, len(data) / sr, num=len(data))

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(time, data, label="Concatenated Wavetable")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Click and drag to select a range — Proceed to save, Cancel to abort")
    ax.legend(loc='upper right')

    ax_proceed = plt.axes([0.7, 0.01, 0.1, 0.05])
    ax_cancel = plt.axes([0.81, 0.01, 0.1, 0.05])
    btn_proceed = Button(ax_proceed, 'Proceed')
    btn_cancel = Button(ax_cancel, 'Cancel')

    btn_proceed.on_clicked(lambda event: pick_on_proceed(event, data, sr, base, suffix_one))
    btn_cancel.on_clicked(pick_on_cancel)

    def on_select(xmin, xmax):
        global selected_range
        if xmax <= xmin:
            return
        selected_range = (xmin, xmax)
        n = int(round((xmax - xmin) * sr))
        print(f"Range: {xmin:.3f}s – {xmax:.3f}s  ({n} samples — will be {'halved' if n > fixed_length else 'padded'} to {fixed_length})")

    # SpanSelector keeps a reference attached to the axes; assign so it's not GC'd.
    span = SpanSelector(
        ax, on_select, 'horizontal',
        useblit=True,
        props=dict(alpha=0.3, facecolor='orange'),
        interactive=True,
    )
    fig._span_selector_ref = span  # prevent GC of the widget

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
    concat_data, sr = sf.read(concat_file_path)
    fitted = fit_data_to_wavetable_size(concat_data, sr)
    sf.write(output_wavetable_path, fitted, sr, subtype='FLOAT')
    add_serum_chunk(Path(output_wavetable_path))


def split_and_save_wav_with_correct_padding(data, output_folder, base_name, suffix_one, timestamp):
    sr = 192000
    segment_length = len(data)
    num_frames_per_file = 2048 * 256

    num_full_files = segment_length // num_frames_per_file
    for i in range(num_full_files):
        counter = f"{i+1:02d}"
        start_sample = i * num_frames_per_file
        end_sample = start_sample + num_frames_per_file
        segment = data[start_sample:end_sample]
        output_file_name = f"{base_name}_{timestamp}{suffix_one}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)

        sf.write(output_file_path, segment, sr, subtype='FLOAT')
        add_serum_chunk(Path(output_file_path))

    remainder = segment_length % num_frames_per_file
    if remainder > 0:
        padding_needed = num_frames_per_file - remainder
        last_segment = np.concatenate([data[-remainder:], np.zeros(padding_needed)])
        counter = f"{num_full_files + 1:02d}"
        output_file_name = f"{base_name}_{timestamp}{suffix_one}_{counter}.wav"
        output_file_path = os.path.join(output_folder, output_file_name)

        sf.write(output_file_path, last_segment, sr, subtype='FLOAT')
        add_serum_chunk(Path(output_file_path))

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

    # Capture run start so we can identify which wavetables were saved this run,
    # vs leftovers from previous runs in the same wavetables folder.
    run_start_ts = datetime.now().timestamp()

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
    method_tag = aa_common.get_method_suffix()  # '_z' or '_a' — identifies segmentation method in filename
    aa_common.clear_screen()
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
                wavetables_folder, f"{base}_{channel_name}{method_tag}_{timestamp}{suffix_one}.wav"
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
                f"{base}_{channel_name}{method_tag}",
                suffix_one,
                timestamp,
            )

    if 3 in selected_options:
        suffix_one = "_pick"
        # Picker UI: plot_concat blocks until the user clicks Proceed (which
        # triggers save_pick via pick_on_proceed) or Cancel. The picker now
        # handles any selection length via fit_data_to_wavetable_size, so it
        # works on short concat files too.
        for channel_name, concat_file_path in concatenated_files.items():
            plot_concat(
                concat_file_path,
                fixed_length=fixed_length,
                sr=sr_frames,
                base=f"{base}_{channel_name}",
                suffix_one=suffix_one,
            )

    if not selected_options & {1, 2, 3}:
        print("Invalid option(s)")

    # Validate and check generated wavetables
    for wav_file in os.listdir(wavetables_folder):
        if wav_file.endswith('.wav'):
            file_path = os.path.join(wavetables_folder, wav_file)
            check_wavetable(file_path)

    # Report what was saved THIS run (mtime >= run_start_ts) so leftovers from
    # earlier runs in the same folder don't get listed.
    saved_this_run = sorted(
        f for f in os.listdir(wavetables_folder)
        if f.endswith('.wav')
        and os.path.getmtime(os.path.join(wavetables_folder, f)) >= run_start_ts
    )
    print(f"\nWavetables saved to: {wavetables_folder}")
    if saved_this_run:
        for f in saved_this_run:
            print(f"  {f}")
    else:
        print("  (no wavetables produced)")
    print()
