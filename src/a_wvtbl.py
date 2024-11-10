# a_wvtbl.py

import os
import b_menu
import c_upsample
import d_interval  # Import d_interval
import f_sort
import g_choose
import h_interpolate
import j_wvtblr
import k_clean
import aa_common
import shutil
import b_stereo2mono

def process_single_file(file_name):
    aa_common.global_settings = aa_common.initialize_settings()
    aa_common._start_file_name = file_name
    aa_common._start_file = os.path.join(aa_common.source_folder, file_name)
    aa_common._base = os.path.splitext(file_name)[0]
    aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")

    seg_folder = os.path.join(aa_common.tmp_folder, "seg")
    if not os.path.exists(seg_folder):
        os.makedirs(seg_folder)
    frames_folder = os.path.join(aa_common.tmp_folder, "frames")
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)
    concat_folder = os.path.join(aa_common.tmp_folder, "concat")
    if not os.path.exists(concat_folder):
        os.makedirs(concat_folder)
    cpy_folder = os.path.join(aa_common.tmp_folder, "cpy")
    os.makedirs(cpy_folder, exist_ok=True)
    
    shutil.copy2(aa_common._start_file, cpy_folder)

    # Run the upsampling and get the autocorrelation flag
    processed_files, autocorrelation_flag = c_upsample.run()

    # Use the appropriate method based on the flag
    if autocorrelation_flag:
        d_interval.run(processed_files)  # Call d_interval if flag is set
        # Directly proceed to f_sort after d_interval
        skip_e_seg = True
    else:
        e_seg.run(processed_files)
        skip_e_seg = False

    # Skip e_seg and go to f_sort if skip_e_seg is True
    if skip_e_seg:
        print("Skipping e_seg and proceeding directly to f_sort.")

    total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
        aa_common.global_settings, 0, 0, 0, 0, True, processed_files
    )

    aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted = g_choose.run(
        aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, True, lower_bound_samples, upper_bound_samples
    )

    h_interpolate.run(total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, aa_common.global_settings)
    j_wvtblr.run(atk_deleted, dev_deleted, normal_deleted)
    k_clean.run()
    print(f"Finished processing {file_name}.\\n")

def main():
    aa_common.global_settings = aa_common.initialize_settings()
    if not b_stereo2mono.run():
        print("Exiting as per user request.")
        return
    selected_files = b_menu.run()
    for file_name in selected_files:
        process_single_file(file_name)
    print("\\n\\nSUCCESS\\n\\n")

if __name__ == "__main__":
    main()
