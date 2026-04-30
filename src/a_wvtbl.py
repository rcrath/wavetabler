# a_wvtbl.py

import os
import b_menu
import c_upsample
import cc_channels
import d_interval
import e_seg
import f_sort
import g_choose
import h_interpolate
import j_wvtblr
import k_clean
import aa_common
import shutil
import soundfile as sf

TOTAL_PHASES = 8

def _phase(n, name):
    print(f"\n[{n}/{TOTAL_PHASES}] {name} ...")

def process_single_file(file_name):
    aa_common.global_settings = aa_common.initialize_settings()
    aa_common._start_file_name = file_name
    aa_common._start_file = os.path.join(aa_common.source_folder, file_name)
    aa_common._base = os.path.splitext(file_name)[0]
    aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")

    # create tmp folders
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

    # copy selected input to cpy
    shutil.copy2(aa_common._start_file, cpy_folder)
    copied_file_path = os.path.join(cpy_folder, os.path.basename(aa_common._start_file))
    
    _phase(1, "Upsampling to 192 kHz")
    processed_files = c_upsample.run()

    _phase(2, "Extracting channels")
    processed_channel_files = cc_channels.run()

    if aa_common.get_autocorrelation_flag():
        _phase(3, "Detecting period (autocorrelation)")
        d_interval.run(processed_channel_files)
    else:
        _phase(3, "Segmenting (zero-crossing)")
        e_seg.run(processed_channel_files)

    _phase(4, "Sorting segments")
    total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
            aa_common.global_settings, 0, 0, 0, 0, True, processed_files)

    _phase(5, "Choosing segments to keep")
    aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted = g_choose.run(
        aa_common.global_settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, True, lower_bound_samples, upper_bound_samples
    )

    _phase(6, "Interpolating to 2048 samples")
    h_interpolate.run(total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, aa_common.global_settings)

    _phase(7, "Building wavetable")
    j_wvtblr.run(atk_deleted, dev_deleted, normal_deleted)

    _phase(8, "Cleanup")
    k_clean.run()

    print(f"\nFinished processing {file_name}.\n")

def main():
    aa_common.global_settings = aa_common.initialize_settings()
    selected_files = b_menu.run()
    for file_name in selected_files:
        process_single_file(file_name)
    print("\n\nSUCCESS\n\n")

if __name__ == "__main__":
    main()
