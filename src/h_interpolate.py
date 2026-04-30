# h_interpolate.py

import os
import shutil
import numpy as np
import soundfile as sf
import re
from tqdm import tqdm

# Move imports inside the function to avoid circular import issues

def run(total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, settings):
    # Import inside the function to avoid circular import
    from aa_common import get_base, get_tmp_folder, get_segment_sizes, interpolate_seg, get_wavecycle_samples_target
    
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

    # Import wavecycle_size locally to avoid circular dependency
    from aa_common import wavecycle_size

    # Pre-filter so the progress bar's total reflects actual work, not directory size.
    seg_files = [f for f in os.listdir(seg_folder) if pattern.match(f)]

    for file in tqdm(seg_files, desc="  interpolating", unit="seg"):
        if pattern.match(file):
            seg_file_path = os.path.join(seg_folder, file)
            single_cycles_192k32b_path = os.path.join(singles_folder, file)

            # Read the original segment
            data, samplerate = sf.read(seg_file_path)

            # Skip resampling if the segment is already exactly wavecycle_size samples.
            # Resampling identity-length data introduces unnecessary numerical drift,
            # which matters for the sine null test.
            if len(data) == wavecycle_size:
                shutil.copy2(seg_file_path, single_cycles_192k32b_path)
                continue

            # Apply interpolation to adjust the segment length
            interpolated_segment = interpolate_seg(data, samplerate)
            sf.write(single_cycles_192k32b_path, interpolated_segment, samplerate, subtype='FLOAT')

    # print("\nInterpolation complete. Files saved to 'frames' folder.")
