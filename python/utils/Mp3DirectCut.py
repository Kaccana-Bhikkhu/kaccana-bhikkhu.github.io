"""Python wrapper to use mp3DirectCut to split mp3 files"""

from __future__ import annotations

import os, shutil, platform
import copy
from datetime import time,timedelta
from typing import List, Union, NamedTuple, Iterator, Iterable

Executable = 'mp3DirectCut.exe'
ExecutableDir = 'mp3DirectCut'
class Mp3CutError(Exception):
    "Raised if mp3DirectCut returns with an error code"
    pass

class ParseError(Mp3CutError):
    "Raised when a string can't be parsed into a time."
    pass

class TimeError(Mp3CutError):
    "Raised when a time value is invalid."
    pass
class ExecutableNotFound(Mp3CutError):
    "Raised when mp3DirectCut can't be found"
    pass

def SetExecutable(directory,program='mp3DirectCut.exe'):
    global Executable,ExecutableDir
    
    Executable = program
    ExecutableDir = directory

TimeSpec = Union[timedelta,float,str]
"A union of types that can indicate a time index to an audio file."

def ToTimeDelta(time: TimeSpec) -> timedelta|None:
    "Convert various types to a timedetla object."

    if type(time) == timedelta:
        return time
    
    try:
        floatVal = float(time)
        return timedelta(seconds=floatVal)
    except (ValueError,TypeError):
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
    
    raise ParseError(f"{repr(time)} cannot be converted to a time.")
    
class Clip(NamedTuple):
    """A Clip represents a section of a given audio file."""
    file: str                       # Filename of the audio file
    start: TimeSpec = timedelta(0)  # Clip start time
    end: TimeSpec|None = None       # Clip end time; None indicates the end of the file

    def ToClipTD(self) -> ClipTD:
        return ClipTD(self.file,ToTimeDelta(self.start),ToTimeDelta(self.end))
    
    def Duration(self,fileDuration:TimeSpec|None) -> timedelta:
        return self.ToClipTD().Duration(ToTimeDelta(fileDuration))

    def __eq__(self,other:Clip):
        return self.ToClipTD() == other.ToClipTD()

class ClipTD(Clip):
    """Same as a Clip, except the times must be of type timedelta."""
    start: timedelta
    end: timedelta

    def ToClipTD(self) -> ClipTD:
        return self

    def Duration(self,fileDuration:timedelta|None) -> timedelta:
        """Calculate the duration of this clip.
        Use fileDuration if self.end is None."""

        if fileDuration is not None:
            if self.start > fileDuration:
                raise TimeError(f"Start time {self.start} is later than file duration {fileDuration}.")
            if self.end and self.end > fileDuration:
                raise TimeError(f"End time {self.end} is later than file duration {fileDuration}.")
            
        if self.end:
            duration = self.end - self.start
            if duration <= timedelta(0):
                raise TimeError(f"Start time {self.start} is later than end time {self.end}.")
            return duration
        else:
            if fileDuration is None:
                raise TimeError("The clip end time and the file duration cannot both be blank.")
            else:
                return fileDuration - self.start

def TimeToCueStr(time):
    "Convert a timedelta object to the form MM:SS:hh, where hh is in hundreths of seconds"
    
    minutes = time.seconds // 60
    seconds = time.seconds % 60
    hundreths = time.microseconds // 10000
    
    return f"{minutes:02d}:{seconds:02d}:{hundreths:02d}"

def ConfigureMp3DirectCut() -> str:
    """Configure the Mp3DirectCut.exe application and return its path.
    Throw an exception if we can't find it or it won't run."""

    if platform.system() != "Windows":
        raise ExecutableNotFound(f"mp3DirectCut.exe only runs on Windows; cannot split mp3 files.")

    mp3DirectCutProgram = os.path.join(ExecutableDir,Executable)
    if not os.path.exists(mp3DirectCutProgram):
        raise ExecutableNotFound(f"mp3DirectCut.exe not found at {mp3DirectCutProgram}; cannot split mp3 files.")
    
    return mp3DirectCutProgram


