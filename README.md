# wavetabler
 Create wavetables for Serum, Vital, etc from any short mono wav file

 ## description
 wavetabler creates 2048 sample X 256 frames wavetables that can be imported as fixed size 2048 in Serum's wavetable editor import screen.  Have not tested on other synths but should be able to figure it out if you rtm for that synth I think.  

 This is an alpha release.  It works for me, ymmv.  I have a Linux and windows box and have tested it on both.

 My packaging skills are not there yet, so for now, download or clone the repository and copy the top folder (wavetabler) to where you wnat to run it. if you cloned it, you definitely want to work form a dedicated separate folder outside your git folder because we will create and delete tons of files.  CD into  wavetabler folder.  There you will find the following tree:  

 

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

You need to set the project up first, Make sure you have python installed. If the script fails, find the python 3.11 version from the python site and install that, even if you already have another version of python installed.  when installing, no need to set it as your main python, just install it as usual and let it go. the setpy commands will take care of using this version.
Download the zip file just above and to the right of the file listing. 

### Windows 
from your command prompt in the wavetabler folder, run:
`setpy`
You only need to do this once.  

### MacOS (untested) or Linux 
from a command prompt in the wavetabler folder run `chmod +x setpy.sh)` and then `./setpy.sh`
You only need to do this once.  

## warning: 
pause dropbox or any other cloud serive while running the script or run it outside of the dropbox folder.  If you get a permissions error, that is usually the cause.  

## Test Run
run a test on the example input files: 

### Windows: 
type `wvtbl` from you command prompt and choose one of the two sample files.  when it asks you to accept defaults, just hit enter, and after a little processing, you should have a shiny new 2048 sample per wwavecycle, 256 frame wavetable in the wavetables folder.

### Mac/:inux: 
you have to set the permissions for it to execute the first time:
 `chmod +x wvtbl.sh)` and then `./wvtbl.sh` runs it
``

## Creating your own wavetables

Copy some samples you want to convert to wavetables to the `wavetabler/imput` folder.  They can be any sample rate or bit depth between `44.1kHz` and `192kHz`, `16 bit` to `32 bit float`.  Higher sample rates and bit depths will help with the quality of the results. For now the files must be mono.  While you can load any length file, *anything more than ten seconds or so will take an inordinate amount of time*, so your best bet is to pick a 2-10 second slice, make sure you save it to mono.  

run `wvtbl` and select from the attending file menu. accept defaults, and look in your `wavetables` folder for your finished wavetables. 

## Loading into Serum (and other wavetable synths)
I only have instructions for Serum ATM:  in serum click on one of the wavetable edit icons in the oscillator section.  from the import menu choose `import-fixed-frame` and enter 2048.  Your oscillator will load up the wavetable you select from the output folder.

## Advanced 
- **known isssue**, in the last section, you get a choice of fitting the wavetable, chopping it into arbitrary chunks, or picking a chunk. There is an issue with the "pick" function where the selection does not start at a zero crossing, throwing the whole selection off.  hang tight, will fix it soon, but for now avoid.  

TBD. If you do not accept defaults, you get an advanced series of prompts, which can help if your wavetables are not to your liking.  I have tried to make the choices clear in the script and will later provide some details about how to choose among the options.  
