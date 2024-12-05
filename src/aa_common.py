# aa_common.py

import os
import sys
import shutil
import soundfile as sf
import resampy
from matplotlib.widgets import Button
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import re

# Global variables
source_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
ext = ".wav"
_start_file_name = ""
_start_file = ""
_base = ""
tmp_folder = ""
cpy_folder = os.path.join(tmp_folder, "cpy")
global_settings = {}  # Global settings dictionary
wavecycle_samples_target_192 = 0  # Global variable for target samples per wavecycle
selected_segment = None
wavecycle_samples = {}  # Centralized dictionary to store segment names and their sample counts
wavecycle_samples_target = 0  # Global variable to store the selected target
mode_interval = 0
autocorrelation_flag = False  # Default to not using autocorrelation
global_segment_sizes = []
highlighted_segment = []  # Track the highlighted segment so we can clear it
sample_index = 0  # Global variable to store the current sample index
wavecycle_size = 2048
frame_count = 256
accept_all_defaults = False
# Global zero threshold in decibels and window size
ZERO_THRESHOLD_DB = -40
# Number of samples to consider for rising/falling checks
ZERO_WINDOW = 32
sputter= 32 # was (frame_count - 1) * wavecycle_size


def db_to_amplitude(db_value):
    """
    Convert decibels to amplitude.
    """
    return 10 ** (db_value / 20.0)

# Global zero threshold in decibels and window size
zero_threshold = db_to_amplitude(ZERO_THRESHOLD_DB)  # Convert to amplitude

def set_all_segment_sizes(sizes):
    global global_segment_sizes
    global_segment_sizes = sizes

def get_all_segment_sizes():
    return global_segment_sizes

# Function to set the mode_interval
def set_mode_interval(samples):
    global mode_interval
    mode_interval = samples

# Function to get the mode_interval
def get_mode_interval():
    global mode_interval
    return mode_interval

# Function to set the autocorrelation_flag
def set_autocorrelation_flag(flag):
    global autocorrelation_flag
    autocorrelation_flag = flag

# Function to get the autocorrelation_flag
def get_autocorrelation_flag():
    global autocorrelation_flag
    return autocorrelation_flag

def initialize_settings():
    global global_settings
    # Initial settings with default values
    global_settings = {
        'zero_crossing_method': 1,  # Add default method for zero crossing
        'percent_tolerance': 5,  # Default tolerance percent
        'discard_atk_choice': 'N',  # Default choice for discarding attack segments
        'discard_dev_choice': 'N',  # Default choice for discarding deviant segments
        'discard_good_choice': 'N',  # Default choice for discarding good segments
        'cleanup_choice': 'Y',  # Default choice for cleanup
        'accept_current_settings': False  # Track if settings are accepted
    }
    return global_settings

def update_settings(settings):
    global global_settings
    global_settings.update(settings)
    return global_settings
'''
def get_src_folder():
    """Return the path to the 'input' folder."""
    return input_folder


def get_input_file():
    """Return the full path to the source file inside 'input' folder."""
    return _start_file
'''
def get_cpy_folder():
    tmp_folder = get_tmp_folder()
    return cpy_folder

def get_cpy_file():
    # Create a variable to store the path of the copied file
    cpy_file_path = os.path.join(cpy_folder, os.path.basename(_start_file))
    return cpy_file_path
    print(f"cpy_file_path: {cpy_file_path}")


def input_with_quit(prompt=""):
    user_input = input(prompt).strip().lower()
    if user_input == "q":
        # Delay the import of k_clean to avoid circular import issues
        from k_clean import run as run_cleanup
        
        # Ask if the user wants to run k_clean before quitting
        cleanup_choice = input_with_defaults("Do you want to run cleanup before quitting? (Y/n): ", default="y")
        if cleanup_choice == 'y':
            print("Running cleanup before quitting...")
            run_cleanup()  # Run the cleanup function from k_clean
        print("Quitting the script gracefully. Goodbye!")
        sys.exit(0)
    return user_input