def WriteCue(cueTime,cueNum,cueFile):
    "Write a cue to a Mp3DirectCut .cue file"
    print(f'  TRACK {cueNum:02d} AUDIO',file=cueFile)
    print(f'    TITLE "(Track {cueNum:02d})"',file=cueFile)
    print(f'    INDEX 01 {TimeToCueStr(cueTime)}',file=cueFile)

def SinglePassSplit(file:str, clips:list[ClipTD],outputDir:str = None,deleteCueFile:str = True) -> None:
    """Run Mp3DirectCut once to split an mp3 file into tracks.
    This function forms the base for functions like Split and MultiFileSplitJoin.
    file - Name and path of the file to split. Write access is required to this directory.
    clips - a list of clips to split the file into. The fields are:
        file (str): - the name of the output file for this clip.
        start (timedelta): the starting time of the clip.
        end (timedelta): the ending time of the clip.
            If end == None, the clip extends to the beginning of the next clip or the end of the file.
    The clips must be sorted by start time and cannot overlap.
    outputDir - move the splith mp3 files here; defaults to same directory as file
    deleteCueFile - delete cue file when finished?"""
    
    mp3DirectCutProgram = ConfigureMp3DirectCut()

    directory,originalFileName = os.path.split(file)
    fileNameBase,extension = os.path.splitext(originalFileName)
    cueFileName = fileNameBase + '.cue'
    
    cueFilePath = os.path.join(directory,cueFileName)
    cueFilePath = cueFilePath.replace('/','\\')
    with open(cueFilePath,'w', encoding='utf-8') as cueFile:
        print('TITLE "(Title N.N.)"',file=cueFile)
        print(f'FILE "{originalFileName}" MP3',file=cueFile)
        
        trackNum = 1
        prevClipEnd = timedelta(seconds = 0)
        WriteCue(prevClipEnd,trackNum,cueFile)
        throwawayTracks = set()
        for clip in clips:
            if prevClipEnd is not None:
                if clip.start < prevClipEnd:
                    raise TimeError(f"Split point {clip}: Clips to extract must be in sequential order.")
                elif clip.start > prevClipEnd:
                    throwawayTracks.add(trackNum)
            
            if clip.start != prevClipEnd:
                trackNum += 1
                WriteCue(clip.start,trackNum,cueFile)
            
            if clip.end:
                if clip.start >= clip.end:
                    raise TimeError(f"Split point {clip}: Clip end must be after clip start.")
                trackNum += 1
                WriteCue(clip.end,trackNum,cueFile)
                prevClipEnd = clip.end
            else:
                prevClipEnd = None
        
        if prevClipEnd is not None: # If the last track has an end time, discard the last mp3 file from the split operation
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
            newName = os.path.join(outputDir,clips[splitIndex].file)
            if os.path.exists(newName):
                os.remove(newName)
            os.rename(trackFile,newName)
            splitIndex += 1
    
    if deleteCueFile:
        os.remove(cueFilePath)

def Split(file:str, clips:list[Clip],outputDir:str = None,deleteCueFile:str = True) -> None:
    """Run Mp3DirectCut (possibly multiple times) to split an mp3 file into tracks.
    file - Name and path of the file to split. Write access is required to this directory.
    clips - a list of clips to split the file into. The fields are:
        file (str): - the name of the output file for this clip.
        start: the starting time of the clip.
        end: the ending time of the clip; None or blank means until the end of the file.
    The clips need not be sorted and can overlap.
    outputDir - move the splith mp3 files here; defaults to same directory as file
    deleteCueFile - delete cue file when finished?"""

    clipsRemaining = [clip.ToClipTD() for clip in clips]
    clipsRemaining.sort(key = lambda clip:clip.start)
    while clipsRemaining:
        lastClipEnd = timedelta(0)
        clipsToSplit = []
        clipsNotSplit = []
        for clip in clipsRemaining:
            if lastClipEnd is not None and clip.start >= lastClipEnd:
                clipsToSplit.append(clip)
                lastClipEnd = clip.end
            else:
                clipsNotSplit.append(clip)
        
        SinglePassSplit(file,clipsToSplit,outputDir)
        clipsRemaining = clipsNotSplit

def SourceFiles(clips:Clip|Iterable[Clip]|dict[object,Clip]) -> set[str]:
    """Iterate recursively over clips and return the set of all source files used."""
    if isinstance(clips,Clip):
        return {clips.file}
    if hasattr(clips,"values"):
        return SourceFiles(clips.values())
    sources = set()
    if isinstance(clips,Iterable):
        for item in clips:
            sources.update(SourceFiles(item))
    return sources

