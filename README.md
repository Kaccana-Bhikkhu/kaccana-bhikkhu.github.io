# Ajahn Pasanno Question and Answer Archive

## Documentation links
[prototype/README.md](prototype/README.md) - purpose and scope of this project and status of the current prototype.

[documentaion/DatabaseFormat.md](documentaion/DatabaseFormat.md) - describes database.json

Project achitecture - this file


## Architecture
We build the archive using a series of scripted operations of the form:

`python QAarchive.py operations [options]`,

where `operations` is a comma-separated list. Each operation is the name of a module in the `python/` directory, which are executed in the sequence below. `QAarchive.py All` runs all modules.

### Textual data flow
[AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) - Google Sheet (in roughly final form); the full archive may contain ~25 retreats and ~2,000 questions)

↓

↓ `QAarchive.py DownloadCSV` (not written; some easy solutions are buggy; need to research Google API; currently using gs script and manual download)

↓

[csv/](csv/) - one .csv file corresponding to each sheet

↓

↓ `QAarchive.py ParseCSV` (almost fully functional)

↓

[database.json](database.json) (main database file; roughly one dict entry per csv sheet; format still evolving)

↓

↓ `QAarchive.py Prototype` (almost fully functional)

↓

[prototype/Index.html](prototype/Index.html), etc.

web/Index.html, etc.

↓

↓ `QAarchive.py ParseCSV BuildSite` (Owen writes this in whatever language he prefers)

↓
web/Index.html, etc.

### Audio data flow (operations depend on the content of database.json)

home/audio/retreats/TG2013/xxx.mp3 - full-length Q&A sessions given during retreat TG2013 (for example); mp3 filenames match published retreat audio
    ↓
    ↓    QAarchive.py SplitMP3 (interface to Mp3DirectCut written and tested)
    ↓
home/audio/questions/TG2013/TG2013_SXX_QYY.mp3 - audio files corresponding to question YY in session XX of retreat TG2013
    ↓
    ↓    QAarchive.py TagMP3 (there are several ID3 tag libraries for python)
    ↓
tagged .mp3 files keep the same names
