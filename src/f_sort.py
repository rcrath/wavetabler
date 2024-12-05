

# f_sort.py

import os
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re
import soundfile as sf
import aa_common


def autocorrelation_sort(wavecycle_samples):
    if aa_common.get_autocorrelation_flag():
        # If the autocorrelation flag is true, use the already set mode_interval
        mode_interval = aa_common.get_mode_interval()
        
        # Also calculate the average wavecycle length
        wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
        print(f"autocorrelation -- mode: {mode_interval} avg: {wavecycle_samples_target_avg}")
        # Return both values
        return mode_interval, wavecycle_samples_target_avg
    else:
        # Otherwise, calculate the mode interval the regular way
        mode_interval = calculate_mode_wavecycle_length(wavecycle_samples)
        
        # Also calculate the average wavecycle length
        wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
        
        # Return both values
        return mode_interval, wavecycle_samples_target_avg

def on_click_hist(event, y_count, x_count, current_sample_rate):
    from aa_common import frequency_to_note_and_cents, set_wavecycle_samples_target  # Local import
    if event.inaxes and event.button == 1:
        x_min, x_max = event.inaxes.get_xlim()
        if x_min <= event.xdata <= x_max:
            clicked_frequency = event.xdata
            closest_idx = (np.abs(np.array(x_count) - clicked_frequency)).argmin()
            closest_frequency = x_count[closest_idx]
            corresponding_samples = current_sample_rate // closest_frequency
            note, cents = frequency_to_note_and_cents(closest_frequency)
            set_wavecycle_samples_target(corresponding_samples)
            print(f"Selected: {note}{cents:+d} / {closest_frequency:.2f}Hz / {corresponding_samples} samples")
            plt.close()
        else:
            print("Click detected outside of valid plot area. Ignoring.")

def mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    outside_tolerance_files = []
    for segment_file, segment_size in segment_sizes:
        file_path = os.path.join(seg_folder, segment_file)
        if '_atk' in segment_file:
            continue
        if not os.path.exists(file_path):
            continue
        if '_dev' in segment_file:
            continue
        if segment_size < lower_bound_samples or segment_size > upper_bound_samples:
            dev_name = f"{os.path.splitext(segment_file)[0]}_dev{ext}"
            dev_path = os.path.join(seg_folder, dev_name)
            if os.path.exists(dev_path):
                print(f"File {dev_path} already exists. Skipping renaming.")
                continue
            os.rename(file_path, dev_path)
            outside_tolerance_files.append(dev_name)
    return outside_tolerance_files

def mark_attack_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    # No aa_common imports here either
    within_tolerance_count = 0
    attack_segments = []
    for segment_file, segment_size in segment_sizes:
        file_path = os.path.join(seg_folder, segment_file)
        if '_dev' in segment_file:
            continue
        if lower_bound_samples <= segment_size <= upper_bound_samples:
            within_tolerance_count += 1
        else:
            within_tolerance_count = 0
        if within_tolerance_count < 3:
            if '_atk' not in segment_file:
                atk_name = f"{os.path.splitext(segment_file)[0]}_atk{ext}"
            else:
                atk_name = segment_file
            atk_path = os.path.join(seg_folder, atk_name)
            if not os.path.exists(file_path):
                file_path = os.path.join(seg_folder, f"{os.path.splitext(segment_file)[0]}_dev{ext}")
            if os.path.exists(file_path):
                os.rename(file_path, atk_path)
                attack_segments.append(atk_name)
            else:
                continue
        else:
            break
    return attack_segments

