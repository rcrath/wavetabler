# wavetabler
 Create wavetables for Serum, Vital, etc from any short wav file.

 ## description
 wavetabler creates 2048 sample X 256 frames wavetables that can be imported as fixed size 2048 in Serum's wavetable editor import screen.  Have not tested on other synths but should be able to figure it out if you rtm for that synth I think.  

 This is an alpha release.  It works for me, ymmv.  I have a Linux and a Windows box and have tested it on both.

To download, click where it says code just above and to the right of the file listing and Download the zip file. 

move the zip file to where you want to run it, referably outside the reach of cloud services like dropbox and one drive since the scripts generate scads of tmp files and cloud services try to grab the all and interfere with the script. 

Unzip the file and then navigate into the wavetabler folder.  There you will find the following tree:  

 ```
wavetabler
│   .gitattributes
│   LICENSE
│   Makefile
│   README.md
│   requirements.txt
│   setpy.cmd # Windows: run first time only
│   setpy.sh # Linux/MacOS: : run first time only \*see below
│   setup.py
│   wvtbl.cmd # this is your windows command. Type `wvtbl` to run
│   wvtbl.sh # this is your linux/<acOS command, run as `./wvtbl.sh` \*see below
│
├───build # temporarily included, might not be necessary.
│   └───bdist.win-amd64
├───dist #currently not working
│       wavetabler-1.0-py3-none-any.whl
│       wavetabler-1.0.tar.gz
│
├───input # short mono wave files go here to be wavetablered
│       00_README.md
│       flange220.wav
│       sinetable.wav
│
├───src # the actual python code
│   │   aa_common.py
│   │   a_wvtbl.py
│   │   b_menu.py
│   │   c_upsample.py
│   │   debug.py
│   │   e_seg.py
│   │   f_sort.py
│   │   g_choose.py
│   │   h_interpolate.py
│   │   j_wvtblr.py
│   │   k_clean.py
│   │
│   └───__pycache__ #probably will delete
...
│
├───wavetabler.egg-info #probably will delete
...
│
└───wavetables # This is where your wavetables land when the script runs.
 ```

## setup

You need to set the project up first, Make sure you have python installed. If the script fails, find the python 3.11 version from the python site and install that, even if you already have another version of python installed.  When installing, no need to set it as your main python, just install it as usual and let it go. The setpy commands will take care of using this version

on all platforms, you will need to open a terminal and navigate ti the wavetabler folder you just unzipped. 
### Windows 
from your command prompt in the wavetabler folder, run:
`setpy`
You only need to do this once.  

### MacOS (untested) or Linux 

Make your two launchers executable. From a command prompt in the wavetablers folder, you only need to enter this once:
`chmod +x *.sh`
Then enter
`./setpy.sh`
You only need to do this once.  
possible problem: if you are on Manjaro, Arch, or any Arch-derived Linux that uses Pacman, you might have to run the following command after setpy.sh:
`pip install numpy scipy librosa resampy soundfile pydub matplotlib pandas tabulate` 
because they wont install from the script. 


## warning: 
pause dropbox or any other cloud serive while running the script or run put the wavetabler folder outside of the dropbox folder.  If you get a permissions error, that is usually the cause.  

## Test Run
run a test on the example input files: 

type `wvtbl` on windows, (`./wvtbl.sh` on Mac/Linux) from you command prompt and choose one or both of the two sample files.  When it asks you to accept defaults, just hit enter, and after a little processing, you should have a shiny new 2048 sample per wwavecycle, 256 frame wavetable in the wavetables folder

## Creating your own wavetables

Copy some short wav files you want to convert to wavetables to the `wavetabler/imput` folder.  

- They can be any sample rate or bit depth between `44.1kHz` and `192kHz`, `16 bit` to `32 bit float`.  Higher bit depths will help with the quality of the results. 
- Stereo files in the input folder get converted to mono, so make sure you keep a copy somewhere. 
- While you can load any length file, *anything more than ten seconds or so will take an inordinate amount of time*, so your best bet is to pick a 2-10 second slice.  

run `wvtbl` on windows or ./wvrbl.sh on MacOS or Linux and select from the attending file menu. Once you select a file or files, accept defaults, and look in your `wavetables` subfolder for your finished wavetables nce the script finishes. 

## Loading into Serum (and other wavetable synths)
I only have instructions for Serum ATM:  In Serum, click on one of the wavetable edit icons in the oscillator section.  From the import menu choose `import-fixed-frame` pick a wavetable and enter 2048 when prompted.  Your oscillator will load up the wavetable you select from the wavetables subfolder.

## Advanced 

TBD. If you do not accept defaults, you get an advanced series of prompts, which can help if your wavetables are not to your liking.  I have tried to make the choices clear in the script and will later provide some details about how to choose among the options.  

- **known isssue**, in the last section, you get a choice of fitting the wavetable, chopping it into arbitrary chunks, or picking a chunk. There is an issue with the "pick" function where the selection does not start at a zero crossing, throwing the whole selection off.  Hang tight, will fix it soon, but for now avoid.  