def input_with_defaults(prompt="", default="y"):
    if accept_all_defaults:
        return default.lower()  # Automatically return the default option
    user_input = input_with_quit(prompt).strip().lower() or default  # Treat Enter as default
    return user_input

def note_to_frequency(note):
    """
    Convert a musical note to its corresponding frequency.
    Assumes A4 = 440Hz as standard tuning.
    """
    A4 = 440
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    # Convert note to uppercase to handle case insensitivity
    note = note.upper()

    # Validate input
    if len(note) < 2 or not note[-1].isdigit():
        print("Invalid note format. Please enter a note followed by its octave (e.g., A4, C#3).")
        return None

    octave = int(note[-1])  # Extract the octave number
    note_name = note[:-1]  # Extract the note name (without octave)

    if note_name in notes:
        # Calculate the note's index in the octave from C0 up to the note
        note_index = notes.index(note_name) - notes.index('A') + (octave - 4) * 12
        # Calculate the frequency
        return A4 * (2 ** (note_index / 12))
    else:
        print("Invalid note name. Please enter a valid musical note (e.g., A4, C#3).")
        return None

def frequency_to_note_and_cents(frequency, A4=440):
    """
    Convert frequency to the nearest note and the cents offset from that note.
    """
    # Handle invalid frequency (e.g., zero or negative)
    if frequency <= 0:
        return 'N/A', 0  # Return 'N/A' for invalid frequencies

    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    c0 = A4 * pow(2, -4.75)
    half_steps_above_c0 = round(12 * np.log2(frequency / c0))
    note = notes[half_steps_above_c0 % 12]
    octave = half_steps_above_c0 // 12
    exact_frequency = c0 * pow(2, half_steps_above_c0 / 12)
    cents = round(1200 * np.log2(frequency / exact_frequency))
    return f"{note}{octave}", cents

def get_manual_frequency_input(lowest_freq, highest_freq):
    """
    Prompt for a frequency in Hz or a musical note. Returns the frequency in Hz.
    """
    while True:
        user_input = input_with_defaults(f"     Enter the frequency in Hz (between {lowest_freq}Hz and {highest_freq}Hz), \n     Or note (no flats) with octave \n     (e.g., A3, A#3, B3, C4, C#4, D4, D#4, E4, F4, F#4, G4, G#4), \n     or press <enter> to proceed without setting it.\n     Hz, Note, or <enter>: ").strip()

        if not user_input:  # User presses Enter to skip
            return None

        if user_input.replace('.', '', 1).isdigit():  # Input is in Hz
            freq = float(user_input)
            if lowest_freq <= freq <= highest_freq:
                return freq
            else:
                print(f"Frequency out of bounds. Please enter a value between {lowest_freq}Hz and {highest_freq}Hz.")
        else:  # Input is potentially a note
            freq = note_to_frequency(user_input)
            if freq and lowest_freq <= freq <= highest_freq:
                return freq
            elif not freq:
                print(f"Invalid note. Please enter a valid musical note (e.g., A4, C#3).")
            else:
                print(f"Note frequency out of bounds. Please enter a note corresponding to a frequency between {lowest_freq}Hz and {highest_freq}Hz.")


def prompt_update_settings(settings):
    # Check if settings were already accepted
    if settings.get('accept_current_settings', False):
        print("     Proceeding with current settings.\n\n\n")
        return settings

    # Prompt to accept current settings with default as 'Y'
    accept_defaults = input_with_defaults("\n\n    Accept current settings? (Y/n, default=Y): ").strip().upper() or 'Y'

    if accept_defaults == 'Y':
        print("     Proceeding with current settings.\n\n\n")
        settings['accept_current_settings'] = True
        return settings

    # Error-checking for percent_tolerance input
    while True:
        percent_input = input_with_defaults(f"Set deviation tolerance from target length (default={settings['percent_tolerance']}%): ").strip()
        if percent_input == '':
            break
        try:
            settings['percent_tolerance'] = float(percent_input)
            break
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

    # Discard attack segments prompt with default 'N'
    settings['discard_atk_choice'] = input_with_defaults("Discard attack segments? (y/N, default=N): ").strip().upper() or 'N'

    # Discard deviant segments prompt with default 'N'
    settings['discard_dev_choice'] = input_with_defaults("Discard deviant segments? (y/N, default=N): ").strip().upper() or 'N'

    # Discard good segments prompt with default 'N'
    settings['discard_good_choice'] = input_with_defaults("Discard good segments? (y/N, default=N): ").strip().upper() or 'N'

    # Cleanup prompt with default 'Y'
    settings['cleanup_choice'] = input_with_defaults("Perform cleanup? (Y/n, default=Y): ").strip().upper() or 'Y'

    settings['accept_current_settings'] = False
    return settings


