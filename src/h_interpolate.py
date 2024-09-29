# h_interpolate.py

import os
import numpy as np
import soundfile as sf
import resampy
import re
from aa_common import input_with_quit, input_with_defaults, get_segment_sizes, get_base, get_tmp_folder, interpolate_seg, get_wavecycle_samples_target

# Function to perform interpolation
def run(total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, settings):
    base = get_base()
    tmp_folder = get_tmp_folder()
    seg_folder = os.path.join(tmp_folder, 'seg')  # Correct folder for segmented files
    ext = ".wav"
    segment_sizes = get_segment_sizes(base, seg_folder, ext)  # Adjust to use seg_folder

    # Define the regex pattern to match segment files with _dev or _atk suffixes
    pattern = re.compile(r"(.+seg_\d{4})(?:_dev|_atk){0,1}\.wav", re.IGNORECASE)

    # Create a new subfolder 'frames' within 'tmp_folder'
    singles_folder = os.path.join(tmp_folder, 'frames')
    os.makedirs(singles_folder, exist_ok=True)

    # Before interpolation, ensure wavecycle_samples_target has a valid value
    wavecycle_samples_target = get_wavecycle_samples_target()
    if wavecycle_samples_target <= 0:
        raise ValueError("Invalid wavecycle_samples_target: It must be a positive non-zero value.")

    print("\nInterpolating...")

    # Iterate through all files in the seg folder, filtering with the regex pattern
    for file in os.listdir(seg_folder):  # Adjusted to use seg_folder
        if pattern.match(file):
            # Process only files matching the pattern
            seg_file_path = os.path.join(seg_folder, file)  # Adjusted to use seg_folder

            # Read the original segment and proceed with interpolation
            data, samplerate = sf.read(seg_file_path)
            info = sf.info(seg_file_path)

            # Determine the correct subtype for writing
            write_subtype = 'FLOAT'  # Default to FLOAT for compatibility
            if info.subtype in ['PCM_16', 'PCM_24', 'PCM_32']:
                write_subtype = info.subtype

            # Apply interpolation to adjust the segment length
            interpolated_segment = interpolate_seg(data, samplerate)  # Remove wavecycle_samples_target

            # Write the interpolated segment to the 'frames' folder
            single_cycles_192k32b_path = os.path.join(singles_folder, file)
            sf.write(single_cycles_192k32b_path, interpolated_segment, samplerate, subtype='FLOAT')

    # print("\nInterpolation complete. Files saved to 'frames' folder.")
