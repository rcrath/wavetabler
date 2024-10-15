#!/bin/bash

# Create a virtual environment named 'wvtbl_nix'
python3.11 -m venv wvtbl_nix

# Activate the virtual environment
source wvtbl_nix/bin/activate

# Install required packages from requirements.txt
pip install -r requirements.txt

# Optional: You can uncomment these lines if you prefer manual installation of packages
# pip install numpy scipy librosa resampy soundfile pydub matplotlib pandas tabulate
alias wvtbl=./wvtbl.sh
