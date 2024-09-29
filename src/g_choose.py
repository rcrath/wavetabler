# g_choose.py

import os
import re
import f_sort  # Add this import to avoid the NameError
from aa_common import input_with_quit, input_with_defaults, print_segment_info, prompt_update_settings, get_base, get_tmp_folder, get_wavecycle_samples_target, set_wavecycle_samples_target, get_wavecycle_samples

def rename_segments(directory):
    # Define the regex pattern to match segment files with _dev or _atk suffixes (case-insensitive)
    pattern = re.compile(r"(.+seg_\d{4})(?:_dev|_atk)\.wav", re.IGNORECASE)

    # Iterate through files in the directory (non-recursive)
    for filename in os.listdir(directory):
        # Check if the file matches the pattern
        match = pattern.match(filename)
        if match:
            # Create the new filename by removing the _dev or _atk suffix and adding .wav manually
            new_filename = pattern.sub(r"\1.wav", filename)

            # Get full paths for renaming
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)

            # Rename the file
            os.rename(old_path, new_path)
            # print(f"Renamed: {filename} -> {new_filename}")

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples):
    seg_folder = os.path.join(get_tmp_folder(), "seg")  # Correct folder for segmented files

    atk_deleted = False
    dev_deleted = False
    normal_deleted = False
    
    while True:  # Add a loop here to handle repeated cycles through f_sort and g_choose
        # Print segment info before making any changes
        print_segment_info(
            total_segments, 
            total_deviant_segments, 
            total_normal_segments, 
            total_attack_segments, 
            get_wavecycle_samples_target(), 
            settings, 
            lower_bound_samples, 
            upper_bound_samples,
            False, False, False
        )

        # Initial input to accept all settings
        accept_all_settings = input_with_defaults("Do you want to accept all current settings? (Y/n): ").strip().lower() or 'y'

        if accept_all_settings == 'y':
            # If the user accepts all settings, proceed to the "keep" questions
            settings['accept_current_settings'] = True
            print("Proceeding with current settings...\n")
            break  # Exit the loop

        # If "no" to accepting current settings, ask about tolerance
        run_f_sort = False
        new_tolerance_input = input_with_defaults(f"Enter new tolerance percentage or accept current (+/-{settings['percent_tolerance']}%) by pressing ENTER: ", default="").strip()

        if new_tolerance_input:
            new_tolerance = float(new_tolerance_input)
            settings['percent_tolerance'] = new_tolerance
            run_f_sort = True  # Flag to rerun f_sort due to tolerance change
        else:
            print(f"Accepted current tolerance: +/-{settings['percent_tolerance']}%")
            # Automatically use mode without asking for input
            set_wavecycle_samples_target(f_sort.calculate_mode_wavecycle_length(get_wavecycle_samples()))

        # After tolerance handling, rerun f_sort if tolerance was changed
        if run_f_sort:
            print("Renaming segments to remove _atk and _dev suffixes and rerunning f_sort...")
            rename_segments(seg_folder)  # Remove _dev and _atk suffixes from the correct folder

            # Call f_sort and return to the top of the loop to restart g_choose
            total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
                settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, os.listdir(seg_folder)  # Use seg_folder
            )
        else:
            # If tolerance wasn't changed, still loop back to f_sort
            total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
                settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, os.listdir(seg_folder)  # Use seg_folder
            )

        # Ensure the custom wavecycle target is saved back to settings
        settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()

    # After settings are fully accepted, proceed to "keep" questions
    keep_atk_segments = input_with_defaults("Do you want to keep attack segments? (Y/n): ").strip().lower() or 'y'
    keep_dev_segments = input_with_defaults("Do you want to keep deviant segments? (Y/n): ").strip().lower() or 'y'
    keep_normal_segments = input_with_defaults("Do you want to keep normal segments? (Y/n): ").strip().lower() or 'y'

    # Handle segment discarding based on user input
    for segment_file in os.listdir(seg_folder):  # Use seg_folder
        file_path = os.path.join(seg_folder, segment_file)  # Use seg_folder for file path
        if keep_atk_segments == 'n' and '_atk.wav' in segment_file:
            os.remove(file_path)
            atk_deleted = True
        elif keep_dev_segments == 'n' and '_dev.wav' in segment_file:
            os.remove(file_path)
            dev_deleted = True
        elif keep_normal_segments == 'n' and re.match(r'.*_seg_\d{4}\.wav$', segment_file):
            os.remove(file_path)
            normal_deleted = True

    # Pass the flags to j_wvtblr.run()
    return settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted
