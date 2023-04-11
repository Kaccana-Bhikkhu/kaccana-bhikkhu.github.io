"""Use Mp3DirectCut.exe to split the session audio files into individual excerpts based on start and end times from Database.json"""

import os, json
import Utils
import Mp3DirectCut as Mp3DirectCut
from typing import List

Mp3DirectCut.SetExecutable(os.path.join('tools','Mp3DirectCut'))

def IncludeRedactedExcerpts() -> List[dict]:
    "Merge the redacted excerpts back into the main list in order to split mp3 files"
    
    allExcerpts = gDatabase["excerpts"] + gDatabase["excerptsRedacted"]
    # print(len(allExcerpts))
    orderedEvents = list(gDatabase["event"].keys()) # Look up the event in this list to sort excerpts by event order in gDatabase
    
    allExcerpts.sort(key = lambda x: (orderedEvents.index(x["event"]),x["sessionNumber"],x["fileNumber"]))
        # Sort by event, then by session, then by file number
    
    return allExcerpts

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--eventMp3Dir',type=str,default=os.path.join('audio','events'),help='Read session mp3 files from this directory; Default: ./audio/events')
    parser.add_argument('--excerptMp3Dir',type=str,default=os.path.join('audio','excerpts'),help='Write excerpt mp3 files from this directory; Default: ./audio/excerpts')
    parser.add_argument('--overwriteMp3',action='store_true',help="Overwrite existing mp3 files; otherwise leave existing files untouched")

gOptions = None
gDatabase = None
def main(clOptions,database):
    """ Split the Q&A session mp3 files into individual excerpts.
    Read the beginning and end points from Database.json."""
    
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    gDatabase = database
    
    if gOptions.sessionMp3 == 'remote' and gOptions.excerptMp3 == 'remote':
        if gOptions.verbose > 0:
            print("   All mp3 links go to remote servers. No mp3 files will be processed.")
        return # No need to run SplitMp3 if all files are remote
    
    excerptIndex = 0
    sessionCount = 0
    mp3SplitCount = 0
    excerpts = IncludeRedactedExcerpts()
    for session in gDatabase["sessions"]:
        
        sessionNumber = session["sessionNumber"]
        event = session["event"]
        excerptList = []
        fileNumber = 1
        
        sessionCount += 1
        
        baseFileName = f"{event}_S{sessionNumber:02d}_"
        while excerptIndex < len(excerpts) and excerpts[excerptIndex]["event"] == event and excerpts[excerptIndex]["sessionNumber"] == sessionNumber:
            fileName = baseFileName + f"F{fileNumber:02d}"
            startTime = Utils.StrToTimeDelta(excerpts[excerptIndex]["startTime"])
            
            endTimeStr = excerpts[excerptIndex]["endTime"].strip()
            if endTimeStr:
                excerptList.append((fileName,startTime,Utils.StrToTimeDelta(endTimeStr)))
            else:
                excerptList.append((fileName,startTime))
                
            excerptIndex += 1
            fileNumber += 1
        
        eventDir = os.path.join(gOptions.eventMp3Dir,event)
        sessionFilePath = os.path.join(eventDir,session["filename"])
        if not os.path.exists(sessionFilePath):
            print("Warning: Cannot locate "+sessionFilePath)
            continue
        
        outputDir = os.path.join(gOptions.excerptMp3Dir,event)
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
        
        allOutputFilesExist = True
        for x in excerptList:
            if not os.path.exists(os.path.join(outputDir,x[0]+'.mp3')):
                allOutputFilesExist = False
        
        if allOutputFilesExist and not gOptions.overwriteMp3:
            continue
        
        # We use eventDir as scratch space for newly generated mp3 files.
        # So first clean up any files left over from previous runs.
        for x in excerptList:
            scratchFilePath = os.path.join(eventDir,x[0]+'.mp3')
            if os.path.exists(scratchFilePath):
                os.remove(scratchFilePath)
        
        # Next invoke Mp3DirectCut:
        try:
            Mp3DirectCut.SplitMp3(sessionFilePath,excerptList)
        except Mp3DirectCut.ExecutableNotFound as err:
            print(err)
            print("Continuing to next module.")
            return
        except Mp3DirectCut.Mp3CutError as err:
            print(err)
            print("Continuing to next mp3 file.")
            continue
        
        # Now move the files to their destination
        for x in excerptList:
            scratchFilePath = os.path.join(eventDir,x[0]+'.mp3')
            outputFilePath = os.path.join(outputDir,x[0]+'.mp3')
            if os.path.exists(outputFilePath):
                os.remove(outputFilePath)
            
            os.rename(scratchFilePath,outputFilePath)
        
        mp3SplitCount += 1
        if gOptions.verbose >= 2:
            print(f"Split {session['filename']} into {len(excerptList)} files.")
    
    if gOptions.verbose > 0:
        print(f"   {mp3SplitCount} sessions split; all files already present for {sessionCount - mp3SplitCount} sessions.")