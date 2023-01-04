# Ajahn Pasanno Question and Answer Archive

## Documentation links
[prototype/README.md](prototype/README.md) - purpose and scope of this project and status of the current prototype.

[documentation/DatabaseFormat.md](documentation/DatabaseFormat.md) - describes Database.json

Project achitecture and command line flags - this file


## Architecture
We build the archive using a series of scripted operations of the form:

`python QAarchive.py operations [options]`,

where `operations` is a comma-separated list. Each operation is the name of a module in the `python/` directory, which are executed in the sequence below. `QAarchive.py All` runs all modules.

### Textual data flow
##### [AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) - Google Sheet (in nearly final form; the full archive may contain ~25 retreats and ~2,000 questions)

↓ `QAarchive.py DownloadCSV` - not written; some easy solutions are buggy; need to research Google API; currently using gs script and manual download 

##### [csv/](csv/) - one .csv file corresponding to each sheet

↓ `QAarchive.py ParseCSV` (almost fully functional)

###### [prototype/SpreadsheetDatabase.json](prototype/SpreadsheetDatabase.json) - human-readable database file; roughly one dict entry per csv sheet; [format](documentaion/DatabaseFormat.md) nearly finalised

↓ `QAarchive.py Prototype` (almost fully functional)

###### [prototype/index.html](prototype/index.html), etc. - Text-based prototype website

#### Main website

###### [prototype/SpreadsheetDatabase.json](prototype/SpreadsheetDatabase.json)

↓ `QAarchive.py OptimizeDatabase` - Owen writes this

###### [Database.json](Database.json) - Database optimized for template engine and web-based Javascript

↓ `QAarchive.py ParseCSV BuildSite` - Owen writes this in whatever language he prefers

###### index.html, etc.

### Audio data flow (operations depend on the content of Database.json)

The operations below execute only when necessary. If the sessionMp3 and questionMp3 options are both remote, all audio links point elsewhere, and there is no need to download or process audio files.

#### First try to download split mp3s from our Google Cloud server:

###### https://storage.googleapis.com/apqa_archive/audio/questions/TG2013/TG2013_S01_Q01.mp3 - previously split mp3 files in Google Cloud

↓ `QAarchive.py DownloadMP3` - not yet written

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - local split mp3 files

#### If this doesn't work, then download and split the files ourselves:

###### [https://www.abhayagiri.org/../AP_11_23_2013...mp3](https://www.abhayagiri.org/media/discs/APasannoRetreats/2013%20Thanksgiving%20Retreat/Audio/AP_11_23_2013_Monastic_Retreat_eve_Questions_and_Answers_1.mp3) - published Q&A sessions on Abhayagiri's website

↓ `QAarchive.py DownloadMP3` - not yet written

###### audio/retreats/TG2013/AP_11_23_2013...mp3 - local copy of full-length Q&A session; mp3 filenames match published retreat audio

↓ `QAarchive.py SplitMP3` (interface to Mp3DirectCut written and tested)

###### audio/questions/TG2013/TG2013_SXX_QYY.mp3 - audio files corresponding to question YY in session XX of retreat TG2013

#### In either case:

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - local split mp3 files

↓ `QAarchive.py TagMP3` (not yet written; there are several ID3 tag libraries for python)

###### audio/questions/TG2013/TG2013_S01_Q01.mp3 - tagged files keep the same names

## Command line

**example:** `python QAarchive.py All --questionMp3 local -vv` - Run all modules with increased verbosity and link to local question mp3 files

**usage:**  QAarchive.py [-h] [--homeDir HOMEDIR] [--spreadsheetDatabase SPREADSHEETDATABASE]
                    [--optimizedDatabase OPTIMIZEDDATABASE] [--sessionMp3 SESSIONMP3] [--questionMp3 QUESTIONMP3]
                    [--remoteQuestionMp3URL REMOTEQUESTIONMP3URL] [--csvDir CSVDIR] [--ignoreTeacherConsent]
                    [--ignoreExcludes] [--zeroCount] [--detailedCount] [--jsonNoClean] [--eventMp3Dir EVENTMP3DIR]
                    [--questionMp3Dir QUESTIONMP3DIR] [--overwriteMp3] [--prototypeDir PROTOTYPEDIR]
                    [--indexHtmlTemplate INDEXHTMLTEMPLATE] [--verbose] [--quiet]
                    ops

Create the Ajahn Pasanno Question and Answer Archive website from mp3 files and the AP QA archive main Google Sheet.

**positional arguments:**
  ops                   A comma-separated list of operations to perform. No spaces allowed. Available operations:
                        ParseCSV - convert the csv files downloaded from the Google Sheet to SpreadsheetDatabase.json.
                        SplitMp3 - split mp3 files into individual questions based on the times in
                        SpreadsheetDatabase.json. Prototype - create various files to illustrate how Database.json
                        should be interpreted. OptimizeDatabase - convert SpreadsheetDatabase.json to (optimized)
                        Database.json All - run all the above modules in sequence.

**options:**

  -h, --help            show this help message and exit
  
  --homeDir HOMEDIR     All other pathnames are relative to this directory; Default: ./
  
  --spreadsheetDatabase SPREADSHEETDATABASE
                        Database created from the csv files; keys match spreadsheet headings; Default:
                        prototype/SpreadsheetDatabase.json
                        
  --optimizedDatabase OPTIMIZEDDATABASE
                        Database optimised for Javascript web code; Default: Database.json
                        
  --sessionMp3 SESSIONMP3
                        Session audio file link location; default: remote - use external Mp3 URL from session database
                        
  --questionMp3 QUESTIONMP3
                        Question audio file link location; default: remote - use remoteQuestionMp3URL
                        
  --remoteQuestionMp3URL REMOTEQUESTIONMP3URL
                        remote URL for questions; default: storage.googleapis.com/apqa_archive/audio/questions/
                        
  --csvDir CSVDIR       Read/write csv files in this directory; Default: ./csv
  
  --ignoreTeacherConsent
                        Ignore teacher consent flags - debugging only
                        
  --ignoreExcludes      Ignore exclude session and question flags - debugging only
  
  --zeroCount           Write count=0 keys to json file; otherwise write only non-zero keys
  
  --detailedCount       Count all possible items; otherwise just count tags
  
  --jsonNoClean         Keep intermediate data in json file for debugging
  
  --eventMp3Dir EVENTMP3DIR
                        Read session mp3 files from this directory; Default: ./audio/events
                        
  --questionMp3Dir QUESTIONMP3DIR
                        Write question mp3 files from this directory; Default: ./audio/questions
                        
  --overwriteMp3        Overwrite existing mp3 files; otherwise leave existing files untouched
  
  --prototypeDir PROTOTYPEDIR
                        Write prototype files to this directory; Default: ./prototype
                        
  --indexHtmlTemplate INDEXHTMLTEMPLATE
                        Use this file to create index.html; Default: prototype/templates/index.html
                        
  --verbose, -v         increase verbosity
  
  --quiet, -q           decrease verbosity

### mp3 file links

The arguments --sessionMp3 and --questionMp3 describe where mp3 links should point in the prototype and final website. The options are:

local - /audio/events (for sessions) or /audio/questions (for questions)

remote (default) - Database.Sessions["Remote session URL"] for sessions or --remoteQuestionMp3URL for questions

In the future, more values could be added:

autoPreferLocal - link to the local file if it exists, otherwise link to remote

autoPreferRemote - link to the remote file if it exists, otherwise link to local
