# f_sort.py

import os
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re
import soundfile as sf

def on_click_hist(event, y_smooth, x_smooth):
    from aa_common import frequency_to_note_and_cents, set_wavecycle_samples_target  # Local import
    if event.inaxes and event.button == 1:
        x_min, x_max = event.inaxes.get_xlim()
        if x_min <= event.xdata <= x_max:
            clicked_frequency = event.xdata
            closest_idx = (np.abs(np.array(x_smooth) - clicked_frequency)).argmin()
            closest_frequency = x_smooth[closest_idx]
            corresponding_samples = 192000 // closest_frequency
            note, cents = frequency_to_note_and_cents(closest_frequency)
            set_wavecycle_samples_target(corresponding_samples)
            print(f"Selected: {note}{cents:+d} / {closest_frequency:.2f}Hz / {corresponding_samples} samples")
            plt.close()
        else:
            print("Click detected outside of valid plot area. Ignoring.")

def mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    # This function uses no aa_common imports, so no changes needed here
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

def plot_wavecycle_frequencies_with_selection(wavecycle_samples, wavecycle_samples_target_mode, wavecycle_samples_target_avg, lower_bound_samples, upper_bound_samples):
    from aa_common import frequency_to_note_and_cents, set_wavecycle_samples_target  # Local import

    counter = Counter(wavecycle_samples.values())
    x = list(counter.keys())
    y = list(counter.values())
    frequencies = [192000 / samples for samples in x]
    window_size = upper_bound_samples - lower_bound_samples
    if window_size > 1 and len(y) >= window_size:
        y_smooth = np.convolve(y, np.ones(window_size) / window_size, mode='valid')
        x_smooth = frequencies[:len(y_smooth)]
    else:
        y_smooth = y
        x_smooth = frequencies

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_smooth, y_smooth, color='blue', label="Rolling Average")
    mode_frequency = 192000 / wavecycle_samples_target_mode
    avg_frequency = 192000 / wavecycle_samples_target_avg
    ax.axvline(mode_frequency, color='red', linestyle='--', linewidth=2, label=f'Mode: {mode_frequency:.2f}Hz')
    ax.axvline(avg_frequency, color='green', linestyle='--', linewidth=2, label=f'Average: {avg_frequency:.2f}Hz')

    xticks = ax.get_xticks()
    xtick_labels = [f"{frequency_to_note_and_cents(f)[0]}" for f in xticks]
    freq_labels = [f"{f:.2f}Hz" for f in xticks]
    for i, (xtick, label) in enumerate(zip(xticks, xtick_labels)):
        ax.annotate(
            label,
            xy=(xtick, 0), xycoords=('data', 'axes fraction'),
            xytext=(0, 5), textcoords='offset points',
            ha='center', va='bottom', fontsize=10, color='black'
        )
    ax.set_xticks(xticks)
    ax.set_xticklabels(freq_labels, fontsize=9, rotation=45, ha='right')

    ax.set_title('Click on the best frequency dot to work with. Usually, this is the mode')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Smoothed Frequency')
    ax.grid(True)
    ax.legend()
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_hist(event, y_smooth, x_smooth))
    plt.show()

def calculate_average_wavecycle_length(wavecycle_samples):
    if not wavecycle_samples:
        return 0
    total_samples = sum(wavecycle_samples.values())
    return total_samples // len(wavecycle_samples)

def calculate_mode_wavecycle_length(wavecycle_samples):
    from scipy.stats import mode as scipy_mode
    if not wavecycle_samples:
        return 0
    sizes = list(wavecycle_samples.values())
    if len(sizes) == 1:
        return sizes[0]
    mode_result = scipy_mode(sizes)
    if isinstance(mode_result.count, np.ndarray):
        if mode_result.count.size > 0 and mode_result.count[0] > 1:
            return mode_result.mode[0]
    else:
        if mode_result.count > 1:
            return mode_result.mode
    return sizes[0]

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, processed_files):
    from aa_common import (get_wavecycle_samples, get_wavecycle_samples_target, set_wavecycle_samples_target,
                           get_all_segment_sizes, get_manual_frequency_input, calculate_tolerance_bounds, 
                           get_base, get_tmp_folder, input_with_defaults, frequency_to_note_and_cents)

    wavecycle_samples = get_wavecycle_samples()
    wavecycle_samples_target_mode = calculate_mode_wavecycle_length(wavecycle_samples)
    wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
    custom_wavecycle_samples_target = settings.get('custom_wavecycle_samples_target', None)
    custom_selection_type = settings.get('custom_selection_type', 'mode')
    lower_bound_samples, upper_bound_samples = calculate_tolerance_bounds(wavecycle_samples_target_mode, settings['percent_tolerance'])
    
    while True:
        mode_frequency = 192000 / wavecycle_samples_target_mode
        mode_note, mode_cents = frequency_to_note_and_cents(mode_frequency)

        if custom_wavecycle_samples_target:
            current_wavecycle_samples_target = custom_wavecycle_samples_target
            current_frequency = 192000 / custom_wavecycle_samples_target
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
                plot_wavecycle_frequencies_with_selection(wavecycle_samples, wavecycle_samples_target_mode, wavecycle_samples_target_avg, lower_bound_samples, upper_bound_samples)
                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'
                break
            elif choice == "3":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(192000 / frequency)
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
                plot_wavecycle_frequencies_with_selection(wavecycle_samples, wavecycle_samples_target_mode, wavecycle_samples_target_avg, lower_bound_samples, upper_bound_samples)
                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'
                break
            elif choice == "4":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(192000 / frequency)
                    set_wavecycle_samples_target(custom_wavecycle_samples_target)
                    settings['custom_wavecycle_samples_target'] = custom_wavecycle_samples_target
                    settings['custom_selection_type'] = 'manual'
                    custom_note, custom_cents = frequency_to_note_and_cents(frequency)
                    custom_frequency = frequency
                    print(f"Set to Known frequency: ({custom_note}{custom_cents:+d} / {frequency:.2f}Hz / {custom_wavecycle_samples_target} samples).")
                break
            else:
                print("Invalid choice.")

    base = get_base()
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
