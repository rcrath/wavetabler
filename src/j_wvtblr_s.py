# jwvtblr_s.py

import os
import re
import soundfile as sf
import numpy as np
from datetime import datetime
from j_wvtblr import create_wavetable_from_concat, apply_padding_if_needed, split_and_save_wav_with_correct_padding, plot_concat, check_wavetable, fixed_length
from aa_common import input_with_defaults
def run(frames_folder, concat_folder, base_name, wavetables_folder):
    """
    Concatenate all audio files in the frames folder, create a single concatenated file,
    and process it to generate wavetables based on user options.

    Parameters:
    - frames_folder: str, path to the folder containing frame files.
    - concat_folder: str, path to the folder where the concatenated file will be saved.
    - base_name: str, base name for the output files.
    - wavetables_folder: str, path to save generated wavetables.
    """
    if not os.path.exists(concat_folder):
        os.makedirs(concat_folder)
    if not os.path.exists(wavetables_folder):
        os.makedirs(wavetables_folder)

    # Concatenate all frames
    concat_file_path = os.path.join(concat_folder, f"{base_name}_concat.wav")
    all_frames = []
    sample_rate = None

    for file_name in sorted(os.listdir(frames_folder)):
        file_path = os.path.join(frames_folder, file_name)
        if not os.path.isfile(file_path):
            continue

        data, sr = sf.read(file_path)
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            raise ValueError(f"Inconsistent sample rate in {file_name}: {sr} Hz")

        all_frames.append(data)

    concatenated_data = np.concatenate(all_frames, axis=0)
    sf.write(concat_file_path, concatenated_data, sample_rate)
    print(f"Concatenated file saved to: {concat_file_path}")

    # Proceed with wavetable creation options
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    options = input_with_defaults(
        "Choose wavetable creation method (e.g., 1,2 or 1-3):\n"
        "1. Fit whole within 256*frames divisible by 2048 samples (default)\n"
        "2. Arbitrarily cut into chunks\n"
        "3. Select and save\n"
        "Press Enter to select option 1: "
    ).strip()

    if not options or not re.match(r'^[1-3, -]+$', options):
        options = "1"

    selected_options = set()
    for part in options.split(','):
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                selected_options.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                selected_options.add(int(part))
            except ValueError:
                continue

    # Option 1: Fit whole
    if 1 in selected_options:
        suffix = "_fit"
        fitted_wavetable_path = os.path.join(
            wavetables_folder, f"{base_name}_{timestamp}{suffix}.wav"
        )
        create_wavetable_from_concat(concat_file_path, fitted_wavetable_path)

    # Option 2: Arbitrary chunks
    if 2 in selected_options:
        suffix = "_chunk"
        data_frames, sr_frames = sf.read(concat_file_path, dtype='float32')
        data_frames_padded = apply_padding_if_needed(data, fixed_length, amplitude_tolerance_db=-60)
        split_and_save_wav_with_correct_padding(
            data_frames_padded, wavetables_folder, base_name, suffix, timestamp, "chunk"
        )

    # Option 3: Manual selection
    if 3 in selected_options:
        suffix = "_pick"
        plot_concat(
            concat_file_path, fixed_length=2048, sr=sample_rate, base=base_name, suffix=suffix
        )

    # Validate wavetables
    for wav_file in os.listdir(wavetables_folder):
        if wav_file.endswith('.wav'):
            file_path = os.path.join(wavetables_folder, wav_file)
            check_wavetable(file_path)

    print(f"\nYour wavetables are in {wavetables_folder}\n")
