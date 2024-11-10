
# a_wvtbl.py

import os
import b_menu
import c_upsample
import e_seg
import e_seg2
import f_sort
import g_choose
import h_interpolate
import j_wvtblr 
import k_clean  
import aa_common
import shutil
import b_stereo2mono


def process_single_file(file_name):
    # Initialize settings for each file to ensure clean state
    aa_common.global_settings = aa_common.initialize_settings()  # Reset settings for each file

    # Update the source file to the current file being processed
    aa_common._start_file_name = file_name
    aa_common._start_file = os.path.join(aa_common.source_folder, file_name)
    aa_common._base = os.path.splitext(file_name)[0]
    aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")

    print(f"Processing {file_name}...")

    # Ensure tmp/seg and tmp/frames folders are created
    seg_folder = os.path.join(aa_common.tmp_folder, "seg")
    if not os.path.exists(seg_folder):
        os.makedirs(seg_folder)  # Create the seg folder if it doesn't exist

    frames_folder = os.path.join(aa_common.tmp_folder, "frames")
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)  # Create the frames folder if it doesn't exist

    concat_folder = os.path.join(aa_common.tmp_folder, "concat")
    if not os.path.exists(concat_folder):
        os.makedirs(concat_folder)  # Create the concat folder if it doesn't exist
    
    # Ensure that tmp/cpy folder is created
    cpy_folder = os.path.join(aa_common.tmp_folder, "cpy")
    os.makedirs(cpy_folder, exist_ok=True)

    # Copy the current source file into the cpy folder
    shutil.copy2(aa_common._start_file, cpy_folder)

    # Run the upsampling
    processed_files, autocorrelation_flag = c_upsample.run()

    # Use the appropriate module based on the flag
    if autocorrelation_flag:
        e_seg2.run(processed_files)
    else:
        e_seg.run(processed_files)

    # Run sorting
    total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
        aa_common.global_settings, 0, 0, 0, 0, True, processed_files
    )

    # Choose settings and update settings
    aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted = g_choose.run(
        aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, True, lower_bound_samples, upper_bound_samples
    )

    # Proceed to interpolation step
    h_interpolate.run(total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, aa_common.global_settings)

    # Call j_wvtblr to generate the final wavetable
    j_wvtblr.run(atk_deleted, dev_deleted, normal_deleted)

    # Cleanup temporary files for this file
    k_clean.run()
    print(f"Finished processing {file_name}.\n")


def main():
    # Initialize settings
    aa_common.global_settings = aa_common.initialize_settings()

    # Run the stereo-to-mono conversion, and quit if the user opts to cancel
    if not b_stereo2mono.run():
        print("Exiting as per user request.")
        return  # Exit the script if the user cancels

    # Run the menu to select the source file(s)
    selected_files = b_menu.run()


    # If multiple files are selected, run in batch mode
    for file_name in selected_files:
        process_single_file(file_name)

    print("\n\nSUCCESS\n\n")

if __name__ == "__main__":
    main()
