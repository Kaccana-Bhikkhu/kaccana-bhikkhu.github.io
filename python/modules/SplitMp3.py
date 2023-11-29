"""Use Mp3DirectCut.exe to split the session audio files into individual excerpts based on start and end times from Database.json"""

from __future__ import annotations

import os, json, platform
import Utils, Alert, Link
import Mp3DirectCut
from typing import List, Union, NamedTuple
from datetime import timedelta
import copy

Mp3DirectCut.SetExecutable(Utils.PosixToWindows(Utils.PosixJoin('tools','Mp3DirectCut')))

TimeSpec = Union[timedelta,float,str]
"A union of types that can indicate a time index to an audio file."

def ToTimeDelta(time: TimeSpec) -> timedelta|None:
    "Convert various types to a timedetla object."

    if type(time) == timedelta:
        return copy(time)
    
    try:
        floatVal = float(time)
        return timedelta(seconds =floatVal)
    except ValueError:
        pass

    if not time:
        return None

    try:
        numbers = str.split(time,":")
        if len(numbers) == 2:
            return timedelta(minutes = int(numbers[0]),seconds = float(numbers[1]))
        elif len(numbers) == 3:
            return timedelta(hours = int(numbers[0]),minutes = int(numbers[1]),seconds = float(numbers[2]))
    except (ValueError,TypeError):
        pass
    
    raise ValueError(f"{repr(time)} cannot be converted to a time.")
    
class Clip(NamedTuple):
    """A Clip represents a section of a given audio file."""
    file: str               # Filename of the audio file
    start: TimeSpec         # Clip start time
    end: TimeSpec|None      # Clip end time; None indicates the end of the file

class ClipTD(NamedTuple):
    """Same as above, except the types must be timedelta."""
    file: str               # Filename of the audio file
    start: timedelta        # Clip start time
    end: timedelta|None     # Clip end time; None indicates the end of the file

    def FromClip(clip: Clip) -> ClipTD:
        """Convert a Clip to a ClipTD."""
        return ClipTD(clip.file,ToTimeDelta(clip.start),ToTimeDelta(clip.end))
    
    def Duration(self,fileDurarion: timedelta) -> timedelta:
        """Calculate the duration of this clip.
        Use fileDuration if self.end is None."""

        if self.end:
            return self.end - self.start
        else:
            return fileDurarion - self.start

def IncludeRedactedExcerpts() -> List[dict]:
    "Merge the redacted excerpts back into the main list in order to split mp3 files"
    
    allExcerpts = gDatabase["excerpts"] + gDatabase["excerptsRedacted"]
    allExcerpts = [x for x in allExcerpts if x["fileNumber"]] # Session excerpts don't need split mp3 files
    orderedEvents = list(gDatabase["event"].keys()) # Look up the event in this list to sort excerpts by event order in gDatabase
    
    allExcerpts.sort(key = lambda x: (orderedEvents.index(x["event"]),x["sessionNumber"],x["fileNumber"]))
        # Sort by event, then by session, then by file number
    
    return allExcerpts

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--overwriteMp3',action='store_true',help="Overwrite existing mp3 files; otherwise leave existing files untouched")

def ParseArguments() -> None:
    pass

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main():
    """ Split the Q&A session mp3 files into individual excerpts.
    Read the beginning and end points from Database.json."""
    
    if platform.system() != "Windows":
        Alert.error(f"SplitMp3 requires Windows to run mp3DirectCut.exe. mp3 files cannot be split on {platform.system()}.")
        return

    sessionCount = 0
    mp3SplitCount = 0
    errorCount = 0
    alreadySplit = 0
    excerpts = IncludeRedactedExcerpts()
    for session in gDatabase["sessions"]:
        
        sessionNumber = session["sessionNumber"]
        event = session["event"]
        if gOptions.events != "All" and event not in gOptions.events:
            continue

        excerptList = []
        fileNumber = 1
        sessionCount += 1
        
        baseFileName = f"{event}_S{sessionNumber:02d}_"
        sessionExcerpts = [x for x in excerpts if x["event"] == event and x["sessionNumber"] == sessionNumber]
        if not any(Link.LocalItemNeeded(x) for x in sessionExcerpts):
            continue # If no local excerpts are needed in this session, then no need to split mp3 files

        for x in sessionExcerpts:
            fileName = baseFileName + f"F{fileNumber:02d}"
            startTime = Utils.StrToTimeDelta(x["clips"][0].start)
            
            endTimeStr = x["clips"][0].end.strip()
            if endTimeStr:
                excerptList.append((fileName,startTime,Utils.StrToTimeDelta(endTimeStr)))
            else:
                excerptList.append((fileName,startTime))
                
            fileNumber += 1
        
        eventDir = Utils.PosixJoin(gOptions.sessionMp3Dir,event)
        sessionFilePath = Utils.PosixJoin(eventDir,session["filename"])
        if not os.path.exists(sessionFilePath):
            Alert.warning("Cannot locate",sessionFilePath)
            errorCount += 1
            continue
        
        outputDir = Utils.PosixJoin(gOptions.excerptMp3Dir,event)
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
        
        allOutputFilesExist = True
        for x in excerptList:
            if not os.path.exists(Utils.PosixJoin(outputDir,x[0]+'.mp3')):
                allOutputFilesExist = False
        
        if allOutputFilesExist and not gOptions.overwriteMp3:
            alreadySplit += 1
            continue
        
        # We use eventDir as scratch space for newly generated mp3 files.
        # So first clean up any files left over from previous runs.
        for x in excerptList:
            scratchFilePath = Utils.PosixToWindows(Utils.PosixJoin(eventDir,x[0]+'.mp3'))
            if os.path.exists(scratchFilePath):
                os.remove(scratchFilePath)
        
        # Next invoke Mp3DirectCut:
        try:
            Mp3DirectCut.Split(Utils.PosixToWindows(sessionFilePath),excerptList)
        except Mp3DirectCut.ExecutableNotFound as err:
            Alert.error(err)
            Alert.status("Continuing to next module.")
            return
        except Mp3DirectCut.Mp3CutError as err:
            Alert.error(err)
            Alert.status("Continuing to next mp3 file.")
            continue
        except (ValueError,OSError) as err:
            Alert.error(f"Error: {err} occured when processing session {session}")
            errorCount += 1
            Alert.status("Continuing to next mp3 file.")
            continue
        
        # Now move the files to their destination
        for x in excerptList:
            scratchFilePath = Utils.PosixJoin(eventDir,x[0]+'.mp3')
            outputFilePath = Utils.PosixJoin(outputDir,x[0]+'.mp3')
            if os.path.exists(outputFilePath):
                os.remove(outputFilePath)
            
            os.rename(scratchFilePath,outputFilePath)
        
        mp3SplitCount += 1
        Alert.info(f"Split {session['filename']} into {len(excerptList)} files.")
    
    Alert.status(f"   {mp3SplitCount} sessions split; {errorCount} sessions had errors; all files already present for {alreadySplit} sessions.")