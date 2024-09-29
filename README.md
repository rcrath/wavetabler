# wavetabler
 Create wavetables for Serum, VItal, etc from any short mono wav file

 ## description
 wavetabler creates 2048 sample X 256 frames wavetables that can be imported as fixed size 2048 in Serum's wavetable editor import screen.  Have not tested on other synths but should be able to figure it out if you rtm for that synth I thnk.  

 This is an alpha release.  It works for me, ymmv.  I have a linux and windows box and have tested it on both.

 my packaging skills are not there yet, so for now, download or clone the repository and copy the top folder (wavetabler) to where you wnat to run it. if you cloned it, you definitely want to work form a dedicated separate folder outside your git folder because we will create and delete tons of files.  CD into  wavetabler folder.  There you will find the following tree:  

 from within wavetabler, open a command prompt, 

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

### Windows 
from your command prompt in the wavetabler folder, run:
`setpy`
You only need to do this once.  

### MacOS (untested) or Linux 
from a command prompt in the wavetabler folder run `chmod +x setpy.sh)` and then `./setpy.sh`
You only need to do this once.  

## Test Run
run a test on the example input files: 

### Windows: 
type `wvtbl` from you command prompt and choose one of the two sample files.  when it asks you to accept defaults, just hit enter, and after a little processing, you should have a shiny new 2048 sample per wwavecycle, 256 frame wavetable in the wavetables folder.

### Mac/:inux: 
you have to set the permissions for it to execute the first time:
 `chmod +x wvtbl.sh)` and then `./wvtbl.sh` runs it
``

## Creating your own wavetables

Copoy some samples you want to convert to wavetables to the `wavetabler/imput` folder.  They can be any sample rate or bit depth between `44.1kHz` and `192kHz`, `16 bit` to `32 bit float`.  Higher sample rates and bit depths will help with the quality of the results. For now the files must be mono.  While you can load any length file, *anything more than ten seconds or so will take an inordinate amount of time*, so your best bet is to pick a 2-10 second slice, make sure you save it to mono.  

run `wvtbl` and select from the attanding file menu. accept defaults, and look in your `wavetables` folder for your finished wavetables. 

## Loading into Serum (and other wavetable synths)
I only have instructions for Serum ATM:  in serum click on one of the wavetable edit icons in the oscillator section.  from the edit menu choose `import-fixed-frame` and enter 2048.  Your oscilator will load up the wavetable you selected from the output folder.

## Advanced 
TBD. If you do not accept defaults, you get an advanced series of prompts, which can help if your wavetables are not to your liking.  I have tried to make the choices clear in the script and will later provide some details about how to choose among the options.  
