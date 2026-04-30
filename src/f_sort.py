

# f_sort.py

import os
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re
import soundfile as sf
from tqdm import tqdm
from aa_common import (
    get_wavecycle_samples_target,
    get_autocorrelation_flag,
    get_mode_interval,
    set_mode_interval,
    calculate_adaptive_tolerance_percentage,
    validate_segment_distribution,
)

def autocorrelation_sort(wavecycle_samples):
    if get_autocorrelation_flag():
        # FIX #22: For autocorrelation, use AVERAGE (not mode) as the primary target.
        # Mode is unstable for autocorr-derived periods because the period estimate
        # often varies by ±1 sample, scattering the mode and leaving zero normal segments.
        wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
        mode_interval = get_mode_interval()
        print(f"autocorrelation -- using avg: {wavecycle_samples_target_avg} (mode was: {mode_interval})")
        return wavecycle_samples_target_avg, wavecycle_samples_target_avg
    else:
        mode_interval = calculate_mode_wavecycle_length(wavecycle_samples)
        wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)
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

def mark_attack_segments_by_onset(segment_sizes, seg_folder, ext, settings):
    """
    Burg LP-residual onset detection on the original cpy audio. Any segment
    whose [start, start+length) range contains a detected onset is marked _atk.

    Replaces the old length-stability heuristic. Works the same way in
    zero-cross and autocorrelation modes — the segmentation method doesn't
    affect onset detection because we run on the un-segmented source audio.
    """
    import soundfile as sf
    from collections import defaultdict
    import aa_common
    import onset_burg

    sensitivity = settings.get('onset_sensitivity', 3.0)
    cpy_folder = os.path.join(aa_common.get_base(), "tmp", "cpy")

    # Group segments by their source file prefix (e.g. "flange220_Mono"),
    # extracted from segment names like "flange220_Mono_seg_0001.wav". Each
    # prefix has its own cpy file and gets its own onset pass.
    by_prefix = defaultdict(list)
    seg_re = re.compile(r"^(.+?)_seg_\d{4}")
    for seg_name, seg_size in segment_sizes:
        m = seg_re.match(seg_name)
        if m:
            by_prefix[m.group(1)].append((seg_name, seg_size))

    positions = aa_common.get_segment_positions()
    attack_segments = []

    for prefix, segs in by_prefix.items():
        cpy_path = os.path.join(cpy_folder, f"{prefix}{ext}")
        if not os.path.exists(cpy_path):
            print(f"  [onset] cpy file not found for {prefix}, skipping")
            continue

        audio, sr = sf.read(cpy_path)
        print(f"  [onset] running Burg detector on {prefix} (sensitivity={sensitivity})")
        onsets = onset_burg.detect_onsets(audio, sr, sensitivity=sensitivity)
        print(f"  [onset] detected {len(onsets)} onset(s)")

        if not onsets:
            continue

        # Build a sorted (start, end, name) list for this prefix.
        spans = []
        for seg_name, seg_size in segs:
            start = positions.get(seg_name)
            if start is None:
                continue
            spans.append((start, start + seg_size, seg_name))
        spans.sort()
        starts = [s[0] for s in spans]
        if not spans:
            continue

        # e_seg's segmentation often has gaps (and never starts at sample 0
        # because it waits for the first rising-from-zero pattern). So onsets
        # frequently fall in gaps or before the first segment. Map each onset
        # to the closest segment within a 50ms window:
        #   - inside a segment -> that segment
        #   - in a gap or before first -> the segment whose START is just after
        #     the onset (the cycle that begins after the transient settles)
        max_gap_samples = int(0.05 * sr)  # 50ms

        import bisect
        marked = set()
        for onset in onsets:
            # First, check if onset falls inside any segment (right-most start <= onset).
            idx_left = bisect.bisect_right(starts, onset) - 1
            if 0 <= idx_left < len(spans):
                s, e, n = spans[idx_left]
                if s <= onset < e:
                    if n not in marked:
                        marked.add(n)
                        attack_segments.append(n)
                    continue

            # Otherwise, find segment that starts soon after the onset.
            idx_right = bisect.bisect_left(starts, onset)
            if idx_right < len(spans):
                s, e, n = spans[idx_right]
                if s - onset <= max_gap_samples and n not in marked:
                    marked.add(n)
                    attack_segments.append(n)
                    continue
            # No reasonable match — this onset is in a wide gap or past the last segment.

    # Apply renames. A segment may have been renamed to _dev by mark_deviant —
    # in that case rename the _dev file to _atk (attack supersedes deviant
    # because the user usually treats _atk and _dev with the same Y/n choice
    # and an onset is the more specific signal).
    for seg_name in attack_segments:
        base_no_ext = os.path.splitext(seg_name)[0]
        atk_path = os.path.join(seg_folder, f"{base_no_ext}_atk{ext}")
        original = os.path.join(seg_folder, seg_name)
        dev_path = os.path.join(seg_folder, f"{base_no_ext}_dev{ext}")
        if os.path.exists(original):
            os.rename(original, atk_path)
        elif os.path.exists(dev_path):
            os.rename(dev_path, atk_path)
        # else: nothing to rename — file may have been removed for another reason

    print(f"  [onset] marked {len(attack_segments)} segment(s) as _atk")
    return attack_segments


def mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    outside_tolerance_files = []
    for segment_file, segment_size in tqdm(segment_sizes, desc="  marking deviants", unit="seg", leave=False):
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
    within_tolerance_count = 0
    attack_segments = []
    for segment_file, segment_size in tqdm(segment_sizes, desc="  marking attacks", unit="seg", leave=False):
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

    mode_frequency = current_sample_rate / get_mode_interval()
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
        set_mode_interval(sizes[0])  # Set the mode interval
        return sizes[0]

    mode_result = scipy_mode(sizes)
    if isinstance(mode_result.count, np.ndarray):
        if mode_result.count.size > 0 and mode_result.count[0] > 1:
            set_mode_interval(mode_result.mode[0])  # Set the mode interval
            return mode_result.mode[0]
    else:
        if mode_result.count > 1:
            set_mode_interval(mode_result.mode)  # Set the mode interval
            return mode_result.mode

    set_mode_interval(sizes[0])  # Set the mode interval as a fallback
    return sizes[0]

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, processed_files):
    from aa_common import (get_wavecycle_samples, get_wavecycle_samples_target, set_wavecycle_samples_target,
                           get_all_segment_sizes, get_manual_frequency_input, calculate_tolerance_bounds, 
                           get_base, get_tmp_folder, input_with_defaults, frequency_to_note_and_cents)
    print(">>> [DEBUG] Retrieved wavecycle_samples_target in f_sort.run:", get_wavecycle_samples_target())
    wavecycle_samples_target = get_wavecycle_samples_target()
    print("Retrieved wavecycle_samples_target in f_sort:", wavecycle_samples_target)
    set_mode_interval(wavecycle_samples_target)  # Set the mode interval
    print(">>> [DEBUG] Retrieved wavecycle_samples_target in f_sort.run:", get_wavecycle_samples_target())

    
    base = get_base()
    # Construct the path to the file in base/tmp/cpy
    cpy_folder = os.path.join(base, "tmp", "cpy")
    cpy_file = os.path.join(cpy_folder, f"{base}.wav")

    # Use sf.read to get the sample rate
    _, current_sample_rate = sf.read(cpy_file)
    # set some variables
    wavecycle_samples = get_wavecycle_samples()
    autocorrelation_sort(wavecycle_samples)
    wavecycle_samples_target, wavecycle_samples_target_avg = autocorrelation_sort(wavecycle_samples)

    print(f"wavecycle_samples_target: {wavecycle_samples_target}")
    custom_wavecycle_samples_target = settings.get('custom_wavecycle_samples_target', None)
    custom_selection_type = settings.get('custom_selection_type', 'mode')

    # FIX #22: Use a wider, adaptive tolerance when autocorrelation is active.
    # Autocorr period estimates have natural ±1-sample jitter, so the default
    # 5% tolerance often classifies every segment as deviant.
    if get_autocorrelation_flag():
        base_tolerance = settings.get('percent_tolerance_autocorr', 10)
        if settings.get('use_adaptive_tolerance', True):
            settings['percent_tolerance'] = calculate_adaptive_tolerance_percentage(
                wavecycle_samples, base_tolerance
            )
            print(f"Autocorrelation adaptive tolerance: {settings['percent_tolerance']:.1f}%")
        else:
            settings['percent_tolerance'] = base_tolerance

    lower_bound_samples, upper_bound_samples = calculate_tolerance_bounds(wavecycle_samples_target, settings['percent_tolerance'])
    
    while True:
        from aa_common import get_wavecycle_samples_target, clear_screen
        clear_screen()
        # The global target is 0 until the user picks one. Until then, fall back
        # to the autocorrelation-derived local value so the prompt has something
        # to show and we don't divide by zero.
        global_target = get_wavecycle_samples_target()
        if global_target:
            wavecycle_samples_target = global_target
        if not wavecycle_samples_target:
            raise ValueError(
                "wavecycle_samples_target is 0 — autocorrelation_sort returned no usable target. "
                "This usually means the upstream segmentation (e_seg/d_interval) found no segments."
            )
        mode_frequency = current_sample_rate / wavecycle_samples_target
        mode_note, mode_cents = frequency_to_note_and_cents(mode_frequency)

        if custom_wavecycle_samples_target:
            current_wavecycle_samples_target = custom_wavecycle_samples_target
            current_frequency = current_sample_rate / custom_wavecycle_samples_target
            current_note, current_cents = frequency_to_note_and_cents(current_frequency)
        else:
            current_wavecycle_samples_target = wavecycle_samples_target
            current_frequency = mode_frequency
            current_note = mode_note
            current_cents = mode_cents

        if get_wavecycle_samples_target() == 0:
            print("\nChoose the dominant frequency. If you aren't sure, press ENTER or 1.")
            print(f"\n1. Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target} samples)")
            print("\n2. Open the graph to select VISUALLY")
            print("\n3. Enter a musical NOTE (e.g., A4, C#3) or a frequency in Hz")

            choice = input_with_defaults("\nPress Enter, 1, 2 or 3 to choose: ", default="1").strip()
            if choice == "" or choice == "1":
                print(f"\nSetting wavecycle length to mode: {wavecycle_samples_target} samples / {mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz")
                set_wavecycle_samples_target(wavecycle_samples_target)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target
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
            print(f"\n2. Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target} samples)")
            print("\n3. Open the graph to select VISUALLY.")
            print("\n4. Enter a frequency in Hz or a musical note (e.g., A4, C#3)")

            choice = input_with_defaults("Your choice: ", default="1").strip()

            if choice == "" or choice == "1":
                set_wavecycle_samples_target(current_wavecycle_samples_target)
                break
            elif choice == "2":
                set_wavecycle_samples_target(wavecycle_samples_target)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target
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

    # OLD length-based attack heuristic — disabled. It only marked segments at
    # the very start of the file before the length-stability detector found 3
    # in-tolerance cycles in a row. Misses real attacks in pitched/clean inputs
    # and false-fires in autocorr mode (always marks first 2 segments). Replaced
    # by Burg LP-residual onset detection on the original audio.
    # mark_attack_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext)
    mark_attack_segments_by_onset(segment_sizes, seg_folder, ext, settings)

    total_segments = len([f for f in os.listdir(seg_folder) if re.match(r'.*_seg_\d{4}.*\.wav$', f)])
    total_attack_segments = len([f for f in os.listdir(seg_folder) if '_atk.wav' in f])
    total_deviant_segments = len([f for f in os.listdir(seg_folder) if '_dev.wav' in f])
    total_normal_segments = total_segments - total_deviant_segments - total_attack_segments

    return total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples
