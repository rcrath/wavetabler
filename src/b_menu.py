# b_menu.py - COMPLETE FIX
# Fixes: directory creation AND path construction bugs

import os
import shutil
import aa_common
import soundfile as sf
from tabulate import tabulate

def list_wav_files_with_details(source_folder):
    """
    List WAV files with details such as ratio (samples/524,288), sample rate, channels, and bit depth.
    """
    files = [f for f in os.listdir(source_folder) if f.endswith(aa_common.ext)]
    file_details = []

    for file in files:
        file_path = os.path.join(source_folder, file)
        with sf.SoundFile(file_path) as f:
            samples = f.frames
            sample_rate = f.samplerate
            channels = f.channels

            # Calculate the ratio of total samples to 524,288
            ratio = round(samples / 524288, 2)

        # Specify the float type explicitly
        if 'FLOAT' in f.subtype.upper():
            float_type = 'float32' if 'FLOAT32' in f.subtype.upper() else 'float64'
        else:
            float_type = f.subtype

        details = {
            'file_name': file,
            'ratio': ratio,
            'sample_rate': sample_rate,
            'channels': channels,
            'bit_depth': float_type
        }
        file_details.append(details)

    return file_details

def print_file_details(file_details):
    """
    Print file details in a readable table format, including the ratio of samples/524,288.
    """
    headers = ['Index', 'File Name', 'Ratio', 'Sample Rate', 'Channels', 'Bit Depth']

    # Prepare data for tabulate
    table_data = []
    for i, details in enumerate(file_details):
        file_name = details['file_name']
        ratio = details['ratio']
        sample_rate = details['sample_rate']
        channels = details['channels']
        bit_depth = details['bit_depth']
        table_data.append([i + 1, file_name, ratio, sample_rate, channels, bit_depth])

    print("\n\nSource Files:")
    print(tabulate(table_data, headers=headers, tablefmt="plain"))

def parse_file_selection(selection, total_files):
    """
    Parse the user's selection input, allowing for comma-separated numbers and ranges.
    """
    selected_indices = set()
    
    try:
        parts = selection.split(',')
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                selected_indices.update(range(start, end + 1))
            else:
                selected_indices.add(int(part))
    except ValueError:
        print("Invalid input format. Please use numbers, commas, and ranges like '1,3,5-7'.")
        return None
    
    # Ensure the selected indices are valid
    selected_indices = {i for i in selected_indices if 1 <= i <= total_files}
    
    if not selected_indices:
        print("No valid file indices selected. Please try again.")
        return None
    
    return sorted(selected_indices)

def run():
    aa_common.clear_screen()
    # List and display WAV files with details
    file_details = list_wav_files_with_details(aa_common.source_folder)
    print_file_details(file_details)

    # Prompt user to select one or more files
    while True:
        selection = input("\nEnter the number(s) of the file(s) to select (e.g. 1, 3, 5-8), \nor type 'q' to exit at any point: ").strip()
        if selection.lower() == 'q':
            print("Quitting script.")
            exit()

        selected_indices = parse_file_selection(selection, len(file_details))
        if selected_indices:
            selected_files = [file_details[i - 1]['file_name'] for i in selected_indices]
            print(f"Selected: {', '.join(selected_files)}")

            # Store selected files in aa_common
            aa_common._start_file_name = selected_files[0]
            aa_common._start_files = selected_files
            base_name = os.path.splitext(selected_files[0])[0]
            aa_common._base = aa_common.sanitize_filename(base_name)
            aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")

            break

    # Create the 'cpy' folder inside tmp and copy the chosen source file(s) there
    base = aa_common.get_base()
    print(f"base: {base}")
    tmp_folder = aa_common.get_tmp_folder()
    print(f"tmp_folder: {tmp_folder}")
    
    # CRITICAL FIX: Don't use get_cpy_folder() - it returns broken path
    # Build the correct path ourselves
    actual_cpy_folder = os.path.join(base, "tmp", "cpy")
    print(f"actual_cpy_folder: {actual_cpy_folder}")
    
    cpy = f"{base}.wav"
    print(f"cpy: {cpy}")

    aa_common.clear_screen()
    # Prompt for method choice using input_with_defaults
    method = aa_common.input_with_defaults(
        f"\nChoose a method of segmenting the file {cpy}\n"
        "\n     1. Zero Crossing (default): good for percussive sounds \n"
        "        and sounds with multiple or unclear pitches.\n"
        "\n     2. Autocorrelation: for clearly single pitched sounds \n\nChoose or press enter for default (patience, it may take a while): ",
        '1'
    )

    # Set a flag for the chosen method
    aa_common.set_autocorrelation_flag(method == '2')
    # prompt to accept ALL defaults
    accept_defaults = aa_common.input_with_defaults("\nAccept all defaults (try this first!) Y/n: ", default="y")

    if accept_defaults == "y":
        aa_common.accept_all_defaults = True  # Set the global flag to accept defaults

    # Check if tmp folder exists before proceeding
    if os.path.exists(tmp_folder):
        cleanup_choice = aa_common.input_with_defaults("Tmp folder exists, remove? (Y or ENTER / n to quit): ").strip().lower() or 'y'

        if cleanup_choice == 'y':
            aa_common.perform_cleanup()  # Call cleanup function from aa_common
        else:
            print("Quitting script.")
            exit()  # Quit the script if the user chooses 'n'
    
    # CRITICAL FIX: Always ensure directories exist after cleanup
    # Create the tmp folder structure
    aa_common.ensure_tmp_folder()
    
    # Ensure the cpy subfolder exists
    os.makedirs(actual_cpy_folder, exist_ok=True)
    print(f"Ensured cpy folder exists: {actual_cpy_folder}")

    # CRITICAL FIX: Copy files with correct destination path
    for file_name in selected_files:
        source_file_path = os.path.join(aa_common.source_folder, file_name)
        dest_file_path = os.path.join(actual_cpy_folder, file_name)
        print(f"Copying: {source_file_path}")
        print(f"     to: {dest_file_path}")
        shutil.copy2(source_file_path, dest_file_path)

    # Return the selected files list
    return selected_files