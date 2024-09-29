

# c_upsample.py

import os
import aa_common
import soundfile as sf
import numpy as np

# New global variable for threshold factor and size
thresh_factor = 4  # Multiplier for the threshold size (can be easily changed)
thresh_size = aa_common.wavecycle_size * aa_common.frame_count * thresh_factor


def load_audio(file_path):
    """
    Function to load the audio file.
    """
    data, sample_rate = sf.read(file_path)
    return data, sample_rate


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
    """
    The main function of c_upsample, now simplified to check for large files and handle selection if needed.
    """
    # Get the src file path from aa_common
    src_file = aa_common.get_src_file()

    # Check if the file exceeds thresh_size size and allow the user to select a portion if needed
    processed_file_path = check_and_prompt_for_large_files(src_file)

    # Call the function to truncate the waveform at the start and end, ensuring it's properly prepared
    check_and_truncate_waveform(processed_file_path)

    # Return the processed file path so the main script can continue handling it
    return [processed_file_path]  # Return as a list to match the old format