def cleanup_tmp_folder(tmp_folder, prep_file_name):
    for file in os.listdir(tmp_folder):
        file_path = os.path.join(tmp_folder, file)
        if file != prep_file_name:
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error: {e}. Skipping file: {file_path}")

def list_and_select_wav_files(source_folder):
    print("\n\nSource Files:")
    files = [f for f in os.listdir(source_folder) if f.endswith(ext)]
    files.sort(key=lambda x: x.lower())
    for i, file in enumerate(files):
        file_path = os.path.join(source_folder, file)
        data, sr = sf.read(file_path)
        bit_depth = sf.info(file_path).subtype
        channels = data.shape[1] if len(data.shape) > 1 else 1
        samples = data.shape[0]
        print(f"{i+1:>5}: {file:<40} ... {samples:>10} {sr:>10} {channels:>8} {bit_depth:>10}")
    print("\nEnter the number of the file to select, or type 'q' to exit.")
    selection = input_with_defaults("Selection: ").strip()
    if selection.lower() == 'q':
        print("Quitting script.")
        sys.exit()
    try:
        selected_index = int(selection) - 1
        if 0 <= selected_index < len(files):
            return files[selected_index]
        else:
            print("Invalid selection. Please try again.")
            return list_and_select_wav_files(source_folder)
    except ValueError:
        print("Please enter a valid number or 'q'.")
        return list_and_select_wav_files(source_folder)

def get_start_file():
    return _start_file

def get_base():
    return _base

def get_tmp_folder():
    return tmp_folder

def ensure_tmp_folder():
    """
    Ensures that both the base and tmp folders exist. If not, they are created.
    Additionally, ensures the 'cpy' folder inside 'tmp' exists.
    """
    # global cpy_folder

    if not os.path.exists(_base):
        os.makedirs(_base)
    
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    # Ensure the 'cpy' folder exists inside the 'tmp' folder
    # cpy_folder = os.path.join(tmp_folder, "cpy")
    # os.makedirs(cpy_folder, exist_ok=True)

def is_rising_from_zero(samples):
    # If stereo (2D array), check both channels separately
    if samples.ndim == 2:  # Check for stereo data
        return (np.any((samples[:, 0][:-1] <= 0) & (samples[:, 0][1:] > 0)) or
                np.any((samples[:, 1][:-1] <= 0) & (samples[:, 1][1:] > 0)))
    else:  # Mono data
        return np.any((samples[:-1] <= 0) & (samples[1:] > 0))

def is_rising_to_zero(samples):
    # If stereo (2D array), check both channels separately
    if samples.ndim == 2:  # Check for stereo data
        return (np.any((samples[:, 0][:-1] >= 0) & (samples[:, 0][1:] < 0)) or
                np.any((samples[:, 1][:-1] >= 0) & (samples[:, 1][1:] < 0)))
    else:  # Mono data
        return np.any((samples[:-1] >= 0) & (samples[1:] < 0))

