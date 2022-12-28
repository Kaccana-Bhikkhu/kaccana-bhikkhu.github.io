# Ajahn Pasanno Question and Answer Archive

Documentation 
[prototype/README.md](prototype/README.md) for information about the purpose and scope of this project and the status of the current prototype.

## Architecture
The project architecture is a series of scripted operations:

### Textual data flow
[AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) - Google Sheet (in roughly final form, but the full archive may contain ~25 retreats and ~2,000 questions)

↓
    
↓ QAarchive.py DownloadCSV (not written; some easy solutions are buggy; need to research Google API; currently using gs script and manual download)

↓

home/csv - one .csv file corresponding to each sheet
    ↓
    ↓    QAarchive.py ParseCSV (in progress)
    ↓
home/database.json (main database file; roughly one dict entry per csv sheet; format still evolving)
    ↓
    ↓    QAarchive.py BuildSite (You can write this in whatever language you prefer)
    ↓
home/web/index.html, etc. (a self-contained website that doesn't require server php or the equivalent would make development and deployment easier)

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
