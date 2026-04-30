
# k_clean

import os
import shutil
# import debug  # Disabled: debug option is broken for now

def run():
    # Get the base folder directly
    from aa_common import input_with_quit, input_with_defaults, get_base, perform_cleanup, delete_base_folder
    base_folder = get_base()

    # Debug option disabled — broken for now. Re-enable by uncommenting both
    # the `import debug` above and the prompt block below.
    # run_debug = input_with_defaults("Do you want to run debug checks before cleanup? (y/N): ", default='n').strip().lower()
    # if run_debug == 'y':
    #     debug.run_debug(base_folder)

    cleanup = input_with_defaults("Do you want to delete the tmp folder? (Y/n): ").strip().lower() or 'y'
    
    if cleanup == 'y':
        delete_base_folder()  # Call cleanup function from aa_common (no argument needed)
        print("Temporary folder deleted.")
    else:
        print("Temporary folder not deleted.")

    # print("Cleanup process completed.")
