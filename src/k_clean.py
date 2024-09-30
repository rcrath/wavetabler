
# k_clean

import os
import shutil
import debug  # Import the debug script when needed

def run():
    # Get the base folder directly
    from aa_common import input_with_quit, input_with_defaults, get_base, perform_cleanup, delete_base_folder
    base_folder = get_base()

    # Print the base folder path for verification
    # print(f"base_folder path: {base_folder}")

   # Ask the user if they want to run the debug checks with default as 'N' (no)
    run_debug = input_with_defaults("Do you want to run debug checks before cleanup? (y/N): ", default='n').strip().lower()

    if run_debug == 'y':
        # Run the debug checks on the base folder
        # print("Running debug checks before cleanup...")
        debug.run_debug(base_folder)  # Pass the base folder to the debug script
    else:
        # print("Skipping debug checks.")
        pass

    # After the debug report (or if debug is skipped), ask to delete the tmp folder
    cleanup = input_with_defaults("Do you want to delete the tmp folder? (Y/n): ").strip().lower() or 'y'
    
    if cleanup == 'y':
        delete_base_folder()  # Call cleanup function from aa_common (no argument needed)
        print("Temporary folder deleted.")
    else:
        print("Temporary folder not deleted.")

    # print("Cleanup process completed.")
