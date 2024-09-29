# f_sort.py

import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import numpy as np
from scipy.stats import mode as scipy_mode
from collections import Counter
import re
import soundfile as sf
from aa_common import (input_with_quit, input_with_defaults, get_wavecycle_samples, 
    get_wavecycle_samples_target, set_wavecycle_samples_target, 
    get_all_segment_sizes, get_manual_frequency_input, 
    calculate_tolerance_bounds, get_base, get_tmp_folder, 
    frequency_to_note_and_cents
)


def on_click_hist(event, y_smooth, x_smooth):
    # Ensure that the click is within valid x-axis range of the histogram
    if event.inaxes and event.button == 1:  # Only respond to left mouse button clicks
        x_min, x_max = event.inaxes.get_xlim()  # Get the x-axis limits

        # Check if the click is within the x bounds of the plot
        if x_min <= event.xdata <= x_max:
            # Get the x-coordinate from the click, representing the frequency
            clicked_frequency = event.xdata
            
            # Find the nearest frequency in x_smooth (or wavecycle lengths)
            closest_idx = (np.abs(np.array(x_smooth) - clicked_frequency)).argmin()
            closest_frequency = x_smooth[closest_idx]
            corresponding_samples = 192000 // closest_frequency

            # Convert the frequency to note and cents
            note, cents = frequency_to_note_and_cents(closest_frequency)
            
            # Set the selected wavecycle samples target
            set_wavecycle_samples_target(corresponding_samples)

            # Print information about the selected frequency
            print(f"Selected: {note}{cents:+d} / {closest_frequency:.2f}Hz / {corresponding_samples} samples")

            # Close the plot after the selection
            plt.close()
        else:
            print("Click detected outside of valid plot area. Ignoring.")

def mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    outside_tolerance_files = []
    for segment_file, segment_size in segment_sizes:
        file_path = os.path.join(seg_folder, segment_file)

        # Skip files that are already marked as attack segments
        if '_atk' in segment_file:
            continue

        # Check if the file exists before attempting to rename
        if not os.path.exists(file_path):
            continue

        # Skip renaming if the file already has a _dev suffix
        if '_dev' in segment_file:
            continue

        # Only rename if the segment size is outside the tolerance bounds
        if segment_size < lower_bound_samples or segment_size > upper_bound_samples:
            dev_name = f"{os.path.splitext(segment_file)[0]}_dev{ext}"
            dev_path = os.path.join(seg_folder, dev_name)

            # Prevent renaming if the target file already exists
            if os.path.exists(dev_path):
                print(f"File {dev_path} already exists. Skipping renaming.")
                continue

            os.rename(file_path, dev_path)
            outside_tolerance_files.append(dev_name)

    return outside_tolerance_files


def mark_attack_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext):
    within_tolerance_count = 0
    attack_segments = []

    for segment_file, segment_size in segment_sizes:
        file_path = os.path.join(seg_folder, segment_file)
        
        # Skip files that are already marked as deviant segments
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
                # print(f"Error: Could not find file {file_path} to rename to {atk_name}")
                continue
        else:
            break

    return attack_segments

def plot_wavecycle_frequencies_with_selection(wavecycle_samples, wavecycle_samples_target_mode, wavecycle_samples_target_avg, lower_bound_samples, upper_bound_samples):
    counter = Counter(wavecycle_samples.values())
    x = list(counter.keys())  # Unique integers (wavecycle lengths)
    y = list(counter.values())  # Frequency of each integer (count of each length)

    # Convert sample lengths to frequencies
    frequencies = [192000 / samples for samples in x]  # 192000 is the sample rate

    # Calculate the window size based on the tolerance range
    window_size = upper_bound_samples - lower_bound_samples

    # Ensure window size is valid and apply rolling average using np.convolve
    if window_size > 1 and len(y) >= window_size:
        y_smooth = np.convolve(y, np.ones(window_size) / window_size, mode='valid')
        x_smooth = frequencies[:len(y_smooth)]  # Convert to frequency
    else:
        y_smooth = y  # If window size is too small or y is too short, leave it as is
        x_smooth = frequencies  # No trimming needed

    fig, ax = plt.subplots(figsize=(10, 6))

    # Use scatter plot to show smoothed points without connecting lines
    ax.scatter(x_smooth, y_smooth, color='blue', label="Rolling Average")

    # Set vertical lines for mode and average frequencies
    mode_frequency = 192000 / wavecycle_samples_target_mode
    avg_frequency = 192000 / wavecycle_samples_target_avg
    ax.axvline(mode_frequency, color='red', linestyle='--', linewidth=2, label=f'Mode: {mode_frequency:.2f}Hz')
    ax.axvline(avg_frequency, color='green', linestyle='--', linewidth=2, label=f'Average: {avg_frequency:.2f}Hz')

    # Set xticks and labels with notes and frequencies
    xticks = ax.get_xticks()
    xtick_labels = [f"{frequency_to_note_and_cents(f)[0]}" for f in xticks]  # Note labels
    freq_labels = [f"{f:.2f}Hz" for f in xticks]  # Frequency labels

    # Annotate the notes inside the plot (above the x-axis)
    for i, (xtick, label) in enumerate(zip(xticks, xtick_labels)):
        ax.annotate(
            label,
            xy=(xtick, 0), xycoords=('data', 'axes fraction'),
            xytext=(0, 5), textcoords='offset points',
            ha='center', va='bottom', fontsize=10, color='black'
        )

    # Set the frequency labels below the plot
    ax.set_xticks(xticks)
    ax.set_xticklabels(freq_labels, fontsize=9, rotation=45, ha='right')

    ax.set_title('Click on the best frequency dot to work with. Usually, this is the mode')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Smoothed Frequency')
    ax.grid(True)
    ax.legend()

    # Connect the click event to the handler and pass x_smooth for frequency values
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_hist(event, y_smooth, x_smooth))

    plt.show()


