# b_menu.py

import os
import shutil  # Added for file copying
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
            channels = f.channels  # Number of channels (1 for mono, 2 for stereo)

            # Calculate the ratio of total samples to 524,288
            ratio = round(samples / 524288, 2)

            details = {
                'file_name': file,
                'ratio': ratio,
                'sample_rate': sample_rate,
                'channels': channels,
                'bit_depth': f.subtype
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


def run():
    # List and display WAV files with details
    file_details = list_wav_files_with_details(aa_common.source_folder)
    print_file_details(file_details)

    # Prompt user to select a file
    while True:
        selection = input("\nEnter the number of the file to select, or type 'q' to exit: ").strip()
        if selection.lower() == 'q':
            print("Quitting script.")
            exit()

        try:
            selected_index = int(selection) - 1
            if 0 <= selected_index < len(file_details):
                selected_file = file_details[selected_index]['file_name']
                aa_common._start_file_name = selected_file
                aa_common._start_file = os.path.join(aa_common.source_folder, selected_file)
                aa_common._base = os.path.splitext(selected_file)[0]
                aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")
                print(f"Selected: {selected_file}")

                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number or 'q'.")

    # prompt to accept ALL defaults
    accept_defaults = aa_common.input_with_defaults("\nAccept all defaults (try this first!) Y/n: ", default="y")

    if accept_defaults == "y":
        aa_common.accept_all_defaults = True  # Set the global flag to accept defaults


    # Check if tmp folder exists before proceeding
    tmp_folder = aa_common.get_tmp_folder()
    if os.path.exists(tmp_folder):
        cleanup_choice = aa_common.input_with_defaults("Tmp folder exists, remove? (Y or ENTER / n to quit): ").strip().lower() or 'y'

        if cleanup_choice == 'y':
            aa_common.perform_cleanup()  # Call cleanup function from aa_common
        else:
            print("Quitting script.")
            exit()  # Quit the script if the user chooses 'n'
    else:
        # If the tmp folder does not exist, create it
        aa_common.ensure_tmp_folder()

    # Create the 'src' folder inside tmp and copy the chosen source file there
    src_folder = os.path.join(aa_common.tmp_folder, "src")
    os.makedirs(src_folder, exist_ok=True)
    shutil.copy2(aa_common._start_file, src_folder)

    # Update variables to point to the new source file inside 'src' folder
    aa_common._src_file = os.path.join(src_folder, aa_common._start_file_name)

    # Everything is now set to use the source file in the 'src' folder.
