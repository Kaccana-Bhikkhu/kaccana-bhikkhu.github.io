# Ajahn Pasanno Question and Answer Archive

## Documentation links
[prototype/README.md](prototype/README.md) - purpose and scope of this project and status of the current prototype.

[documentation/DatabaseFormat.md](documentation/DatabaseFormat.md) - describes database.json

Project achitecture - this file


## Architecture
We build the archive using a series of scripted operations of the form:

`python QAarchive.py operations [options]`,

where `operations` is a comma-separated list. Each operation is the name of a module in the `python/` directory, which are executed in the sequence below. `QAarchive.py All` runs all modules.

### Textual data flow
##### [AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) - Google Sheet (in nearly final form; the full archive may contain ~25 retreats and ~2,000 questions)

↓

↓ `QAarchive.py DownloadCSV` - not written; some easy solutions are buggy; need to research Google API; currently using gs script and manual download 

↓

##### [csv/](csv/) - one .csv file corresponding to each sheet

↓

↓ `QAarchive.py ParseCSV` (almost fully functional)

↓

###### [database.json](database.json) - main database file; roughly one dict entry per csv sheet; [format](documentaion/DatabaseFormat.md) nearly finalised

↓

↓ `QAarchive.py ParseCSV BuildSite` - Owen writes this in whatever language he prefers

↓

###### web/Index.html, etc.

#### Prototype website textual data flow

###### [database.json](database.json)

↓

↓ `QAarchive.py Prototype` (almost fully functional)

↓

###### [prototype/Index.html](prototype/Index.html), etc.

### Audio data flow (operations depend on the content of database.json)

#### First try to download split mp3s from our Google Cloud server:

###### https://storage.googleapis.com/apqa_archive/audio/questions/TG2013/TG2013_S01_Q01.mp3 - previously split mp3 files in Google Cloud

↓

↓ `QAarchive.py DownloadMP3` - not yet written

↓

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - local split mp3 files

#### If this doesn't work, then download and split the files ourselves:

###### [https://www.abhayagiri.org/../AP_11_23_2013...mp3](https://www.abhayagiri.org/media/discs/APasannoRetreats/2013%20Thanksgiving%20Retreat/Audio/AP_11_23_2013_Monastic_Retreat_eve_Questions_and_Answers_1.mp3) - published Q&A sessions on Abhayagiri's website

↓

↓ `QAarchive.py DownloadMP3` - not yet written

↓

###### audio/retreats/TG2013/AP_11_23_2013...mp3 - local copy of full-length Q&A session; mp3 filenames match published retreat audio

↓

↓ `QAarchive.py SplitMP3` (interface to Mp3DirectCut written and tested)

↓

###### audio/questions/TG2013/TG2013_SXX_QYY.mp3 - audio files corresponding to question YY in session XX of retreat TG2013

#### In either case:

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - local split mp3 files

↓

↓ `QAarchive.py TagMP3` (there are several ID3 tag libraries for python)

↓

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - tagged files keep the same names
