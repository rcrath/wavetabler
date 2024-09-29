# a_wvtbl.py

import os
import b_menu
import c_upsample
import e_seg
import f_sort
import g_choose
import h_interpolate
import j_wvtblr 
import k_clean  
import aa_common

def main():
    # Initialize settings
    settings = aa_common.initialize_settings()

    # Run the menu to select the source file
    selected_file_details = b_menu.run()

    # Run the upsampling
    processed_files = c_upsample.run()

    tmp_folder = aa_common.get_tmp_folder()

    # Initialize segment variables
    total_segments = total_deviant_segments = total_normal_segments = total_attack_segments = 0
    first_iteration = True
    

    # Run segmentation for each processed file and collect wavecycle samples
    e_seg.run(processed_files)



    # Run sorting
    total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
        settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, processed_files
    )

    # Choose settings and update settings
    settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted = g_choose.run(
        settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples
    )
    # Proceed to interpolation step
    h_interpolate.run(
        total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, settings
    )

    # Call j_wvtblr to generate the final wavetable
    j_wvtblr.run(atk_deleted, dev_deleted, normal_deleted)

    # Cleanup temporary files
    k_clean.run()
    print("\n\nSUCCESS\n\n")


if __name__ == "__main__":
    main()