def plot_wavecycle_frequencies_with_selection(wavecycle_samples, lower_bound_samples, upper_bound_samples, current_sample_rate, wavecycle_samples_target_avg):
    from aa_common import frequency_to_note_and_cents, set_wavecycle_samples_target  # Local import

    counter = Counter(wavecycle_samples.values())
    x = list(counter.keys())
    y = list(counter.values())
    frequencies = [current_sample_rate / samples for samples in x]

    # get counts of frequencies
    y_count = y  # Actual number of occurrences
    x_count = frequencies  # Corresponding frequencies

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_count, y_count, color='blue', label="Counts")

    # Set the x-axis to a logarithmic scale
    ax.set_xscale('log')

    # Custom frequency tick locations based on musical relevance
    custom_ticks = [20, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 20000]  # Example frequencies
    ax.set_xticks(custom_ticks)
    ax.set_xticklabels([f"{f} Hz" for f in custom_ticks], rotation=45, ha='right')

    mode_frequency = current_sample_rate / aa_common.get_mode_interval()
    avg_frequency = current_sample_rate / wavecycle_samples_target_avg
    ax.axvline(mode_frequency, color='red', linestyle='--', linewidth=2, label=f'Mode: {mode_frequency:.2f}Hz')
    ax.axvline(avg_frequency, color='green', linestyle='--', linewidth=2, label=f'Average: {avg_frequency:.2f}Hz')

    ax.set_title('Click on the best frequency dot to work with. Usually, this is the mode')
    ax.set_xlabel('Frequency (Hz, Log Scale)')
    ax.set_ylabel('Occurrences')
    ax.grid(True, which="both", linestyle='--', alpha=0.5)  # Grid for both major and minor ticks
    ax.legend()

    # Updated to include current_sample_rate
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_hist(event, y_count, x_count, current_sample_rate))
    plt.show()



def calculate_average_wavecycle_length(wavecycle_samples):
    if not wavecycle_samples:
        return 0
    total_samples = sum(wavecycle_samples.values())
    return total_samples // len(wavecycle_samples)


