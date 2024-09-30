# g_choose.py

import os
import re
import f_sort  # Still need this import here

def rename_segments(directory):
    """Renames _atk and _dev files to their base segment names."""
    pattern = re.compile(r"(.+seg_\d{4})(?:_dev|_atk)\.wav", re.IGNORECASE)
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            new_filename = pattern.sub(r"\1.wav", filename)
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)
            os.rename(old_path, new_path)

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples):
    from aa_common import input_with_defaults, print_segment_info, get_tmp_folder, get_wavecycle_samples_target, set_wavecycle_samples_target, get_wavecycle_samples

    seg_folder = os.path.join(get_tmp_folder(), "seg")

    atk_deleted = False
    dev_deleted = False
    normal_deleted = False

    while True:
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

        accept_all_settings = input_with_defaults("Do you want to accept all current settings? (Y/n): ").strip().lower() or 'y'

        if accept_all_settings == 'y':
            settings['accept_current_settings'] = True
            print("Proceeding with current settings...\n")
            break

        run_f_sort = False
        new_tolerance_input = input_with_defaults(f"Enter new tolerance percentage or accept current (+/-{settings['percent_tolerance']}%) by pressing ENTER: ", default="").strip()
        if new_tolerance_input:
            new_tolerance = float(new_tolerance_input)
            settings['percent_tolerance'] = new_tolerance
            run_f_sort = True
        else:
            print(f"Accepted current tolerance: +/-{settings['percent_tolerance']}%")
            set_wavecycle_samples_target(f_sort.calculate_mode_wavecycle_length(get_wavecycle_samples()))

        if run_f_sort:
            print("Renaming segments to remove _atk and _dev suffixes and rerunning f_sort...")
            rename_segments(seg_folder)

            total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
                settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, os.listdir(seg_folder)
            )
        else:
            total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples = f_sort.run(
                settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, os.listdir(seg_folder)
            )

        settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()

    keep_atk_segments = input_with_defaults("Do you want to keep attack segments? (Y/n): ").strip().lower() or 'y'
    keep_dev_segments = input_with_defaults("Do you want to keep deviant segments? (Y/n): ").strip().lower() or 'y'
    keep_normal_segments = input_with_defaults("Do you want to keep normal segments? (Y/n): ").strip().lower() or 'y'

    for segment_file in os.listdir(seg_folder):
        file_path = os.path.join(seg_folder, segment_file)
        if keep_atk_segments == 'n' and '_atk.wav' in segment_file:
            os.remove(file_path)
            atk_deleted = True
        elif keep_dev_segments == 'n' and '_dev.wav' in segment_file:
            os.remove(file_path)
            dev_deleted = True
        elif keep_normal_segments == 'n' and re.match(r'.*_seg_\d{4}\.wav$', segment_file):
            os.remove(file_path)
            normal_deleted = True

    return settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, lower_bound_samples, upper_bound_samples, atk_deleted, dev_deleted, normal_deleted
