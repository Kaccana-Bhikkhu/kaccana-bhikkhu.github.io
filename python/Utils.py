"""Utility files to support QAarchive.py modules"""

from __future__ import annotations

from datetime import timedelta, datetime
import copy
import unicodedata
import re
from typing import List
import Alert
import pathlib

gOptions = None
gDatabase = None # These will be set later by QSarchive.py

def Contents(container:list|dict) -> list:
    try:
        return container.values()
    except AttributeError:
        return container

def AppendUnique(dest: list, source: list) -> list:
    "Append the items in source to dest, preserving order but eliminating duplicates."

    destSet = set(dest)
    for item in source:
        if item not in destSet:
            dest.append(item)

def ItemCode(item:dict|None = None, event:str = "", session:int|None = None, fileNumber:int|None = None) -> str:
    "Return a code for this item. "

    if item:
        event = item.get("event",None)
        session = item.get("sessionNumber",None)
        fileNumber = item.get("fileNumber",None)
    
    outputStr = event
    if session is not None:
        outputStr += f"_S{session:02d}"
    if fileNumber is not None:
        outputStr += f"_F{fileNumber:02d}"
    return outputStr

def PosixJoin(*paths):
    "Join directories using / to make nicer html code. Python handles / in pathnames graciously even on Windows."
    return str(pathlib.PurePosixPath(*paths))

def Mp3Link(item: dict,directoryDepth: int = 2) -> str:
    """Return a link to the mp3 file associated with a given excerpt or session.
    item: a dict representing an excerpt or session.
    directoryDepth: depth of the html file we are writing relative to the home directory"""

    if "fileNumber" in item and item["fileNumber"]: # Is this is a non-session excerpt?
        if gOptions.excerptMp3 == 'local':
            baseURL = ("../" * directoryDepth) + "audio/excerpts/"
        else:
            baseURL = gOptions.remoteExcerptMp3URL

        return f"{baseURL}{item['event']}/{ItemCode(item)}.mp3"
    
    session = FindSession(gDatabase["sessions"],item["event"],item["sessionNumber"])
    if gOptions.sessionMp3 == "local":
        return ("../" * directoryDepth) + "audio/events/" + "/" + session["event"] + "/" + session["filename"]
    else:
        return session["remoteMp3Url"]

def SearchForOwningExcerpt(annotation: dict) -> dict:
    """Search the global database of excerpts to find which one owns this annotation.
    This is a slow function and should be called infrequently."""
    if not gDatabase:
        return None
    for x in gDatabase["excerpts"]:
        for a in x["annotations"]:
            if annotation is a:
                return x
    return None

def EllideText(s: str,maxLength = 50) -> str:
    "Truncate a string to keep the number of characters under maxLength."
    if len(s) <= maxLength:
        return s
    else:
        return s[:maxLength - 3] + "..."

def ItemRepr(item: dict) -> str:
    """Generate a repr-style string for various dict types in gDatabase. 
    Check the dict keys to guess what it is.
    If we can't identify it, return repr(item)."""

    if type(item) == dict:
        if "tag" in item:
            if "level" in item:
                kind = "tagDisplay"
            else:
                kind = "tag"
            return(f"{kind}({repr(item['tag'])})")
        
        event = session = fileNumber = None
        args = []
        if "code" in item and "subtitle" in item:
            kind = "event"
            event = item["code"]
        elif "sessionTitle" in item:
            kind = "session"
            event = item["event"]
            session = item["sessionNumber"]
        elif "kind" in item and "sessionNumber" in item:
            if "annotations" in item:
                kind = "excerpt"
                event = item["event"]
                session = item["sessionNumber"]
                fileNumber = item.get("fileNumber",None)
            else:
                kind = "annotation"
                x = SearchForOwningExcerpt(item)
                if x:
                    event = x["event"]
                    session = x["sessionNumber"]
            args = [item['kind'],EllideText(item['text'])]
        else:   
            return(repr(item))
        
        if event:
            name = event
            if session is not None:
                name += f"_S{session:02d}"
            if fileNumber is not None:
                name += f"_F{fileNumber:02d}"
            args = [name] + args
        
        return f"{kind}({', '.join(repr(i) for i in args)})"
    else:
        return repr(item)

def StrToTimeDelta(inStr):
    "Convert a string with format mm:ss or hh:mm:ss to a timedelta object"
    
    numbers = str.split(inStr,":")
    try:
        if len(numbers) == 2:
            return timedelta(minutes = int(numbers[0]),seconds = int(numbers[1]))
        elif len(numbers) == 3:
            return timedelta(hours = int(numbers[0]),minutes = int(numbers[1]),seconds = int(numbers[2]))
    except ValueError:
        pass
        
    raise ValueError("'" + inStr + "' cannot be converted to a time.")

def TimeDeltaToStr(time):
    "Convert a timedelta object to the form [HH:]MM:SS"
    
    seconds = (time.days * 24 * 60 * 60) + time.seconds
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def ReformatDate(dateStr:str, formatStr:str = "%b %d, %Y") -> str:
    "Take a date formated as DD/MM/YYYY and reformat it as mmm d YYYY."
    
    date = datetime.strptime(dateStr,"%d/%m/%Y")
    
    return f'{date.strftime("%b. ")} {int(date.day)}, {int(date.year)}'

def FindSession(sessions:list, event:str ,sessionNum: int) -> dict:
    "Return the session specified by event and sessionNum."
    
    for session in sessions:
        if session["event"] == event and session["sessionNumber"] == sessionNum:
            return session
    
    raise ValueError(f"Can't locate session {sessionNum} of event {event}")

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def RegexMatchAny(strings: List[str],capturingGroup = True):
    """Return a regular expression that matches any item in strings.
    Optionally make it a capturing group."""

    if strings:
        if capturingGroup:
            return r"(" + r"|".join(strings) + r")"
        else:
            return r"(?:" + r"|".join(strings) + r")"
    else:
        return r'a\bc' # Looking for a word boundary between text characters always fails: https://stackoverflow.com/questions/1723182/a-regex-that-will-never-be-matched-by-anything


def ReorderKeys(ioDict: dict,firstKeys = [],lastKeys = []) -> None:
    "Reorder the keys in ioDict"

    spareDict = copy.copy(ioDict) # Make a shallow copy
    ioDict.clear()

    for key in firstKeys:
        ioDict[key] = spareDict.pop(key)

    for key in spareDict:
        if key not in lastKeys:
            ioDict[key] = spareDict[key]

    for key in lastKeys:
        ioDict[key] = spareDict[key]

def SummarizeDict(d: dict,printer: Alert.AlertClass) -> None:
    "Print a summary of dict d, one line per key."
    for key,value in d.items():
        desc = f"{key}: {value.__class__.__name__}"
        try:
            desc += f"[{len(value)}]"
        except TypeError:
            pass
        printer.Show(desc)
    