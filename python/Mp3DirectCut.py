"""Python wrapper to use mp3DirectCut to split mp3 files"""

import os, shutil
from datetime import time,timedelta
from typing import List

Executable = 'mp3DirectCut.exe'
ExecutableDir = 'mp3DirectCut'

class ExecutableNotFound(Exception):
    "Called when mp3DirectCut can't be found"
    pass
    
class Mp3CutError(Exception):
    "Called if mp3DirectCut returns with an error code"
    pass

def SetExecutable(directory,program='mp3DirectCut.exe'):
    global Executable,ExecutableDir
    
    Executable = program
    ExecutableDir = directory

def TimeToStr(time):
    "Convert a timedelta object to the form MM:SS:hh, where hh is in hundreths of seconds"
    
    minutes = time.seconds // 60
    seconds = time.seconds % 60
    hundreths = time.microseconds // 10000
    
    return f"{minutes:02d}:{seconds:02d}:{hundreths:02d}"

def WriteCue(cueTime,cueNum,cueFile):
    "Write a cue to a Mp3DirectCut .cue file"
    
    print(f'  TRACK {cueNum:02d} AUDIO',file=cueFile)
    print(f'    TITLE "(Track {cueNum:02d})"',file=cueFile)
    print(f'    INDEX 01 {TimeToStr(cueTime)}',file=cueFile)

def Split(file:str, splitPoints:List[tuple] ,outputDir:str = None,deleteCueFile:str = True):
    """Split an mp3 file into tracks.
    file - Name and path of the file to split. Write access is required to this directory.
    splitPoints - a list of tuples of the format: (trackFileName,startTime[,endTime])
        trackFileName: name of the track (without .mp3 suffix)
            Track files are saved in the same directory as the original file.
        startTime, endTime: timedelta objects describing the audio to cut
            Tracks must be cut from the original file in order.
            If endTime is omitted, there is no gap between the tracks.
    outputDir - move the splith mp3 files here; defaults to same directory as file
    deleteCueFile - delete cue file when finished?"""
    
    mp3DirectCutProgram = os.path.join(ExecutableDir,Executable)
    if not os.path.exists(mp3DirectCutProgram):
        raise ExecutableNotFound(f"mp3DirectCut.exe not found at {mp3DirectCutProgram}; cannot split mp3 files.")
    
    directory,originalFileName = os.path.split(file)
    fileNameBase,extension = os.path.splitext(originalFileName)
    cueFileName = fileNameBase + '.cue'
    
    cueFilePath = os.path.join(directory,cueFileName)
    cueFilePath = cueFilePath.replace('/','\\')
    with open(cueFilePath,'w') as cueFile:
        print('TITLE "(Title N.N.)"',file=cueFile)
        print(f'FILE "{originalFileName}" MP3',file=cueFile)
        
        trackNum = 1
        prevTrackEnd = timedelta(seconds = 0)
        WriteCue(prevTrackEnd,trackNum,cueFile)
        throwawayTracks = set()
        for point in splitPoints:
            if prevTrackEnd is not None:
                if point[1] < prevTrackEnd:
                    raise ValueError("Tracks to extract must be in sequential order.")
                elif point[1] > prevTrackEnd:
                    throwawayTracks.add(trackNum)
            
            if point[1] != prevTrackEnd:
                trackNum += 1
                WriteCue(point[1],trackNum,cueFile)
            
            if len(point) > 2:
                if point[1] >= point[2]:
                    raise ValueError("Track end must be after track begin.")
                trackNum += 1
                WriteCue(point[2],trackNum,cueFile)
                prevTrackEnd = point[2]
            else:
                prevTrackEnd = None
        
        if prevTrackEnd is not None: # If the last track has an end time, discard the last mp3 file from the split operation
            throwawayTracks.add(trackNum)
            
    totalTracks = trackNum
    trackNames = [fileNameBase + f' Track {track:02d}.mp3' for track in range(1,totalTracks + 1)]
    for name in trackNames:
        if os.path.exists(os.path.join(directory,name)):
            os.remove(os.path.join(directory,name))
    
    command = mp3DirectCutProgram + ' "' + cueFilePath + '" /split'
    result = os.system(command)
    if result:
        raise Mp3CutError(f"{command} returned code {result}; mp3 file not split.")
    
    if outputDir is None:
        outputDir = directory
        
    splitIndex = 0
    for trackNum in range(1,totalTracks + 1):
        trackFile = os.path.join(directory,trackNames[trackNum - 1])
        if trackNum in throwawayTracks:
            os.remove(trackFile)
        else:
            newName = os.path.join(outputDir,f'{splitPoints[splitIndex][0]}.mp3')
            if os.path.exists(newName):
                os.remove(newName)
            os.rename(trackFile,newName)
            splitIndex += 1
    
    if deleteCueFile:
        os.remove(cueFilePath)

def Join(fileList: List[str],outputFile: str,heal = True) -> None:
    """Join mp3 files into a single file using simple file copying operations.
    fileList: list of pathnames of the files to join.
    outFile: pathname of output file.
    heal: Use Mp3DirectCut to clean up the output file. Usually a good idea.
    This operation fails with mp3 files with different sample rates."""

    if len(fileList) == 1:
        heal = False # In this case, we're just copying the file

    name, ext = os.path.splitext(outputFile)
    tempFile = name + "_temp" + ext

    with open(tempFile,'wb') as dest:
        for fileName in fileList:
            with open(fileName,'rb') as source:
                shutil.copyfileobj(source, dest)
    
    if heal:
        dir, name = os.path.split(name)
        Split(tempFile,[(name,timedelta(0))],dir)
        os.remove(tempFile)
    else:
        os.rename(tempFile,outputFile)