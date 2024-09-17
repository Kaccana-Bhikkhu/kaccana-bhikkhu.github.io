"""Functions for reading and writing the json databases used in QSArchive."""

from collections.abc import Iterable
import json, re
import Html2 as Html
import Link
from Prototype import gDatabase
import SplitMp3
import Utils
import Alert
import Filter

gDatabase:dict[str] = {} # This will be set later by QSarchive.py

def LoadDatabase(filename: str) -> dict:
    """Read the database indicated by filename"""

    with open(filename, 'r', encoding='utf-8') as file: # Otherwise read the database from disk
        newDB = json.load(file)
    
    for x in newDB["excerpts"]:
        if "clips" in x:
            x["clips"] = [SplitMp3.Clip(*c) for c in x["clips"]]
    
    return newDB


def FindSession(sessions:list, event:str ,sessionNum: int) -> dict:
    "Return the session specified by event and sessionNum."

    for session in sessions:
        if session["event"] == event and session["sessionNumber"] == sessionNum:
            return session

    raise ValueError(f"Can't locate session {sessionNum} of event {event}")


def Mp3Link(item: dict,directoryDepth: int = 2) -> str:
    """Return a link to the mp3 file associated with a given excerpt or session.
    item: a dict representing an excerpt or session.
    directoryDepth: depth of the html file we are writing relative to the home directory"""

    if "fileNumber" in item and item["fileNumber"]: # Is this is a regular (non-session) excerpt?
        return Link.URL(item,directoryDepth=directoryDepth)

    session = FindSession(gDatabase["sessions"],item["event"],item["sessionNumber"])
    audioSource = gDatabase["audioSource"][session["filename"]]
    return Link.URL(audioSource,directoryDepth=directoryDepth)


def EventLink(event:str, session: int|None = None, fileNumber:int|None = None) -> str:
    "Return a link to a given event, session, and fileNumber. If session == None, link to the top of the event page"

    directory = "../events/"
    if session or fileNumber:
        return f"{directory}{event}.html#{ItemCode(event=event,session=session,fileNumber=fileNumber)}"
    else:
        return f"{directory}{event}.html"


def ItemCitation(item: dict) -> str:
    """Return html code with the name of the event, session number, and file number.
    item can be an event, session or excerpt"""

    event = item.get("event",None)
    session = item.get("sessionNumber",None)
    fileNumber = item.get("fileNumber",None)

    link = EventLink(event,session,fileNumber)

    eventName = gDatabase["event"][event]["title"]
    if not re.search(r"[0-9]{4}",eventName):
        eventYear = re.search(r"[0-9]{4}",event)
        if eventYear:
            eventName += f" ({eventYear[0]})"
    parts = [eventName]
    if session:
        parts.append(f"Session {session}")
    excerptNumber = item.get("excerptNumber",None)
    if excerptNumber:
        parts.append(f"Excerpt {excerptNumber}")
    text = ", ".join(parts)

    return Html.Tag("a",{"href":link})(text)


def TagLookup(tagRef:str,tagDictCache:dict = {}) -> str|None:
    "Search for a tag based on any of its various names. Return the base tag name."

    if not tagDictCache: # modify the value of a default argument to create a cache of potential tag references
        tagDB = gDatabase["tag"]
        tagDictCache.update((tag,tag) for tag in tagDB)
        tagDictCache.update((tagDB[tag]["fullTag"],tag) for tag in tagDB)
        tagDictCache.update((tagDB[tag]["pali"],tag) for tag in tagDB if tagDB[tag]["pali"])
        tagDictCache.update((tagDB[tag]["fullPali"],tag) for tag in tagDB if tagDB[tag]["fullPali"])

    return tagDictCache.get(tagRef,None)

def ParentTagListEntry(listIndex: int) -> dict|None:
    "Return a the entry in gDatabase['tagDisplayList'] that corresponds to this tag's parent tag."

    tagHierarchy = gDatabase["tagDisplayList"]
    level = tagHierarchy[listIndex]["level"]
    
    if level < 2:
        return None
    while (listIndex >= 0):
        if tagHierarchy[listIndex]["level"] < level:
            return tagHierarchy[listIndex]
        listIndex -= 1

    return None


def TeacherLookup(teacherRef:str,teacherDictCache:dict = {}) -> str|None:
    "Search for a tag based on any of its various names. Return the base tag name."

    if not teacherDictCache: # modify the value of a default argument to create a cache of potential teacher references
        teacherDB = gDatabase["teacher"]
        teacherDictCache.update((t,t) for t in teacherDB)
        teacherDictCache.update((teacherDB[t]["attributionName"],t) for t in teacherDB)
        teacherDictCache.update((teacherDB[t]["fullName"],t) for t in teacherDB)

    return teacherDictCache.get(teacherRef,None)


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
            args = [item['kind'],Utils.EllideText(item['text'])]
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

def SubsumesTags() -> dict:
    """Inverts gDatabase["tagSubsumed"] to create a dictionary of which tags a tag subsumes."""

    subsumesTags:dict[str,list[dict]] = {}

    for subsumedTag in gDatabase["tagSubsumed"].values():
        subsumesTags[subsumedTag["subsumedUnder"]] = subsumesTags.get(subsumedTag["subsumedUnder"],[]) + [subsumedTag]

    return subsumesTags

def FTagOrder(excerpt: dict,tags: Iterable[str]) -> int:
    """Return the fTagOrder number of the excerpt x.
    tags is a list of tags to attempt to get the fTag order from"""
    
    for tag in tags:
        try:
            fTagIndex = excerpt["fTags"].index(tag)
            return excerpt["fTagOrder"][fTagIndex]
        except (ValueError, IndexError):
            pass
    return 999

