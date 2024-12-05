import os
import shutil
import aa_common
import h_interpolate_s
import j_wvtblr_s
import k_clean
import tkinter as tk
from tkinter import filedialog

def select_folder():
    """
    Opens a folder selection dialog and returns the selected folder path.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    folder_path = filedialog.askdirectory(title="Select the Singles Folder")
    if not folder_path:
        print("No folder selected. Exiting.")
        exit(1)
    return folder_path

def process_singles(singles_folder):
    # Initialize global settings
    aa_common.global_settings = aa_common.initialize_settings()
    
    # Get all wavecycle files in the selected folder
    wavecycle_files = sorted([f for f in os.listdir(singles_folder) if os.path.isfile(os.path.join(singles_folder, f))])
    if not wavecycle_files:
        print("No wavecycle files found in the selected folder!")
        return

    # Determine the base name from the first file
    base_name = os.path.splitext(wavecycle_files[0])[0].rstrip("0123456789 ").strip()
    aa_common._base = base_name
    aa_common.tmp_folder = os.path.join(aa_common._base, "tmp")
    
    # Create necessary folders
    seg_folder = os.path.join(aa_common.tmp_folder, "seg")
    if not os.path.exists(seg_folder):
        os.makedirs(seg_folder)
    frames_folder = os.path.join(aa_common.tmp_folder, "frames")
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)
    concat_folder = os.path.join(aa_common.tmp_folder, "concat")
    if not os.path.exists(concat_folder):
        os.makedirs(concat_folder)

    # Copy wavecycles to seg folder
    for wavecycle_file in wavecycle_files:
        src_path = os.path.join(singles_folder, wavecycle_file)
        dst_path = os.path.join(seg_folder, wavecycle_file)
        shutil.copy2(src_path, dst_path)
    
    print(f"Copied {len(wavecycle_files)} wavecycle files to {seg_folder}")

    # Start from h_interpolate
    print("Starting interpolation process...")
    h_interpolate_s.run(seg_folder, frames_folder)

    # Continue with the rest of the pipeline
    wavetables_folder = os.path.join(os.getcwd(), 'wavetables')
    j_wvtblr_s.run(frames_folder, concat_folder, base_name, wavetables_folder)
    k_clean.run()

    print(f"Finished processing wavecycles in {singles_folder}.\n")

def main():
    help = '''
    This script takes a folder of single wavecycle files 
    and creates a wavetable from all the files in that 
    folder in alphabetical order. To proceed, find or 
    create a folder with single wavecycle wav files in 
    it and select it in the next step. 

    '''
    print(help)
    input("Press Enter to proceed...")
    
    # Open folder selection dialog
    singles_folder = select_folder()
    process_singles(singles_folder)

if __name__ == "__main__":
    main()
