import os
import aa_common
import numpy as np
import soundfile as sf
import resampy
from scipy.signal import butter, filtfilt


def load_audio(file_path):
    """Function to load audio data from a file."""
    data, sample_rate = sf.read(file_path)
    return data, sample_rate

def save_audio(file_path, data, sample_rate):
    # print("Entering save_audio")
    # print(f"File path: {file_path}")
    # print(f"Audio data type: {type(audio_data)}, Shape: {audio_data.shape}")
    # print(f"Sample rate: {sample_rate}")
    # breakpoint()  # Inspect before saving
    """
    Save the audio data to a specified file path with the given sample rate.
    
    Parameters:
    - file_path: str, the path to save the audio file.
    - data: np.ndarray, the audio data to save.
    - sample_rate: int, the sample rate of the audio data.
    """
    sf.write(file_path, data, sample_rate, subtype='FLOAT')
    # print(f"File saved: {file_path}")
    # print(sf.info(file_path))  # Confirm file properties after saving
    # breakpoint()  # Inspect saved file

def cleanup_files(file_paths, selected_files):
    """
    Delete files that were not selected for further processing.
    
    Parameters:
    - file_paths: dict, dictionary of all channel file paths.
    - selected_files: dict, dictionary of selected file paths.
    """
    for name, path in selected_files.items():
        print(f"Proceed with {path}")

def extract_channels(data):
    """
    Extract channels from audio data (already loaded).
    
    Parameters:
    - data: np.ndarray, audio data loaded with soundfile or another library.
    
    Returns:
    - dict, channels extracted as numpy arrays.
    """
    # Check if the data is stereo
    if data.ndim == 2 and data.shape[1] == 2:  # Stereo file
        # Extract Left and Right channels
        left = data[:, 0]
        right = data[:, 1]
        mid = (left + right) / 2
        side = (left - right) / 2

        print(f"Stereo detected: Left channel length: {len(left)}, Right channel length: {len(right)}")
        print(f"Mid channel length: {len(mid)}, Side channel length: {len(side)}")
        # print("inside extract_channels after stereo detector")

        return {
            'Left': left,
            'Right': right,
            'Mid': mid,
            'Side': side
        }
    elif data.ndim == 1:  # Mono file
        print(f"Mono detected: Channel length: {len(data)}")
        return {'Mono': data}
    else:
        raise ValueError("Unsupported audio format: Expected 1D (mono) or 2D (stereo) data.")


def save_channel_files(channels, sample_rate, base, tmp_folder):
    file_paths = {}
    for name, channel_data in channels.items():
        # print(f"Processing channel: {name}, Data shape: {channel_data.shape}")
        filtered_channel_data = high_pass_filter(channel_data, sample_rate)
        # print("DC Bias removed")
        file_name = f"{base}_{name}.wav"
        file_path = os.path.join(tmp_folder, file_name)
        sf.write(file_path, filtered_channel_data, sample_rate, subtype='FLOAT')
        file_paths[name] = file_path
    return file_paths


def parse_channel_selection(selections, total_channels):
    """Parse mixed range and comma input like '1-2,4'. Returns sorted 0-based indices, or None on error."""
    selected_indices = set()
    try:
        for part in selections.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                start, end = map(int, part.split('-'))
                selected_indices.update(range(start - 1, end))
            else:
                selected_indices.add(int(part) - 1)
    except (ValueError, IndexError) as e:
        print(f"Error parsing selection: {e}. Use format: 1 or 1,3 or 1-2 or 1-2,4")
        return None

    selected_indices = {i for i in selected_indices if 0 <= i < total_channels}
    if not selected_indices:
        return None
    return sorted(selected_indices)


def choose_channels(file_paths):
    """
    Select channels to proceed with. Supports defaults for 'Mid' or 'Mono' channels.

    Parameters:
    - file_paths: dict, mapping channel names to file paths.

    Returns:
    - dict, selected channels.
    """
    # Check if the file is mono
    if 'Mono' in file_paths:
        # If mono, skip the menu and proceed directly with the mono channel
        print(f"Proceed with Mono channel: {file_paths['Mono']}")
        return {'Mono': file_paths['Mono']}

    # Reorder channels for stereo files: "Mid", "Side", "Left", "Right"
    ordered_channels = []
    if 'Mid' in file_paths:
        ordered_channels.append('Mid')
    if 'Side' in file_paths:
        ordered_channels.append('Side')
    if 'Left' in file_paths:
        ordered_channels.append('Left')
    if 'Right' in file_paths:
        ordered_channels.append('Right')

    aa_common.clear_screen()
    print("\nAvailable channels:")
    for i, name in enumerate(ordered_channels, start=1):
        print(f"{i}. {name} ({os.path.basename(file_paths[name])})")

    while True:
        selections = aa_common.input_with_defaults(
            "\nEnter the numbers of the channels to proceed with (e.g., 1, 1,3, 1-2, or 1-2,4 — default=1): ",
            default="1"
        ).strip()

        selected_indices = parse_channel_selection(selections, len(ordered_channels))
        if selected_indices is not None:
            selected_channels = [ordered_channels[i] for i in selected_indices]
            print(f"Selected channels: {', '.join(selected_channels)}")
            return {name: file_paths[name] for name in selected_channels}
        print("Invalid selection. Please try again.")


def high_pass_filter(data, sample_rate, cutoff_freq=10):
    """
    Apply a Butterworth high-pass filter to remove DC offset.
    
    Parameters:
    - data: np.ndarray, the input audio data (mono).
    - sample_rate: int, the sample rate of the audio data.
    - cutoff_freq: float, the cutoff frequency for the high-pass filter (default 10 Hz).
    
    Returns:
    - np.ndarray, the filtered audio data.
    """
    nyquist = 0.5 * sample_rate
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(N=4, Wn=normal_cutoff, btype='high', analog=False)
    # print(f"Signal length: {len(data)}")
    # print(f"Signal contains NaN: {np.isnan(data).any()}")
    # print(f"Signal contains Inf: {np.isinf(data).any()}")
    # print(f"Signal shape: {data.shape}")
    return filtfilt(b, a, data).astype(np.float32)

def run():

    # print("Running cc_channels")
    tmp_folder = aa_common.get_tmp_folder()
    base = aa_common.get_base()
    # Update the file path to use the cpy folder

    cpy_folder = os.path.join(tmp_folder, "cpy")
    if not os.path.exists(cpy_folder):
        os.makedirs(cpy_folder)  # Ensure the cpy folder exists
    # Adjust cpy_file to point to the cpy folder
    cpy_file = os.path.join(tmp_folder, "cpy", f"{base}.wav")
    # print(sf.info(cpy_file))
    # breakpoint()
    # Load the waveform and sample rate from the input file
    cpy_file_data, sample_rate = sf.read(cpy_file)
    # print(f"Initial cpy file: {cpy_file}, Shape: {cpy_file_data.shape}, Sample rate: {sample_rate}")
    # breakpoint()
    # Extract channels
    channels = extract_channels(cpy_file_data)
    # print(f"after extract_channels: {cpy_file}, Shape: {cpy_file_data.shape}, Sample rate: {sample_rate}")
    # breakpoint()

    channel_files = save_channel_files(channels, sample_rate, base, cpy_folder)
    # print(f"after save_channel_files: {cpy_file}, Shape: {cpy_file_data.shape}, Sample rate: {sample_rate}")
    # breakpoint()

    # Choose channels to proceed with
    selected_channels = choose_channels(channel_files)

    # List to store the paths of processed files
    processed_files = []

    # Process each selected channel
    for name, channel_path in selected_channels.items():
        # Load the waveform and sample rate from the selected channel file
        channel_data, sample_rate = load_audio(channel_path)

        # Save the audio data to the cpy folder without the suffix
        channel_file_path = os.path.join(cpy_folder, f"{base}_{name}.wav")
        save_audio(channel_file_path, channel_data, 192000)
        processed_files.append(channel_file_path)

    # Cleanup files that were not chosen or processed
    cleanup_files(channel_files, {name: path for name, path in selected_channels.items()})

    # Return the list of processed files
    return processed_files