# Function to calculate the average wavecycle length
def calculate_average_wavecycle_length(wavecycle_samples):
    if not wavecycle_samples:
        return 0  # Return 0 if no valid segments
    total_samples = sum(wavecycle_samples.values())
    return total_samples // len(wavecycle_samples)  # Integer division

# Function to calculate the mode wavecycle length
def calculate_mode_wavecycle_length(wavecycle_samples):
    if not wavecycle_samples:
        return 0  # Return 0 if no valid segments

    sizes = list(wavecycle_samples.values())

    if len(sizes) == 1:
        return sizes[0]  # If there's only one element, return it as the mode

    mode_result = scipy_mode(sizes)

    # Determine if mode_result.count is an array or a scalar
    if isinstance(mode_result.count, np.ndarray):
        if mode_result.count.size > 0 and mode_result.count[0] > 1:
            return mode_result.mode[0]
    else:
        if mode_result.count > 1:
            return mode_result.mode

    return sizes[0]  # Fallback: return the first element if all sizes are unique


# Main function in f_sort.py to run the process
# Inside f_sort.py

def run(settings, total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, first_iteration, processed_files):
    wavecycle_samples = get_wavecycle_samples()

    # Calculate mode and average
    wavecycle_samples_target_mode = calculate_mode_wavecycle_length(wavecycle_samples)
    wavecycle_samples_target_avg = calculate_average_wavecycle_length(wavecycle_samples)

    # Retrieve custom target from settings, if set
    custom_wavecycle_samples_target = settings.get('custom_wavecycle_samples_target', None)
    custom_selection_type = settings.get('custom_selection_type', 'mode')  # New: track whether it was 'mode', 'visual', or 'manual'

    # Calculate tolerance bounds early, before user input
    lower_bound_samples, upper_bound_samples = calculate_tolerance_bounds(wavecycle_samples_target_mode, settings['percent_tolerance'])
 
    # Menu for wavecycle selection
    custom_frequency = None
    custom_note = None
    custom_cents = None

    while True:
        mode_frequency = 192000 / wavecycle_samples_target_mode
        mode_note, mode_cents = frequency_to_note_and_cents(mode_frequency)

        # If a custom target has been set, use it; otherwise, use the mode
        if custom_wavecycle_samples_target:
            current_wavecycle_samples_target = custom_wavecycle_samples_target
            current_frequency = 192000 / custom_wavecycle_samples_target
            current_note, current_cents = frequency_to_note_and_cents(current_frequency)
        else:
            current_wavecycle_samples_target = wavecycle_samples_target_mode
            current_frequency = mode_frequency
            current_note = mode_note
            current_cents = mode_cents

        # First run (3 choices)
        if get_wavecycle_samples_target() == 0:
            print("\nChoose the dominant frequency. If you aren't sure, press ENTER or 1.")
            print(f"\n1. Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target_mode} samples) \n     MODE is a good starting point (ENTER).")
            print("\n2. Open the graph to select VISUALLY\n     If you want to choose the main frequency visually, choose this")
            print("\n3. Enter a musical NOTE (e.g., A4, C#3 -- sharps only) or a frequency in Hz \n     If you know what the note or frequency is, choose this")

            # Default to mode if Enter is pressed or "Y" is selected
            choice = input_with_defaults("\nPress Enter, 1, 2 or 3 to choose: ", default="1").strip()

            if choice == "" or choice == "1":
                print(f"\nSetting wavecycle length to mode: {wavecycle_samples_target_mode} samples / {mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz")
                set_wavecycle_samples_target(wavecycle_samples_target_mode)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target_mode  # Save mode as the custom target
                settings['custom_selection_type'] = 'mode'  # Track selection type as 'mode'
                break  # Exit the loop after valid input

            elif choice == "2":
                plot_wavecycle_frequencies_with_selection(
                    wavecycle_samples,
                    wavecycle_samples_target_mode,
                    wavecycle_samples_target_avg,
                    lower_bound_samples,
                    upper_bound_samples
                )
                # Set the custom target after graph selection
                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'  # Track selection type as 'visual'
                break  # Exit after the graph selection

            elif choice == "3":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(192000 / frequency)
                    set_wavecycle_samples_target(custom_wavecycle_samples_target)
                    settings['custom_wavecycle_samples_target'] = custom_wavecycle_samples_target  # Save manual frequency
                    settings['custom_selection_type'] = 'manual'  # Track selection type as 'manual'
                    custom_note, custom_cents = frequency_to_note_and_cents(frequency)
                    custom_frequency = frequency
                    print(f"\nSetting central frequency to {custom_note}{custom_cents:+d} / {frequency:.2f}Hz / {custom_wavecycle_samples_target} samples")
                break  # Exit after manual frequency entry

            else:
                print("Invalid choice. Please press Enter or choose a valid option (1, 2, 3).")
                continue  # Prompt again

        # Subsequent runs (4 choices, default to previous selection)
        else:
            # Display the current settings based on previous selection type
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
            print("    Reasonable choice if you are not sure.")
            print("\n3. Open the graph to select VISUALLY.")
            print("    Use this to get a better understanding if your results are off.")
            print("\n4. Enter a frequency in Hz or a musical note (e.g., A4, C#3)")

            # Press Enter defaults to option 1 (keep the current choice)
            choice = input_with_defaults("Your choice: ", default="1").strip()

            if choice == "" or choice == "1":
                print(f"Keeping the current frequency: {current_note}{current_cents:+d} / {current_frequency:.2f}Hz / {current_wavecycle_samples_target} samples.")
                set_wavecycle_samples_target(current_wavecycle_samples_target)  # Ensure the custom target is set
                break  # Exit the loop after valid input

            elif choice == "2":
                print(f"Set to the MODE ({mode_note}{mode_cents:+d} / {mode_frequency:.2f}Hz / {wavecycle_samples_target_mode} samples).")
                set_wavecycle_samples_target(wavecycle_samples_target_mode)
                settings['custom_wavecycle_samples_target'] = wavecycle_samples_target_mode  # Save mode as the custom target
                settings['custom_selection_type'] = 'mode'  # Track selection type as 'mode'
                break  # Exit the loop

            elif choice == "3":
                plot_wavecycle_frequencies_with_selection(
                    wavecycle_samples,
                    wavecycle_samples_target_mode,
                    wavecycle_samples_target_avg,
                    lower_bound_samples,
                    upper_bound_samples
                )
                # Set the custom target after graph selection
                settings['custom_wavecycle_samples_target'] = get_wavecycle_samples_target()
                settings['custom_selection_type'] = 'visual'  # Track selection type as 'visual'
                break  # Exit after graph selection

            elif choice == "4":
                frequency = get_manual_frequency_input(20.0, 20000.0)
                if frequency:
                    custom_wavecycle_samples_target = int(192000 / frequency)
                    set_wavecycle_samples_target(custom_wavecycle_samples_target)
                    settings['custom_wavecycle_samples_target'] = custom_wavecycle_samples_target  # Save manual frequency
                    settings['custom_selection_type'] = 'manual'  # Track selection type as 'manual'
                    custom_note, custom_cents = frequency_to_note_and_cents(frequency)
                    custom_frequency = frequency
                    print(f"Set to Known frequency: ({custom_note}{custom_cents:+d} / {frequency:.2f}Hz / {custom_wavecycle_samples_target} samples).")
                break  # Exit after manual frequency entry

            else:
                print("Invalid choice. Please press Enter or choose a valid option (1, 2, 3, 4).")
                continue  # Re-prompt the user


    # Now proceed with the rest of the function logic
    base = get_base()
    seg_folder = os.path.join(get_tmp_folder(), "seg")
    ext = ".wav"

    segment_sizes = get_all_segment_sizes()

    # Mark deviant segments
    mark_deviant_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext)

    # Mark attack segments
    mark_attack_segments(segment_sizes, lower_bound_samples, upper_bound_samples, base, seg_folder, ext)

    total_segments = len([f for f in os.listdir(seg_folder) if re.match(r'.*_seg_\d{4}.*\.wav$', f)])
    total_attack_segments = len([f for f in os.listdir(seg_folder) if '_atk.wav' in f])
    total_deviant_segments = len([f for f in os.listdir(seg_folder) if '_dev.wav' in f])
    total_normal_segments = total_segments - total_deviant_segments - total_attack_segments

    return total_segments, total_deviant_segments, total_normal_segments, total_attack_segments, lower_bound_samples, upper_bound_samples
