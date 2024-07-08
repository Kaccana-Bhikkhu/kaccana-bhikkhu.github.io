"""Utility files to support QAarchive.py modules"""

from __future__ import annotations

from datetime import timedelta, datetime
import copy
import re, os,argparse
from urllib.parse import urlparse
from typing import BinaryIO
import Alert, Link
import pathlib, posixpath
from collections import Counter
from collections.abc import Iterable
from urllib.parse import urljoin,urlparse,quote,urlunparse
import urllib.request, urllib.error
from DjangoTextUtils import slugify,RemoveDiacritics
from concurrent.futures import ThreadPoolExecutor

gOptions = None
gDatabase:dict[str] = {} # These will be set later by QSarchive.py

def Contents(container:list|dict) -> list:
    try:
        return container.values()
    except AttributeError:
        return container

def ExtendUnique(dest: list, source: Iterable) -> list:
    "Append all the items in source to dest, preserving order but eliminating duplicates."

    destSet = set(dest)
    for item in source:
        if item not in destSet:
            dest.append(item)
    return dest

def Duplicates(source: Iterable) -> list:
    "Return a list of the item which appear more than once in source."
    itemCount = Counter(source)
    return [item for item,count in itemCount.items() if count > 1]

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

def ParseItemCode(itemCode:str) -> tuple[str,int|None,int|None]:
    "Parse an item code into (eventCode,session,fileNumber). If parsing fails, return ("",None,None)."

    m = re.match(r"([^_]*)(?:_S([0-9]+))?(?:_F([0-9]+))?",itemCode)
    session = None
    fileNumber = None
    if m:
        if m[2]:
            session = int(m[2])
        if m[3]:
            fileNumber = int(m[3])
        return m[1],session,fileNumber
    else:
        return "",None,None

def PosixToWindows(path:str) -> str:
    return str(pathlib.PureWindowsPath(pathlib.PurePosixPath(path)))

PosixJoin = posixpath.join
PosixSplit = posixpath.split

def DirectoryURL(url:str) -> str:
    "Ensure that this url specifies a directory path."
    if url.endswith("/"):
        return url
    else:
        return url + "/"

def RemoteURL(url:str) -> bool:
    "Does this point to a remote file server?"
    return bool(urlparse(url).netloc)

def QuotePath(url:str) -> str:
    """If the path section of url contains any % characters, assume it's already been quoted.
    Otherwise quote it."""

    parsed = urlparse(url)
    if "%" in parsed.path:
        return url
    else:
        return urlunparse(parsed._replace(path=quote(parsed.path)))

def OpenUrlOrFile(url:str) -> BinaryIO:
    """Determine whether url represents a remote URL or local file, open it for reading, and return a handle."""
    
    if RemoteURL(url):
        url = QuotePath(url)
        return urllib.request.urlopen(url)
    else:
        return open(url,"rb")

def SwitchedMoveFile(locationFalse: str,locationTrue: str,switch: bool) -> bool:
    """Move a file to either locationFalse or locationTrue depending on the value of switch.
    Raise FileExistsError if both locations are occupied.
    Return True if the file was moved."""
    if switch:
        moveTo,moveFrom = locationTrue,locationFalse
    else:
        moveTo,moveFrom = locationFalse,locationTrue
    
    if os.path.isfile(moveFrom):
        if os.path.isfile(moveTo):
            raise FileExistsError(f"Cannot move {moveFrom} to overwrite {moveTo}.")
        os.makedirs(PosixSplit(moveTo)[0],exist_ok=True)
        os.rename(moveFrom,moveTo)
        return True
    return False

def MoveFile(fromPath: str,toPath: str) -> bool:
    return SwitchedMoveFile(fromPath,toPath,True)

def ReplaceExtension(filename:str, newExt: str) -> str:
    "Replace the extension of filename before the file extension"
    name,_ = os.path.splitext(filename)
    return name + newExt

def AppendToFilename(filename:str, appendStr: str) -> str:
    "Append to fileName before the file extension"
    name,ext = os.path.splitext(filename)
    return name + appendStr + ext

def Mp3Link(item: dict,directoryDepth: int = 2) -> str:
    """Return a link to the mp3 file associated with a given excerpt or session.
    item: a dict representing an excerpt or session.
    directoryDepth: depth of the html file we are writing relative to the home directory"""

    if "fileNumber" in item and item["fileNumber"]: # Is this is a regular (non-session) excerpt?
        return Link.URL(item,directoryDepth=directoryDepth)
    
    session = FindSession(gDatabase["sessions"],item["event"],item["sessionNumber"])
    audioSource = gDatabase["audioSource"][session["filename"]]
    return Link.URL(audioSource,directoryDepth=directoryDepth)

def TagLookup(tagRef:str,tagDictCache:dict = {}) -> str|None:
    "Search for a tag based on any of its various names. Return the base tag name."

    if not tagDictCache: # modify the value of a default argument to create a cache of potential tag references
        tagDB = gDatabase["tag"]
        tagDictCache.update((tag,tag) for tag in tagDB)
        tagDictCache.update((tagDB[tag]["fullTag"],tag) for tag in tagDB)
        tagDictCache.update((tagDB[tag]["pali"],tag) for tag in tagDB if tagDB[tag]["pali"])
        tagDictCache.update((tagDB[tag]["fullPali"],tag) for tag in tagDB if tagDB[tag]["fullPali"])
    
    return tagDictCache.get(tagRef,None)

def TeacherLookup(teacherRef:str,teacherDictCache:dict = {}) -> str|None:
    "Search for a tag based on any of its various names. Return the base tag name."

    if not teacherDictCache: # modify the value of a default argument to create a cache of potential teacher references
        teacherDB = gDatabase["teacher"]
        teacherDictCache.update((t,t) for t in teacherDB)
        teacherDictCache.update((teacherDB[t]["attributionName"],t) for t in teacherDB)
        teacherDictCache.update((teacherDB[t]["fullName"],t) for t in teacherDB)
    
    return teacherDictCache.get(teacherRef,None)

def AboutPageLookup(pageName:str,aboutPageCache:dict = {}) -> str|None:
    "Search for an about page based on its name. Return the path to the page relative to prototypeDir."

    if not aboutPageCache: # modify the value of a default argument to create a cache of potential tag references
        dirs = ["about"]
        for dir in dirs:
            fileList = os.listdir(PosixJoin(gOptions.prototypeDir,dir))
            for file in fileList:
                m = re.match(r"[0-9]*_?(.*)\.html",file)
                if m:
                    aboutPageCache[m[1].lower()] = PosixJoin(dir,m[0])

    return aboutPageCache.get(pageName.lower().replace(" ","-"),None)

def Singular(noun: str) -> str:
    "Use simple rules to guess the singular form or a noun."
    if noun.endswith("ies"):
        return noun[:-3] + "y"
    else:
        return noun.rstrip("s")

def EllideText(s: str,maxLength = 50) -> str:
    "Truncate a string to keep the number of characters under maxLength."
    if len(s) <= maxLength:
        return s
    else:
        return s[:maxLength - 3] + "..."

def SmartQuotes(s: str):
    """Takes a string and returns it with dumb quotes, single and double,
    replaced by smart quotes. Accounts for the possibility of HTML tags
    within the string.
    Based on https://gist.github.com/davidtheclark/5521432"""

    # Find dumb double quotes coming directly after letters or punctuation,
    # and replace them with right double quotes.
    s = re.sub(r'([a-zA-Z0-9.,?!;:/\'\"])"', r'\1”', s)
    # Find any remaining dumb double quotes and replace them with
    # left double quotes.
    s = s.replace('"', '“')
    # Reverse: Find any SMART quotes that have been (mistakenly) placed around HTML
    # attributes (following =) and replace them with dumb quotes.
    s = re.sub(r'=“(.*?)”', r'="\1"', s)
    # Follow the same process with dumb/smart single quotes
    s = re.sub(r"([a-zA-Z0-9.,?!;:/\"\'])'", r'\1’', s)
    s = s.replace("'", '‘')
    s = re.sub(r'=‘(.*?)’', r"='\1'", s)
    return s

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
                x = FindOwningExcerpt(item)
                if x:
                    event = x["event"]
                    session = x["sessionNumber"]
            args = [item['kind'],EllideText(item['text'])]
        elif "pdfPageOffset" in item:
            kind = "reference"
            args.append(item["abbreviation"])
        elif "url" in item:
            kind = "audioSource"
            args = [item["event"],item["filename"]]
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

def ParseDate(dateStr:str) -> datetime.date:
    "Read a date formated as DD/MM/YYYY and return datetime.date."
    
    return datetime.strptime(dateStr,"%d/%m/%Y").date()

def ReformatDate(dateStr:str,fullMonth:bool = False) -> str:
    "Take a date formated as DD/MM/YYYY and reformat it as mmm d YYYY."
    
    date = ParseDate(dateStr)
    
    return f'{date.strftime("%B" if fullMonth else "%b.")} {int(date.day)}, {int(date.year)}'

def ModificationDate(file:str) -> datetime:
    info = os.stat(file)
    return datetime.fromtimestamp(info.st_mtime)

def DependenciesModified(file:str,dependencies:Iterable[str]) -> bool:
    """Returns true if any of the file paths specified in dependencies has a later modification date than file."""

    try:
        fileDate = ModificationDate(file)
        for d in dependencies:
            if ModificationDate(d) >= fileDate:
                return True
        return False
    except FileNotFoundError:
        return True

def FindSession(sessions:list, event:str ,sessionNum: int) -> dict:
    "Return the session specified by event and sessionNum."
    
    for session in sessions:
        if session["event"] == event and session["sessionNumber"] == sessionNum:
            return session
    
    raise ValueError(f"Can't locate session {sessionNum} of event {event}")

def SessionIndex(sessions:list, event:str ,sessionNum: int) -> int:
    "Return the session specified by event and sessionNum."
    
    for n,session in enumerate(sessions):
        if session["event"] == event and session["sessionNumber"] == sessionNum:
            return n
    
    raise ValueError(f"Can't locate session {sessionNum} of event {event}")

def FindExcerpt(event: str, session: int|None, fileNumber: int|None) -> dict|None:
    "Return the excerpt that matches these parameters. Otherwise return None."

    if not gDatabase:
        return None
    if not event or fileNumber is None:
        return None
    if session is None:
        session = 0
    for x in gDatabase["excerpts"]:
        if x["event"] == event and x["sessionNumber"] == session and x["fileNumber"] == fileNumber:
            return x
    return None

def FindOwningExcerpt(annotation: dict) -> dict:
    """Search the global database of excerpts to find which one owns this annotation.
    This is a slow function and should be called infrequently."""
    if not gDatabase:
        return None
    for x in gDatabase["excerpts"]:
        for a in x["annotations"]:
            if annotation is a:
                return x
    return None

def SubAnnotations(excerpt: dict,annotation: dict) -> list[dict]:
    """Return the annotations that are under this annotation or excerpt."""

    if annotation is excerpt:
        scanLevel = 1
        scanning = True
    else:
        scanLevel = annotation["indentLevel"] + 1
        scanning = False
    
    subs = []
    for a in excerpt["annotations"]:
        if scanning:
            if a["indentLevel"] == scanLevel:
                subs.append(a)
            elif a["indentLevel"] < scanLevel:
                scanning = False
        elif a is annotation:
            scanning = True

    return subs

def ParentAnnotation(excerpt: dict,annotation: dict) -> dict|None:
    """Return this annotation's parent."""
    if not annotation or annotation is excerpt:
        return None
    if annotation["indentLevel"] == 1:
        return excerpt
    searchForLevel = 0
    found = False
    for searchAnnotation in reversed(excerpt["annotations"]):
        if searchAnnotation["indentLevel"] == searchForLevel:
            return searchAnnotation
        if searchAnnotation is annotation:
            searchForLevel = annotation["indentLevel"] - 1
    if not found:
        Alert.error("Annotation",annotation,"doesn't have a proper parent.")
        return None

def SubtagDescription(tag: str) -> str:
    "Return a string describing this tag's subtags."
    primary = gDatabase["tag"][tag]["listIndex"]
    listEntry = gDatabase["tagDisplayList"][primary]
    return f'{listEntry["subtagCount"]} subtags, {listEntry["subtagExcerptCount"]} excerpts'


def GroupBySession(excerpts: list[dict],sessions: list[dict]|None = None) -> Iterable[tuple[dict,list[dict]]]:
    """Yield excerpts grouped by their session."""
    if not sessions:
        sessions = gDatabase["sessions"]
    sessionIterator = iter(sessions)
    curSession = next(sessionIterator)
    yieldList = []
    for excerpt in excerpts:
        while excerpt["event"] != curSession["event"] or excerpt["sessionNumber"] != curSession["sessionNumber"]:
            if yieldList:
                yield curSession,yieldList
                yieldList = []
            curSession = next(sessionIterator)
        yieldList.append(excerpt)
    
    if yieldList:
        yield curSession,yieldList

def GroupByEvent(excerpts: list[dict],events: dict[dict]|None = None) -> Iterable[tuple[dict,list[dict]]]:
    """Yield excerpts grouped by their event. NOT YET TESTED"""
    if not events:
        events = gDatabase["event"]
    yieldList = []
    curEvent = ""
    for excerpt in excerpts:
        while excerpt["event"] != curEvent:
            if yieldList:
                yield events[curEvent],yieldList
                yieldList = []
            curEvent = excerpt["event"]
        yieldList.append(excerpt)
    
    if yieldList:
        yield events[curEvent],yieldList

def PairWithSession(excerpts: list[dict],sessions: list[dict]|None = None) -> Iterable[tuple[dict,dict]]:
    """Yield tuples (session,excerpt) for all excerpts."""
    if not sessions:
        sessions = gDatabase["sessions"]
    
    for session,excerptList in GroupBySession(excerpts,sessions):
        yield from ((session,x) for x in excerptList)



def RegexMatchAny(strings: Iterable[str],capturingGroup = True,literal = False):
    """Return a regular expression that matches any item in strings.
    Optionally make it a capturing group."""

    if literal:
        strings = [re.escape(s) for s in strings]
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
        printer(desc)

class MockFuture():
    def __init__(self, result) -> None:
        self.result = result
    def result(self, timeout=None):
        return self.result
    def cancel(self):
        pass

class MockThreadPoolExecutor():
    """Don't execute any threads for testing purposes.
    https://stackoverflow.com/questions/10434593/dummyexecutor-for-pythons-futures"""
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    def submit(self, fn, *args, **kwargs):
        # execute functions in series without creating threads
        # for easier unit testing
        result = fn(*args, **kwargs)
        return MockFuture(result)

    def shutdown(self, wait=True):
        pass

def ConditionalThreader() -> ThreadPoolExecutor|MockThreadPoolExecutor:
    return ThreadPoolExecutor() if gOptions.multithread else MockThreadPoolExecutor()

try:
    STORE_TRUE = dict(action=argparse.BooleanOptionalAction,default=False)
except AttributeError:
    STORE_TRUE = dict(action="store_true")