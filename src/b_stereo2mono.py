import os
import soundfile as sf
import aa_common

def is_stereo(file_path):
    """Check if the given audio file is stereo."""
    try:
        with sf.SoundFile(file_path) as f:
            return f.channels == 2
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return False

def convert_to_mono(file_path):
    """Convert a stereo audio file to mono and overwrite the original file."""
    try:
        data, sample_rate = sf.read(file_path)
        if data.ndim == 2:
            # Average the left and right channels to create a mono track
            mono_data = data.mean(axis=1)
            sf.write(file_path, mono_data, sample_rate)
            print(f"Converted {os.path.basename(file_path)} to mono.")
    except Exception as e:
        print(f"Error converting {file_path}: {e}")

def prompt_user():
    """Display a prompt to inform the user about the process."""
    message = (
        "This script converts any of the files you choose from the input folder into wavetables. "
        "If you have not done so yet, place COPIES of any short wav files you wish to process in the input folder. "
        "Any that are stereo will be reduced to mono first.\n"
        "Proceed? (Y/n): "
    )
    proceed = input(message).strip().lower() or 'y'
    return proceed == 'y'

def run():
    if not prompt_user():
        print("Operation cancelled. Exiting.")
        return False  # Signal to quit the main script

    input_folder = aa_common.source_folder
    stereo_files_found = False

    # Loop through all WAV files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(aa_common.ext):
            file_path = os.path.join(input_folder, filename)
            if is_stereo(file_path):
                stereo_files_found = True
                convert_to_mono(file_path)

    if stereo_files_found:
        print("\nAll stereo files have been converted to mono.")
    else:
        print("\nNo stereo files found. Proceeding to the menu.")

    return True  # Signal to continue the main script


if __name__ == "__main__":
    run()