def is_rising_zero_crossing(data, index):
    """Check if there is a valid rising zero-crossing starting from the given index."""
    
    # Search for the next rising zero-crossing
    for i in range(ZERO_WINDOW // 2, len(data) - ZERO_WINDOW // 2):
        if data[i - 1] < 0 and data[i] >= 0:  # Potential rising zero-crossing
            
            # Check window of 16 samples before and after the crossing
            if np.all(data[i - ZERO_WINDOW // 2 : i] < 0) and np.all(data[i : i + ZERO_WINDOW // 2] > 0):
                return True  # Found a valid rising zero-crossing
    
    return False  # No valid rising zero-crossing found
    
'''
def is_rising_zero_crossing(data, index):
    """
    Check if the waveform crosses zero from negative to positive, ignoring samples within zero tolerance.
    """
    prev_sample = data[index - 1]  # n-1 (previous sample)
    curr_sample = data[index]      # n0 (current sample)
    
    # Ensure the crossing from strictly negative to strictly positive, ignoring zero-tolerance samples
    if prev_sample < -zero_threshold and curr_sample > zero_threshold:
        return True
    return False
'''

def is_falling_zero_crossing(data, index):
    """
    Check if the waveform crosses zero from positive to negative, ignoring samples within zero tolerance.
    """
    prev_sample = data[index - 1]  # n-1 (previous sample)
    curr_sample = data[index]      # n0 (current sample)
    
    # Ensure the crossing from strictly positive to strictly negative, ignoring zero-tolerance samples
    if prev_sample > zero_threshold and curr_sample < -zero_threshold:
        return True
    return False


def check_segments(segment_path):
    """
    Validate each segment using the following criteria:
    1. Segment starts with is_rising_from_zero = True.
    2. No is_rising_zero_crossing anywhere in the segment.
    3. There is exactly one is_falling_zero_crossing.
    4. Segment ends with is_rising_to_zero = True.
    """
    data, samplerate = sf.read(segment_path)
    segment_name = os.path.basename(segment_path)
    
    # Check 1: Segment begins with is_rising_from_zero
    if not is_rising_from_zero(data[:3]):
        print(f"Segment {segment_name} failed: Does not start with is_rising_from_zero.")
        return False

    # Check 2: Segment must not contain any is_rising_zero_crossing
    rising_zero_crossings = [i for i in range(1, len(data)) if is_rising_zero_crossing(data, i)]
    
    if len(rising_zero_crossings) > 0:
        print(f"Segment {segment_name} failed: Contains {len(rising_zero_crossings)} is_rising_zero_crossing(s).")
        return False

    # Check 3: Segment must contain exactly one is_falling_zero_crossing
    falling_zero_crossings = [i for i in range(1, len(data)) if is_falling_zero_crossing(data, i)]
    
    if len(falling_zero_crossings) != 1:
        print(f"Segment {segment_name} failed: Contains {len(falling_zero_crossings)} is_falling_zero_crossing(s).")
        return False

    # Check 4: Segment ends with is_rising_to_zero
    if not is_rising_to_zero(data[-3:]):
        print(f"Segment {segment_name} failed: Does not end with is_rising_to_zero.")
        return False

    # If all checks pass
    print(f"Segment {segment_name} passed validation.")
    return True


def validate_all_segments(seg_folder):
    """
    Validate all segments in the 'seg' folder.
    """
    failed_segments = []
    
    for segment_file in os.listdir(seg_folder):
        segment_path = os.path.join(seg_folder, segment_file)
        if segment_path.endswith('.wav'):
            if not check_segments(segment_path):
                failed_segments.append(segment_file)
    
    if failed_segments:
        print(f"\nSome segments failed validation: {failed_segments}")
    else:
        print("\nAll segments passed validation.")


def is_full_wavecycle(segment, amplitude_tolerance_db=-60):
    if len(segment) < 3:
        return False

    first_sample_db = 20 * np.log10(max(abs(segment[0]), 1e-10))
    last_sample_db = 20 * np.log10(max(abs(segment[-1]), 1e-10))

    if first_sample_db > amplitude_tolerance_db or last_sample_db > amplitude_tolerance_db:
        return False

    zero_crossings = np.where(np.diff(np.signbit(segment)))[0]

    if len(zero_crossings) < 2:
        return False

    return True

def get_wavecycle_samples():
    """Return the global wavecycle_samples dictionary."""
    global wavecycle_samples
    return wavecycle_samples

def set_wavecycle_samples(segment_name, sample_count):
    """Update the global wavecycle_samples dictionary."""
    global wavecycle_samples
    wavecycle_samples[segment_name] = sample_count

def get_wavecycle_samples_target():
    """Return the global wavecycle_samples_target."""
    global wavecycle_samples_target
    return wavecycle_samples_target

def set_wavecycle_samples_target(value):
    """Set the global wavecycle_samples_target."""
    global wavecycle_samples_target
    wavecycle_samples_target = value

def get_segment_sizes(base, tmp_folder, ext):
    segment_files = [f for f in os.listdir(tmp_folder) if f.startswith(f"{base}_seg") and f.endswith(ext)]
    segment_sizes = []
    for segment_file in segment_files:
        file_path = os.path.join(tmp_folder, segment_file)
        data, _ = sf.read(file_path)
        segment_sizes.append((segment_file, len(data)))
    return segment_sizes

def recount_segments(base, tmp_folder, ext):
    segment_sizes = get_segment_sizes(base, tmp_folder, ext)
    total_segments = len(segment_sizes)
    total_deviant_segments = len([f for f in segment_sizes if '_dev' in f[0]])
    total_normal_segments = len([f for f in segment_sizes if '_seg' in f[0] and not any(suffix in f[0] for suffix in ['_atk', '_dev'])])
    total_attack_segments = len([f for f in segment_sizes if '_atk' in f[0]])
    return total_segments, total_deviant_segments, total_normal_segments, total_attack_segments

def print_segment_info(
    total_segments, 
    total_deviant_segments, 
    total_normal_segments, 
    total_attack_segments, 
    wavecycle_samples_target, 
    settings, 
    lower_bound_samples, 
    upper_bound_samples,
    discarding_atk, 
    discarding_dev, 
    discarding_good
):
    # Use seg_folder instead of tmp_folder
    seg_folder = os.path.join(get_tmp_folder(), "seg")

    # Initialize counts for smaller, larger, and exact segments for each type
    atk_smaller = atk_larger = 0
    norm_smaller = norm_larger = norm_exact = 0
    dev_smaller = dev_larger = 0
    ttl_smaller = ttl_larger = ttl_exact = 0

    # Define the correct regex patterns for attack, deviant, and normal files
    atk_pattern = re.compile(r"(.+seg_\d{4})_atk\.wav")
    dev_pattern = re.compile(r"(.+seg_\d{4})_dev\.wav")
    norm_pattern = re.compile(r"(.+seg_\d{4})\.wav")

    # Define the correct regex pattern to match valid segment files (normal, dev, or atk)
    valid_file_pattern = re.compile(r"(.+seg_\d{4})(?:_dev|_atk){0,1}\.wav")

    # Loop through files in the seg folder to count smaller, larger, and exact segments
    for segment_file in os.listdir(seg_folder):
        file_path = os.path.join(seg_folder, segment_file)

        # Only process files that match the valid segment pattern
        if valid_file_pattern.match(segment_file):
            # Calculate the segment size by reading the file data
            data, _ = sf.read(file_path)
            segment_size = len(data)

            if atk_pattern.match(segment_file):
                if segment_size < wavecycle_samples_target:
                    atk_smaller += 1
                elif segment_size > wavecycle_samples_target:
                    atk_larger += 1

            elif dev_pattern.match(segment_file):
                if segment_size < wavecycle_samples_target:
                    dev_smaller += 1
                elif segment_size > wavecycle_samples_target:
                    dev_larger += 1

            elif norm_pattern.match(segment_file):  # Normal segments without atk or dev suffix
                if segment_size < wavecycle_samples_target:
                    norm_smaller += 1
                elif segment_size > wavecycle_samples_target:
                    norm_larger += 1
                else:
                    norm_exact += 1

    # For total segments, use global_segment_sizes
    for segment_file, segment_size in get_all_segment_sizes():
        if segment_size < wavecycle_samples_target:
            ttl_smaller += 1
        elif segment_size > wavecycle_samples_target:
            ttl_larger += 1
        else:
            ttl_exact += 1

    # Calculate tolerance bounds
    lower_bound_samples, upper_bound_samples = calculate_tolerance_bounds(wavecycle_samples_target, settings['percent_tolerance'])

    # Print the segment information
    print(f"\nValid segment range within +/-{settings['percent_tolerance']}% tolerance: {lower_bound_samples} to {upper_bound_samples} samples.")
    print(f"    Number of attack segments.............................. {total_attack_segments} ({atk_smaller} < tolerance < {atk_larger})")
    print(f"    Number of normal segments.............................. {total_normal_segments} ({norm_smaller} < {norm_exact} exactly {wavecycle_samples_target} samples < {norm_larger})")
    print(f"    Number of deviant segments............................. {total_deviant_segments} ({dev_smaller} < tolerance < {dev_larger})")
    print("===============================================================================")
    print(f"    Total number of wavetable segments (all)............... {total_segments}\n")


def on_click(event, data, sr, fig, ax, wav_file, fixed_length):
    global highlighted_segment, selected_segment, sample_index  # Use global variables

    if event.inaxes:  # Ensure the click is inside the waveform plot axes
        x = event.xdata
        # Convert the x position (time in seconds) to a sample index
        sample_index = int(x * sr)

        # Ensure the selection does not go beyond the bounds of the data
        if sample_index >= len(data) - fixed_length:
            sample_index = len(data) - fixed_length
            selected_segment = data[sample_index:]
            highlight_time = np.linspace(sample_index / sr, len(data) / sr, len(selected_segment))
        elif 0 <= sample_index <= len(data) - fixed_length:
            selected_segment = data[sample_index:sample_index + fixed_length]
            highlight_time = np.linspace(sample_index / sr, (sample_index + fixed_length) / sr, fixed_length)
        else:
            sample_index = 0
            selected_segment = data[:fixed_length]
            highlight_time = np.linspace(0, fixed_length / sr, fixed_length)

        # Remove the previous highlight
        if highlighted_segment:
            for line in highlighted_segment:
                line.remove()  # Remove the previously drawn highlighted segment
            highlighted_segment = []

        # Plot the new highlighted segment
        if data.ndim == 2:  # Stereo
            highlighted_segment = [
                ax.plot(highlight_time, selected_segment[:, 0], color='orange', label="Selected Left Channel", linewidth=2)[0],
                ax.plot(highlight_time, selected_segment[:, 1], color='orange', label="Selected Right Channel", linewidth=2)[0]
            ]
        else:  # Mono
            highlighted_segment = [ax.plot(highlight_time, selected_segment, color='orange', label="Selected Segment", linewidth=2)[0]]

        # Redraw the figure to update the highlight
        fig.canvas.draw()

        # Print for debugging: Start and end sample indices
        print(f"Selected segment starts at sample {sample_index}, ends at {sample_index + len(selected_segment)}")

def plot_wav_file_interactive(wav_file, fixed_length=None):
    global data, sr, fig, ax, highlighted_segment  # Make these global to retain data across functions
    data, sr = sf.read(wav_file)
    time = np.linspace(0, len(data) / sr, num=len(data))

    # Set the default selection to the first fixed_length samples
    if fixed_length is not None:
        start_index = 0
        end_index = fixed_length
    else:
        start_index = 0
        end_index = min(len(data), 256 * 2048)  # Default to first 524288 samples

    # Clear the previous figure and axes if they exist
    if 'fig' in globals() and plt.fignum_exists(fig.number):
        plt.close(fig)

    # Create a new figure and axes
    fig, ax = plt.subplots(figsize=(15, 5))

    # Plot the channels
    if data.ndim == 2:  # Stereo
        ax.plot(time, data[:, 0], color='red', label="Left Channel")
        ax.plot(time, data[:, 1], color='blue', label="Right Channel")
    else:  # Mono
        ax.plot(time, data, color='blue', label="Mono Channel")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Wav File Visualization")
    ax.legend()

    # Highlight the default selection in orange
    highlight_time = time[start_index:end_index]
    if data.ndim == 2:  # Stereo
        highlighted_segment = [
            ax.plot(highlight_time, data[start_index:end_index, 0], color='orange', label="Selected Left Channel", linewidth=2)[0],
            ax.plot(highlight_time, data[start_index:end_index, 1], color='orange', label="Selected Right Channel", linewidth=2)[0]
        ]
    else:  # Mono
        highlighted_segment = [ax.plot(highlight_time, data[start_index:end_index], color='orange', label="Selected Segment", linewidth=2)[0]]

    # Add text to the plot
    ax.text(0.5, 0.9, 'Click to select a different segment', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)

    # Add Proceed and Cancel buttons
    ax_proceed = plt.axes([0.7, 0.01, 0.1, 0.05])
    ax_cancel = plt.axes([0.81, 0.01, 0.1, 0.05])
    btn_proceed = Button(ax_proceed, 'Proceed')
    btn_cancel = Button(ax_cancel, 'Cancel')

    # Button actions
    btn_proceed.on_clicked(lambda event: on_proceed(event, wav_file))  # Pass wav_file to on_proceed
    btn_cancel.on_clicked(lambda event: on_cancel(event, wav_file))

    # Connect the click event to the on_click handler, only allow clicks inside the graph axes (not buttons)
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click(event, data, sr, fig, ax, wav_file, fixed_length) if event.inaxes == ax else None)

    plt.show()

def on_proceed(event, wav_file):
    global selected_segment  # Ensure we're using the global variable

    if selected_segment is not None:
        # Save the selected segment directly to the upsampled file (overwrite the prep_192k32b file)
        save_selection_to_prep(selected_segment, wav_file)
        print(f"Selection saved to {wav_file}. Proceeding...")
    
    plt.close('all')  # Close the plot window after saving

def on_cancel(event, wav_file):
    plt.close('all')  # Close all plots
    print("No segment selected. Proceeding with the full waveform.")  # Notify the user in the console
    # Here you can handle the logic to use the full waveform as needed

def save_selection_to_prep(selected_segment, wav_file):
    """
    Overwrite the original upsampled file with the selected segment.
    """
    # Overwrite the upsampled file (wav_file) with the selected segment
    sf.write(wav_file, selected_segment, 192000, subtype='FLOAT')
    print(f"Selection saved to {wav_file}")

def highlight_selection(data, sr, start_index, fixed_length=None):
    if fixed_length:
        end_index = start_index + fixed_length
    else:
        end_index = start_index + 256 * 2048  # Default to 524288 samples
    return data[start_index:end_index]


def plot_selection_graph(data, sr, wav_file):
    time = np.linspace(0, len(data) / sr, num=len(data))

    # Clear the previous figure and axes if they exist
    if 'fig' in globals() and plt.fignum_exists(fig.number):
        plt.close(fig)

    # Create a new figure and axes
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(time, data, label="Wav File")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Selected Wavetable Segment")
    ax.legend()
    
    # Highlight the selected segment
    ax.plot(time[:len(selected_segment)], selected_segment, color='orange', label="Selected Segment")

    ax_yes = plt.axes([0.7, 0.05, 0.1, 0.075])
    ax_no = plt.axes([0.81, 0.05, 0.1, 0.075])
    btn_yes = Button(ax_yes, 'Yes')
    btn_no = Button(ax_no, 'No')

    def on_yes(event):
        plt.close('all')  # Close all plots and proceed to the next step

    def on_no(event):
        plt.close(fig)  # Close the current plot and reopen the selection plot
        plot_wav_file_interactive(wav_file)  # Restart the selection process

    btn_yes.on_clicked(on_yes)
    btn_no.on_clicked(on_no)
    
    plt.show(block=False)  # Non-blocking show for the second plot to allow interaction

    # Manually process events to keep the interaction responsive
    while plt.get_fignums():
        plt.pause(0.1)
def calculate_tolerance_bounds(wavecycle_samples_target, tolerance_percent):
    plus_minus_tolerance = tolerance_percent / 100.0
    lower_bound = wavecycle_samples_target * (1 - plus_minus_tolerance)
    upper_bound = wavecycle_samples_target * (1 + plus_minus_tolerance)
    
    # Round to nearest integer
    return round(lower_bound), round(upper_bound)

# Function to interpolate segments by ratios
def interpolate_seg(data, original_sr):
    """
    Interpolate a waveform segment to wavecycle_size (2048) samples in length.

    Parameters:
    - data: np.ndarray, the input waveform (audio segment).
    - original_sr: int, the original sample rate of the waveform.

    Returns:
    - np.ndarray, the resampled waveform segment with exactly wavecycle_size samples.
    """
    global wavecycle_size  # Declare wavecycle_size as global to access the global variable

    original_length = len(data)
    target_sample_rate = int(round(wavecycle_size * original_sr / original_length))
    interpolated = resampy.resample(data, original_sr, target_sample_rate)

    # Ensure the interpolated segment is the exact target length (trim or pad if necessary)
    if len(interpolated) > wavecycle_size:
        # Trim excess samples
        interpolated = interpolated[:wavecycle_size]
    elif len(interpolated) < wavecycle_size:
        # Pad with zeros to reach the target length
        padding = np.zeros(wavecycle_size - len(interpolated))
        interpolated = np.concatenate((interpolated, padding))

    return interpolated


def resample_to_power_of_two(single_cycles_192k32b, wavecycle_samples_target_192):
    nearest_192_higher_pwr2 = int(2**np.ceil(np.log2(wavecycle_samples_target_192)))

    base = get_base()
    tmp_folder = get_tmp_folder()
    single_cycles_pwr2_any = os.path.join(tmp_folder, f'192k_pwr2_{nearest_192_higher_pwr2}')

    if not os.path.exists(single_cycles_pwr2_any):
        os.makedirs(single_cycles_pwr2_any, exist_ok=True)

    print(f"Source 192 waveforms folder set to: {single_cycles_192k32b}")
    print(f"Resampled waveforms folder set to: {single_cycles_pwr2_any}")

    pwr_of_2_192_ratio = nearest_192_higher_pwr2 / wavecycle_samples_target_192
    pwr_of_2_192_target = int(round(wavecycle_samples_target_192 * pwr_of_2_192_ratio))

    for filename in os.listdir(single_cycles_192k32b):
        if filename.endswith('.wav'):
            input_file_path = os.path.join(single_cycles_192k32b, filename)
            data, original_sr = sf.read(input_file_path)
            interpolated_data = interpolate_seg(data, original_sr, pwr_of_2_192_target)
            pwr2_192_file_path = os.path.join(single_cycles_pwr2_any, filename)
            sf.write(pwr2_192_file_path, interpolated_data, original_sr, subtype='FLOAT')
    return single_cycles_pwr2_any

def perform_cleanup():
    """
    Performs cleanup by deleting the tmp folder.
    """
    tmp_folder = get_tmp_folder()

    try:
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
            print(f"Deleted folder: {tmp_folder}")

        # print("Temporary folder cleanup completed.")
    except Exception as e:
        print(f"An error occurred during tmp folder cleanup: {e}")

def delete_base_folder():
    """
    Performs cleanup by deleting the tmp folder.
    """
    base_folder = get_base()

    try:
        if os.path.exists(base_folder):
            shutil.rmtree(base_folder)
            print(f"Deleted folder: {base_folder}")

        # print("Temporary folder cleanup completed.")
    except Exception as e:
        print(f"An error occurred during tmp folder cleanup: {e}")
'''
def delete_base_folder():
    """
    Prompts the user to decide whether to delete the base folder and its contents.
    """
    base_folder = get_base()
    if not os.path.exists(base_folder):
        print(f"Base folder {base_folder} does not exist.")
        return

    # Ask the user for confirmation
    delete_base = input_with_defaults(f"Do you want to delete the base folder '{base_folder}' and all its contents? (Y/n): ").strip().lower() or 'y'
    if delete_base == 'y':
        try:
            shutil.rmtree(base_folder)
            print(f"Deleted base folder: {base_folder}")
        except Exception as e:
            print(f"An error occurred during base folder cleanup: {e}")
    else:
        print("Base folder not deleted.")

'''