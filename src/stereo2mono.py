import os
import sys
import soundfile as sf
import numpy as np

def list_stereo_files(input_folder):
    """List all stereo audio files in the input folder."""
    stereo_files = []
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".wav"):  # Adjust for other file formats if needed
            file_path = os.path.join(input_folder, file_name)
            try:
                with sf.SoundFile(file_path) as f:
                    if f.channels == 2:  # Check if the file is stereo
                        stereo_files.append(file_name)
            except:
                print(f"Error reading file: {file_name}")
    return stereo_files

def stereo_to_mono_mid_channel(input_file):
    """Convert stereo file to mono using the mid channel and overwrite the original file."""
    # Read the stereo file
    data, samplerate = sf.read(input_file)

    # Check if the file is stereo
    if len(data.shape) == 2 and data.shape[1] == 2:
        # Extract the mid channel (average of left and right channels)
        mid_channel = np.mean(data, axis=1)
    else:
        raise ValueError("Input file is not stereo.")

    # Overwrite the original file with the mono (mid-channel) audio file
    sf.write(input_file, mid_channel, samplerate, subtype='FLOAT')
    print(f"Converted {input_file} to mono and overwritten the original file.")

if __name__ == "__main__":
    # Prompt the user to proceed with the conversion
    proceed = input("This will convert and overwrite any stereo files in the input folder to mono. \nIf you choose not to, make sure you do not choose any stereo files in the next step. \nThey will crash the script.  (This is a temporary thing) \nProceed to convert stereo to mono? Y/n: ").strip().lower()

    if proceed not in ('y', ''):  # If not 'y' or empty (Enter), quit
        print("Nothing changed, proceeding")
        exit()

    # Define the input folder (where the stereo files are located)
    input_folder = os.path.join(os.path.dirname(__file__), '../input')


    # List all stereo files in the input folder
    stereo_files = list_stereo_files(input_folder)

    if not stereo_files:
        print("No stereo files found in the input folder.")
    else:
        # Process each stereo file and convert it to mono
        print("Processing stereo files...")
        for file_name in stereo_files:
            input_file = os.path.join(input_folder, file_name)
            try:
                stereo_to_mono_mid_channel(input_file)
            except ValueError as e:
                print(f"Skipping {file_name}: {e}")
        print("All stereo files processed.")