def GroupBySourceFiles(outputFiles:dict[str,list[Clip]]) -> Iterator[tuple[set[str],dict[str,list[Clip]]]]:
    """Group the outputFiles by source files. Returns an iterator of tuples:
    (sourceFiles,theseOutputFiles), where sourceFiles is a set of source files and theseOutputFiles is the dict of files that use
    these source files."""

    filesRemaining = outputFiles
    while filesRemaining:
        sourceFiles:set[str] = SourceFiles(next(iter(filesRemaining.values())))
            # Begin with the first file of the first item in clipsRemaining
        prevSourceFiles:set[str] = set()

        while (prevSourceFiles != sourceFiles):
            filesWithTheseSources:dict[str,list[Clip]] = {}
            for filename,clips in filesRemaining.items():
                for clip in clips:
                    if clip.file in sourceFiles:
                        filesWithTheseSources[filename] = clips
            
            prevSourceFiles = sourceFiles
            sourceFiles = SourceFiles(filesWithTheseSources)
        
        yield sourceFiles,filesWithTheseSources
        filesRemaining = {file:clips for file,clips in filesRemaining.items() if file not in filesWithTheseSources}

def MultiFileSplitJoin(fileClips:dict[str,list[Clip]],inputDir:str = ".",outputDir:str|None = None) -> None:
    """Split and join multiple mp3 files using Mp3DirectCut.
    fileClips: each key is the name of a file to create in outputDir.
        each value is a list of Clips to join. The Clip fields mean:
            file: the name of a file in inputDir
            start: the start time of the audio to extract
            end: the end time of the audio to extract; None means end of file.
    inputDir: directory for input files.
    outputDir: directory for output files. None means same as inputDir."""

    if outputDir is None:
        outputDir = inputDir

    for sourceFiles,selectFileClips in GroupBySourceFiles(fileClips):

        # Strategy: Create dictionaries describing the operations that need to be executed, then run these operations

        splitOps:dict[Clip,str] = {} 
            # key: the clip that we need to split (clip file relative to inputDir)
            # value: the filename where the clip will be split to (relative to outputDir) 
            # can be either a final output file which doesn't require joining or a temporary file
        joinOps:dict[str,list[Clip]] = {}
            # keys: the name of a final output file that requires joining (relative to outputDir)
            # values: the clips to join to create the final output file (clip files relative to outputDir)
        
        tempFilePrefix = "__QStemp_"
        tempFileCount = 0

        for outputFile,clips in selectFileClips.items():
            if len(clips) > 1:
                for clip in clips:
                    clipFile = splitOps.get(clip.file,"")
                    if not clipFile:
                        tempFileCount += 1
                        clipFile = f"{tempFilePrefix}{tempFileCount:02d}.mp3"
                        splitOps[clip] = clipFile
                joinOps[outputFile] = clips
            else:
                existingFilename = splitOps.get(clips[0],"")
                if not existingFilename or existingFilename.startsWith(tempFilePrefix):
                        # If we haven't split clip before or it splits to a temporary file,
                    splitOps[clips[0]] = outputFile
                        # register a new splitOp or redirect an existing splitOp away from the temporary file.
                else:
                    joinOps[outputFile] = [existingFilename]
                        # Otherwise copy an existing file.

        for sourceFile in sourceFiles:
            clipsWithDestFile = [clip._replace(file = dest) for clip,dest in splitOps.items() if clip.file == sourceFile]
            sourcePath = os.path.join(inputDir,sourceFile)
            Split(sourcePath,clipsWithDestFile,outputDir)

        for outputFile,clipsToJoin in joinOps.items():
            destPath = os.path.join(outputDir,outputFile)
            joinFiles = [os.path.join(outputDir,splitOps[clip]) for clip in clipsToJoin]
            Join(joinFiles,destPath)
        

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
        dir, filename = os.path.split(outputFile)
        SinglePassSplit(tempFile,[ClipTD(filename,timedelta(0),None)],dir)
        os.remove(tempFile)
    else:
        os.rename(tempFile,outputFile)
