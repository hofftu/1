# MFCRecorder

This is script to automate the recording of public webcam shows from myfreecams. 


## Requirements

I have only tested this on debian(7+8) and Mac OS X (10.10.4), but it should run on other OSs

Requires python3.5 or newer. You can grab python3.5.2 from https://www.python.org/downloads/release/python-352/
and mfcauto.py (https://github.com/ZombieAlex/mfcauto.py)

to install required modules, run:
```
python3.5 -m pip install -r requirements.txt
python3.5 -m pip install --upgrade git+https://github.com/ZombieAlex/mfcauto.py@master
```

## Setup

edit the config.conf file and set the appropirate paths to your directories and wanted.txt file. 

Add models UID (user ID) to the "wanted.txt" file (only one model per line). This uses the UID instead of the name becaue the models can change their name at anytime, but their UID always stays the same. There is a number of ways to get the models UID, but the easiest would probably be to get it from the URL for their profile image. The profile image URL is formatted as (or similar to):
```
https://img.mfcimg.com/photos2/###/{uid}/avatar.90x90.jpg
```
"{uid}" is the models UID which is the number you will want to add to the "wanted.txt" file. the "###" is the first 3 digits of the models UID. For example, if the models UID is "123456789" the URL for their profile picture will be:
```
https://img.mfcimg.com/photos2/123/123456789/avatar.90x90.jpg
```

alternatively, you can add a model with the "add.py" script (must be ran with python3.5 or newer).

Its usage is as follows:
add.py {models_display_name}

ie:
```
python3.5 add.py AspenRae
```


## Additional options

you can now set a custom "completed" directory where the videos will be moved when the stream ends. The variables which can be used in the naming are as follows:

{path} = the value set to "save directory"

{model} = the display name of the model

{uid} = the uid (user id) or broadcasters id as its often reffered in MFCs code which is a static number for the model

{year} = the current 4 digit year (ie:2017)

{month} = the current two digit month (ie: 01 for January)

{day} = the two digit day of the month

{hour} = the two digit hour in 24 hour format (ie: 1pm = 13)

{minute} = the current minute value in two digit format (ie: 1:28 = 28)

{seconds} = the current times seconds value in 2 digit format

{auto} = reason why the model was recorded if not in wanted list (see auto recording based on conditions below)

For example, if a made up model named "hannah" who has the uid 208562, and the "save_directory" in the config file == "/Users/Joe/MFC/": {path}/{uid}/{year}/{year}.{month}.{day}_{hour}.{minutes}.{seconds}_{model}.mp4 = "/Users/Joe/MFC/208562/2017/2017.07.26_19.34.47_hannah.mp4"


You can create your own "post processing" script which can be called at the end of the stream. The parameters which will be passed to the script are as follows:

1 = full file path (ie: /Users/Joe/MFC/208562/2017/2017.07.26_19.34.47_hannah.mp4)

2 = filename (ie : 2017.07.26_19.34.47_hannah.mp4)

3 = directory (ie : /Users/Joe/MFC/208562/hannah/2017/)

4 = models name (ie: hannah)

5 = uid (ie: 208562 as given in the directory/file naming structure example above)


## Conditional recording

In the config file you can specify conditions in which models who are not in the wnated list should be recorded. There is also a blacklist you can create and add models UID to if you want to specify models who will not be recorded even if these conditions are met. 

Tags: you can add a comma (,) separated list of tags which models will be checked against each models specified tags.

minTags: indicates the minimum number of tags from the "Tags" option which must be met to start recording a model.

newerTahHours: If a model has joined the site in less than the number of hours specified here, the model will be recorded until she has been a model for longer than this time (it will continue to record any active recording started prior to this time). 

score: any model with a camscore greater than this number will be recorded

viewers: when a model reachest this number of viewers in her chatroom, she will be recorded. This can be used to catch models as many users are entering the chat which usually indicates some sort of show has started.

autoStopViewers: This only apples to models who are being recorded based on the viewers condition above. The session will stop recording when the number of viewers drops below this number. Make sure there is enough of a difference between these two numbers (viewers and autoStopViewers) to avoid the show continuously starting and stopping as the number of viewers moves above/below these numbers. 
