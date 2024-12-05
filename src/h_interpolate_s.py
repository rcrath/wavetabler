# h_interpolate_s.py
import os
import resampy
import soundfile as sf

def run(seg_folder, frames_folder):
    """
    Interpolates all audio files in the seg folder to 2048 samples
    and saves them to the frames folder.

    Parameters:
    - seg_folder: str, path to the folder containing the input files.
    - frames_folder: str, path to the folder where interpolated files will be saved.
    """
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)

    # Process each file in the seg folder
    for file_name in os.listdir(seg_folder):
        file_path = os.path.join(seg_folder, file_name)

        # Ensure it's a file
        if not os.path.isfile(file_path):
            continue

        try:
            # Load the audio
            data, sample_rate = sf.read(file_path)
            # print(f"Processing file: {file_name}, Original shape: {data.shape}")

            # Interpolate to 2048 samples
            target_samples = 2048
            interpolated_data = resampy.resample(data, len(data), target_samples)

            # Save to frames folder
            output_path = os.path.join(frames_folder, file_name)
            sf.write(output_path, interpolated_data, sample_rate)
            # print(f"Saved interpolated file: {output_path}")
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
