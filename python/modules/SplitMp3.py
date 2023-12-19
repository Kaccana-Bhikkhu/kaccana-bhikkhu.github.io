"""Use Mp3DirectCut.exe to split the session audio files into individual excerpts based on start and end times from Database.json"""

from __future__ import annotations

import os, json, platform
import Utils, Alert, Link, TagMp3, PrepareUpload
import Mp3DirectCut
from Mp3DirectCut import Clip, ClipTD
from typing import List, Union, NamedTuple
from datetime import timedelta

Mp3DirectCut.SetExecutable(Utils.PosixToWindows(Utils.PosixJoin('tools','Mp3DirectCut')))


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
    parser.add_argument('--overwriteMp3',**Utils.STORE_TRUE,help="Overwrite existing mp3 files; otherwise leave existing files untouched")

def ParseArguments() -> None:
    pass

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main():
    """ Split the Q&A session mp3 files into individual excerpts.
    Read the beginning and end points from Database.json."""
    
    if platform.system() != "Windows":
        Alert.error(f"SplitMp3 requires Windows to run mp3DirectCut.exe. mp3 files cannot be split on {platform.system()}.")
        return

    # Step 1: Determine which excerpt mp3 files need to be created
    eventExcerptClipsDict:dict[str,dict[str,list[Mp3DirectCut.Clip]]] = {}
        # eventExcerptClipsDict[eventName][filename] is the list of clips to join to create
        # excerpt file filename
    excerptsByFilename:dict[str,dict] = {}
        # Store each excerpt by filename for future reference
    for event,eventExcerpts in Utils.GroupByEvent(gDatabase["excerpts"]):        
        eventName = event["code"]
        if gOptions.events != "All" and eventName not in gOptions.events:
            continue

        excerptClipsDict:dict[str,list[Mp3DirectCut.Clip]] = {}

        if gOptions.overwriteMp3:
            excerptsNeedingSplit = eventExcerpts
        else:
            excerptsNeedingSplit = [x for x in eventExcerpts if Link.LocalItemNeeded(x)]
        if not excerptsNeedingSplit:
            continue
        
        session = dict(sessionNumber=None)
        for excerpt in excerptsNeedingSplit:
            if session["sessionNumber"] != excerpt["sessionNumber"]:
                session = Utils.FindSession(gDatabase["sessions"],eventName,excerpt["sessionNumber"])

            filename = f"{Utils.ItemCode(excerpt)}.mp3"
            clips = list(excerpt["clips"])
            defaultSource = session["filename"]
            for index in range(len(clips)):
                source = clips[index].file
                if source == "$":
                    source = defaultSource
                elif index == 0:
                    defaultSource = clips[0].file
                clips[index] = clips[index]._replace(file=Utils.PosixToWindows(Link.URL(gDatabase["audioSource"][source],"local")))

            excerptClipsDict[filename] = clips
            excerptsByFilename[filename] = excerpt
    
        eventExcerptClipsDict[eventName] = excerptClipsDict
    
    if not eventExcerptClipsDict:
        Alert.status("No excerpt files need to be split.")
        return
    
    allSources = [gDatabase["audioSource"][os.path.split(source)[1]] for source in Mp3DirectCut.SourceFiles(eventExcerptClipsDict)]
    totalExcerpts = sum(len(xList) for xList in eventExcerptClipsDict.values())
    Alert.extra(totalExcerpts,"excerpt(s) in",len(eventExcerptClipsDict),"event(s) need to be split from",len(allSources),"source file(s).")
    
    # Step 2: Download any needed audio sources
    def DownloadItem(item: dict) -> None:
        Link.DownloadItem(item,scanRemoteMirrors=False)

    with Utils.ConditionalThreader() as pool:
        for source in allSources:
            pool.submit(DownloadItem,source)

    splitCount = 0
    errorCount = 0
    # Step 3: Loop over all events and split mp3 files
    for eventName,excerptClipsDict in eventExcerptClipsDict.items():
        outputDir = Utils.PosixJoin(gOptions.excerptMp3Dir,eventName)
        os.makedirs(outputDir,exist_ok=True)

        # Group clips by sources and call MultiFileSplitJoin multiple times.
        # If there is an error, this lets us continue to split the remaining files.
        for sources,clipsDict in Mp3DirectCut.GroupBySourceFiles(excerptClipsDict):
            # Invoke Mp3DirectCut on each group of clips:
            try:
                Mp3DirectCut.MultiFileSplitJoin(clipsDict,outputDir=Utils.PosixToWindows(outputDir))
            except Mp3DirectCut.ExecutableNotFound as err:
                Alert.error(err)
                Alert.status("Continuing to next module.")
                return
            except (Mp3DirectCut.Mp3CutError,ValueError,OSError) as err:
                Alert.error(f"{eventName}: {err} occured when splitting source files {sources}.")
                Alert.status("Continuing to next source file(s).")
                errorCount += 1
                continue
            
            for filename in clipsDict:
                filePath = Utils.PosixJoin(outputDir,filename)
                TagMp3.TagMp3WithClips(filePath,excerptsByFilename[filename]["clips"])
            
            splitCount += 1
            sources = set(os.path.split(source)[1] for source in sources)
            Alert.info(f"{eventName}: Split {sources} into {len(clipsDict)} files.")
    
    Alert.status(f"   {splitCount} source file groups split; {errorCount} source file groups had errors.")