def calculate_mode_wavecycle_length(wavecycle_samples):
    # Local import to avoid dependency loops
    from scipy.stats import mode as scipy_mode

    # Proceed with the usual calculations
    if not wavecycle_samples:
        return 0

    sizes = list(wavecycle_samples.values())
    if len(sizes) == 1:
        aa_common.set_mode_interval(sizes[0])  # Set the mode interval
        return sizes[0]

    mode_result = scipy_mode(sizes)
    if isinstance(mode_result.count, np.ndarray):
        if mode_result.count.size > 0 and mode_result.count[0] > 1:
            aa_common.set_mode_interval(mode_result.mode[0])  # Set the mode interval
            return mode_result.mode[0]
    else:
        if mode_result.count > 1:
            aa_common.set_mode_interval(mode_result.mode)  # Set the mode interval
            return mode_result.mode

    aa_common.set_mode_interval(sizes[0])  # Set the mode interval as a fallback
    return sizes[0]

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, processed_files):
    from aa_common import (get_wavecycle_samples, get_wavecycle_samples_target, set_wavecycle_samples_target,
                           get_all_segment_sizes, get_manual_frequency_input, calculate_tolerance_bounds, 
                           get_base, get_tmp_folder, input_with_defaults, frequency_to_note_and_cents)
    base = get_base()
    # Construct the path to the file in base/tmp/cpy
    cpy_folder = os.path.join(base, "tmp", "cpy")
    cpy_file = os.path.join(cpy_folder, f"{base}.wav")

    # Use sf.read to get the sample rate
    _, current_sample_rate = sf.read(cpy_file)
    # set some variables
    wavecycle_samples = aa_common.get_wavecycle_samples()
    autocorrelation_sort(wavecycle_samples)
    # wavecycle_samples_target_mode = aa_common.get_mode_interval()
    wavecycle_samples_target_mode, wavecycle_samples_target_avg = autocorrelation_sort(wavecycle_samples)

    print(f"wavecycle_samples_target_mode: {wavecycle_samples_target_mode}")
    # wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
    custom_wavecycle_samples_target = settings.get('custom_wavecycle_samples_target', None)
    custom_selection_type = settings.get('custom_selection_type', 'mode')
    lower_bound_samples, upper_bound_samples = calculate_tolerance_bounds(wavecycle_samples_target_mode, settings['percent_tolerance'])
    
    while True:
        mode_frequency = current_sample_rate / wavecycle_samples_target_mode
        mode_note, mode_cents = frequency_to_note_and_cents(mode_frequency)

        if custom_wavecycle_samples_target:
            current_wavecycle_samples_target = custom_wavecycle_samples_target
            current_frequency = current_sample_rate / custom_wavecycle_samples_target
            current_note, current_cents = frequency_to_note_and_cents(current_frequency)
        else:
            current_wavecycle_samples_target = wavecycle_samples_target_mode
            current_frequency = mode_frequency
            current_note = mode_note
            current_cents = mode_cents

        if get_wavecycle_samples_target() == 0:
            print("\nChoose the dominant frequency. If you aren't sure, press ENTER or 1.")
            print(f"\n1. Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target_mode} samples)")
            print("\n2. Open the graph to select VISUALLY")
            print("\n3. Enter a musical NOTE (e.g., A4, C#3) or a frequency in Hz")

            choice = input_with_defaults("\nPress Enter, 1, 2 or 3 to choose: ", default="1").strip()
            if choice == "" or choice == "1":
                print(f"\nSetting wavecycle length to mode: {wavecycle_samples_target_mode} samples / {mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz")
                set_wavecycle_samples_target(wavecycle_samples_target_mode)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target_mode
                settings['custom_selection_type'] = 'mode'
                break
            elif choice == "2":
                plot_wavecycle_frequencies_with_selection(wavecycle_samples, lower_bound_samples, upper_bound_samples, current_sample_rate, wavecycle_samples_target_avg)

                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'
                break
            elif choice == "3":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(current_sample_rate / frequency)
                    set_wavecycle_samples_target(custom_wavecycle_samples_target)
                    settings['custom_wavecycle_samples_target'] = custom_wavecycle_samples_target
                    settings['custom_selection_type'] = 'manual'
                    custom_note, custom_cents = frequency_to_note_and_cents(frequency)
                    custom_frequency = frequency
                    print(f"\nSetting central frequency to {custom_note}{custom_cents:+d} / {frequency:.2f}Hz / {custom_wavecycle_samples_target} samples")
                break
            else:
                print("Invalid choice.")
                continue
        else:
            if custom_selection_type == 'mode':
                current_choice_text = f"Keep the current MODE ({current_note}{current_cents:+d} / {current_frequency:.2f}Hz / {current_wavecycle_samples_target} samples)"
            elif custom_selection_type == 'visual':
                current_choice_text = f"Keep the current VISUAL selection ({current_note}{current_cents:+d} / {current_frequency:.2f}Hz / {current_wavecycle_samples_target} samples)"
            else:
                current_choice_text = f"Keep the current MANUAL frequency ({current_note}{current_cents:+d} / {current_frequency:.2f}Hz / {current_wavecycle_samples_target} samples)"

            print(f"\nAdjust main note / central frequency")
            print(f"\n1. {current_choice_text}.")
            print("    ENTER or 1 to keep the current central frequency.")
            print(f"\n2. Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target_mode} samples)")
            print("\n3. Open the graph to select VISUALLY.")
            print("\n4. Enter a frequency in Hz or a musical note (e.g., A4, C#3)")

            choice = input_with_defaults("Your choice: ", default="1").strip()

            if choice == "" or choice == "1":
                set_wavecycle_samples_target(current_wavecycle_samples_target)
                break
            elif choice == "2":
                set_wavecycle_samples_target(wavecycle_samples_target_mode)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target_mode
                settings['custom_selection_type'] = 'mode'
                break
            elif choice == "3":
                plot_wavecycle_frequencies_with_selection(wavecycle_samples, lower_bound_samples, upper_bound_samples, current_sample_rate, wavecycle_samples_target_avg)

                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'
                break
            elif choice == "4":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(current_sample_rate / frequency)
                    set_wavecycle_samples_target(custom_wavecycle_samples_target)
                    settings['custom_wavecycle_samples_target'] = custom_wavecycle_samples_target
                    settings['custom_selection_type'] = 'manual'
                    custom_note, custom_cents = frequency_to_note_and_cents(frequency)
                    custom_frequency = frequency
                    print(f"Set to Known frequency: ({custom_note}{custom_cents:+d} / {frequency:.2f}Hz / {custom_wavecycle_samples_target} samples).")
                break
            else:
                print("Invalid choice.")

    
    seg_folder = os.path.join(get_tmp_folder(), "seg")
    ext = ".wav"

    segment_sizes = get_all_segment_sizes()
    mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext)
    mark_attack_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext)

    total_segments = len([f for f in os.listdir(seg_folder) if re.match(r'.*_seg_\d{4}.*\.wav$', f)])
    total_attack_segments = len([f for f in os.listdir(seg_folder) if '_atk.wav' in f])
    total_deviant_segments = len([f for f in os.listdir(seg_folder) if '_dev.wav' in f])
    total_normal_segments = total_segments - total_deviant_segments - total_attack_segments

    return total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples
