
# c_upsample.py

import os
import aa_common
import librosa
import resampy
import numpy as np
import soundfile as sf
from pydub import AudioSegment


# New global variable for threshold factor and size
thresh_factor = 4  # Multiplier for the threshold size (can be easily changed)
thresh_size = 2048 * 256 * thresh_factor


def load_audio(file_path):
    """
    Function to load the audio file.
    """
    data, sample_rate = sf.read(file_path, dtype='float32')

    return data, sample_rate

# upsample function
def interpolate_best(waveform, original_sr, target_sr):
    """
    Resample a waveform to a new sample rate using high-quality resampling.
    Handles both mono and stereo input.

    Parameters:
    - waveform: np.ndarray, input waveform (mono or stereo).
    - original_sr: int, original sample rate.
    - target_sr: int, target sample rate.

    Returns:
    - np.ndarray, resampled waveform (mono or stereo).
    """
    # print("Entering interpolate_best")
    # print(f"Audio data type: {type(waveform)}, Shape: {waveform.shape}")

    if waveform.ndim == 2:  # Stereo
        print("Stereo detected, processing each channel separately")
        # Extract and resample each channel
        left_channel = resampy.resample(waveform[:, 0], original_sr, target_sr)
        right_channel = resampy.resample(waveform[:, 1], original_sr, target_sr)

        # Combine channels into stereo
        resampled_waveform = np.stack((left_channel, right_channel), axis=-1)
    elif waveform.ndim == 1:  # Mono
        print("Mono detected, processing single channel")
        # Resample mono waveform directly
        resampled_waveform = resampy.resample(waveform, original_sr, target_sr)
    else:
        raise ValueError(f"Unexpected waveform shape: {waveform.shape}")

    # print("After interpolation")
    # print(f"Resampled audio type: {type(resampled_waveform)}, Shape: {resampled_waveform.shape}")
    return resampled_waveform


def save_audio(file_path, data, sample_rate):
    """
    Save the audio data to a specified file path with the given sample rate.
    
    Parameters:
    - file_path: str, the path to save the audio file.
    - data: np.ndarray, the audio data to save.
    - sample_rate: int, the sample rate of the audio data.
    """
    sf.write(file_path, data, sample_rate, subtype='FLOAT')




def apply_fades(data, fade_samples):
    if len(data) > 2 * fade_samples:
        fade_in_window = np.linspace(0, 1, fade_samples, dtype=np.float32)
        fade_out_window = np.linspace(1, 0, fade_samples, dtype=np.float32)
        data[:fade_samples] *= fade_in_window
        data[-fade_samples:] *= fade_out_window
    else:
        print("Audio data too short for the specified fade length.")
    return data

def test_rising_conditions(data):
    """
    Test the rising-from-zero at the start and rising-to-zero at the end of the file.
    This function does not modify the data but returns whether the start and end are valid.
    """
    
    sample_size = len(data)

    # Check if the start rises from zero within the sputter range
    start_valid = False
    for i in range(min(aa_common.sputter, sample_size - aa_common.ZERO_WINDOW + 1)):
        if aa_common.is_rising_from_zero(data[i:i + aa_common.ZERO_WINDOW]):
            # print(f"Valid rising-from-zero found at index {i}.")
            start_valid = True
            break

    # Check if the end rises to zero within the sputter range
    end_valid = False
    for i in range(sample_size - 1, max(aa_common.ZERO_WINDOW, sample_size - aa_common.sputter), -1):
        if aa_common.is_rising_to_zero(data[i - aa_common.ZERO_WINDOW + 1:i + 1]):
            # print(f"Valid rising-to-zero found at index {i}.")
            end_valid = True
            break

    return start_valid, end_valid


def truncate_waveform(data):
    """
    Truncate the waveform if the start and end do not meet the rising-from-zero or rising-to-zero conditions.
    """
    sample_size = len(data)
    
    # Find the first valid rising-from-zero and truncate before it
    for i in range(min(aa_common.sputter, sample_size - aa_common.ZERO_WINDOW + 1)):
        if aa_common.is_rising_from_zero(data[i:i + aa_common.ZERO_WINDOW]):
            # print(f"Truncating start at index {i}.")
            data = data[i:]
            break

    # Find the last valid rising-to-zero and truncate after it
    for i in range(sample_size - 1, max(aa_common.ZERO_WINDOW, sample_size - aa_common.sputter), -1):
        if aa_common.is_rising_to_zero(data[i - aa_common.ZERO_WINDOW + 1:i + 1]):
            # print(f"Truncating end at index {i}.")
            data = data[:i + 1]
            break

    return data


def check_and_truncate_waveform(file_path):
    """
    Test the waveform for valid rising-from-zero and rising-to-zero, and truncate if necessary.
    """
    data, sample_rate = load_audio(file_path)

    # print(f"Loaded file with {len(data)} samples and sample rate {sample_rate}")

    # First test if the waveform is valid without truncation
    start_valid, end_valid = test_rising_conditions(data)

    # If either start or end is invalid, truncate the waveform
    if not start_valid or not end_valid:
        # print("Waveform did not pass tests. Truncating...")
        data = truncate_waveform(data)
    else:
        # print("Waveform passed tests. No truncation needed.")
        pass

    # Save the waveform back to the file, whether modified or not
    sf.write(file_path, data, sample_rate, subtype='FLOAT')
    # print(f"Waveform processed and saved back to {file_path}")


def check_and_prompt_for_large_files(file_path):
    """
    Check if the file exceeds the thresh_size size and prompt the user to select a portion or continue with the whole file.
    """
    data, sample_rate = load_audio(file_path)

    thresh_size = thresh_factor * aa_common.frame_count * aa_common.wavecycle_size

    # Check if the file is larger than thresh_size
    if len(data) > thresh_size:
        choice = aa_common.input_with_defaults(
            f"\nThis is a large file that may take a significant time to process.\n"
            f"Would you like to select a portion of it or continue with the whole file? (Press Enter to continue or type 's' to select): ",
            default="continue"
        ).strip().lower()

        if choice == "s":
            # If the user chooses to select a portion, limit the selection to thresh_size samples
            aa_common.plot_wav_file_interactive(file_path, fixed_length=thresh_size)
        else:
            print("Continuing with the whole file.")

    return file_path  # Return the file path that will be processed

def run():
    
    base = aa_common.get_base()
    # print(f"base: {base}")
    # start_file = aa_common.get_start_file()
    
    # Construct the full tmp_folder path
    tmp_folder = os.path.join(base, "tmp")
    # print(f"tmp: {tmp_folder}")

    # Construct the full path for cpy_file
    cpy_folder = os.path.join(tmp_folder, "cpy")
    cpy_file = os.path.join(cpy_folder, f"{base}.wav")
    # print(sf.info(cpy_file))
    # print("this is the input")
    # breakpoint()
    cpy_file_data, sample_rate = load_audio(cpy_file)
    # print(sf.info(cpy_file))
    # print("audio loaded on line 182")
    # breakpoint()
    # Check if the file exceeds thresh_size size and allow the user to select a portion if needed
    processed_files = check_and_prompt_for_large_files(cpy_file)
    # print(f"processed_files: {processed_files}")
    # print(sf.info(cpy_file))
    # print("audio checked for large files on line 187")
    # breakpoint()
    # Call the function to truncate the waveform at the start and end, ensuring it's properly prepared
    check_and_truncate_waveform(processed_files)

    # upsample the file
    # Load the waveform and sample rate from the input file
    cpy_file_data, sample_rate = load_audio(cpy_file)

    # During the upsampling process in c_upsample.py
    # Convert the input data to 32-bit float
    interpolated_input_192k32b = interpolate_best(cpy_file_data.astype(np.float32), sample_rate, 192000)

    # Save the interpolated input to cpy
    cpy = f"{base}.wav"
    cpy_path = os.path.join(cpy_folder, cpy)
    save_audio(cpy_path, interpolated_input_192k32b, 192000)

    # Load the upsampled file
    cpy_data, _ = load_audio(cpy_path)

    return processed_files  # Return the file path
