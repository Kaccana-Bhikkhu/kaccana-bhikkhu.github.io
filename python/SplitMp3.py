"""Use Mp3DirectCut.exe to split the session audio files into individual questions based on start and end times from database.json"""

import os, json
from Utils import StrToTimeDelta, Mp3FileName
import Mp3DirectCut as Mp3DirectCut
from typing import List

Mp3DirectCut.SetExecutable(os.path.join('tools','Mp3DirectCut'))

def IncludeRedactedQuestions() -> List[dict]:
    "Merge the redacted questions back into the main list in order to split mp3 files"
    
    allQuestions = gDatabase["Questions"] + gDatabase["Questions_Redacted"]
    print(len(allQuestions))
    orderedEvents = list(gDatabase["Event"].keys()) # Look up the event in this list to sort questions by event order in gDatabase
    
    allQuestions.sort(key = lambda q: (orderedEvents.index(q["Event"]),q["Session #"],q["File #"]))
        # Sort by event, then by session, then by file number
    
    return allQuestions

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--eventMp3Dir',type=str,default=os.path.join('audio','events'),help='Read session mp3 files from this directory; Default: ./audio/events')
    parser.add_argument('--questionMp3Dir',type=str,default=os.path.join('audio','questions'),help='Write question mp3 files from this directory; Default: ./audio/questions')
    parser.add_argument('--overwriteMp3',action='store_true',help="Overwrite existing mp3 files; otherwise leave existing files untouched")

gOptions = None
gDatabase = None
def main(clOptions):
    """ Split the Q&A session mp3 files into individual questions.
    Read the beginning and end points from database.json."""
    
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    with open(gOptions.jsonFile, 'r', encoding='utf-8') as file:
        gDatabase = json.load(file)
    
    questionIndex = 0
    questions = IncludeRedactedQuestions()
    for session in gDatabase["Sessions"]:
        
        sessionNumber = session["Session #"]
        event = session["Event"]
        questionList = []
        fileNumber = 1
        
        baseFileName = f"{event}_S{sessionNumber:02d}_"
        while questionIndex < len(questions) and questions[questionIndex]["Event"] == event and questions[questionIndex]["Session #"] == sessionNumber:
            fileName = baseFileName + f"Q{fileNumber:02d}"
            startTime = StrToTimeDelta(questions[questionIndex]["Start time"])
            
            endTimeStr = questions[questionIndex]["End time"].strip()
            if endTimeStr:
                questionList.append((fileName,startTime,StrToTimeDelta(endTime)))
            else:
                questionList.append((fileName,startTime))
                
            questionIndex += 1
            fileNumber += 1
        
        eventDir = os.path.join(gOptions.eventMp3Dir,event)
        sessionFilePath = os.path.join(eventDir,session["Filename"])
        if not os.path.exists(sessionFilePath):
            print("Warning: Cannot locate "+sessionFilePath)
            continue
        
        outputDir = os.path.join(gOptions.questionMp3Dir,event)
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
        
        allOutputFilesExist = True
        for q in questionList:
            if not os.path.exists(os.path.join(outputDir,q[0]+'.mp3')):
                allOutputFilesExist = False
        
        if allOutputFilesExist and not gOptions.overwriteMp3:
            continue
        
        # We use eventDir as scratch space for newly generated mp3 files.
        # So first clean up any files left over from previous runs.
        for q in questionList:
            scratchFilePath = os.path.join(eventDir,q[0]+'.mp3')
            if os.path.exists(scratchFilePath):
                os.remove(scratchFilePath)
        
        # Next invoke Mp3DirectCut:
        try:
            Mp3DirectCut.SplitMp3(sessionFilePath,questionList)
        except Mp3DirectCut.ExecutableNotFound as err:
            print(err)
            print("Continuing to next module.")
            return
        except Mp3DirectCut.Mp3CutError as err:
            print(err)
            print("Continuing to next mp3 file.")
            continue
        
        # Now move the files to their destination
        for q in questionList:
            scratchFilePath = os.path.join(eventDir,q[0]+'.mp3')
            outputFilePath = os.path.join(outputDir,q[0]+'.mp3')
            if os.path.exists(outputFilePath):
                if gOptions.overwriteMp3:
                    os.remove(outputFilePath)
                else:
                    os.remove(scratchFilePath)
                    continue
            
            os.rename(scratchFilePath,outputFilePath)
        
        if gOptions.verbose >= 2:
            print(f"Split {session['Filename']} into {len(questionList)} files.")