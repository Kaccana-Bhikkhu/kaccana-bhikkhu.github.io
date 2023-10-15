"""Add a "mirror" field to each session, excerpt and reference indicating which hyperlink the item should use.
LinkValidator and its subclasses determine whether a given hyperlink is valid.
"""

from __future__ import annotations

import os
from functools import reduce
from datetime import timedelta
from io import BytesIO
import Utils, Alert
from urllib.parse import urljoin,urlparse
import urllib.request, urllib.error
from mutagen.mp3 import MP3
from typing import Tuple, Type, Callable, Iterable, BinaryIO
from enum import Enum
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import math

class StrEnum(str,Enum):
    pass

class ItemType(StrEnum): # The kinds of items we will link to
    SESSION = "sessionMp3"
    EXCERPT = "excerptMp3"
    REFRENCE = "reference"

def AutoType(item:dict) -> ItemType:
    if "fileNumber" in item:
        return ItemType.EXCERPT
    elif "sessionTitle" in item:
        return ItemType.SESSION
    elif "pdfPageOffset" in item:
        return ItemType.REFRENCE
    
    Alert.error("Autotype: unknown type",item)

class LinkValidator:
    """For a given item and URL, determine whether the link is valid.
    The base class checks to see if local files exist but assumes remote URLs are always valid.
    Subclasses implement intelligent URL checking."""

    def ValidLink(self,url:str,item:dict) -> bool:
        if not url.strip():
            return False
        if Utils.RemoteURL(url):
            return True
        else:
            return os.path.isfile(url)

class RemoteURLChecker (LinkValidator):
    """Check to see if the remote URL exists before reporting it to be valid.
    Subclasses can """
    
    openLocalFiles: bool # Do we open local files as well as remote ones?

    def __init__(self,openLocalFiles = False):
        self.openLocalFiles = openLocalFiles
    
    def ValidLink(self,url:str,item:dict) -> bool:
        if Utils.RemoteURL(url):
            try:
                with urllib.request.urlopen(url) as request:
                    return self.ValidateContents(url,item,request)
            except urllib.error.HTTPError as error:
                Alert.notice("Unable to open",url,"for",item)
                return False
        else:
            if not os.path.isfile(url):
                return False
            if self.openLocalFiles:
                try:
                    with open(url,"rb") as file:
                        return self.ValidateContents(url,item,file)
                except IOError as error:
                    Alert.warning(error,"when opening",url,"when processing",item)
                    return False
            else:
                return super().ValidLink(url,item)
    
    def ValidateContents(self,url:str,item:dict,contents:BinaryIO) -> bool:
        "This method should be overriden by subclasses that validate file contents."
        return True

def RemoteMp3Tags(url:str) -> dict:
    """Read the """
    def get_n_bytes(url, size):
        req = urllib.request.Request(url)
        req.headers['Range'] = 'bytes=%s-%s' % (0, size-1)
        response = urllib.request.urlopen(req)
        return response.read()

    data = get_n_bytes(url, 10)
    if data[0:3] != 'ID3':
        raise Exception('ID3 not in front of mp3 file')

    size_encoded = bytearray(data[-4:])
    size = reduce(lambda a,b: a*128+b, size_encoded, 0)

    header = BytesIO()
    # mutagen needs one full frame in order to function. Add max frame size
    data = get_n_bytes(url, size+2881) 
    header.write(data)
    header.seek(0)
    f = MP3(header)

    if f.tags and 'APIC:' in f.tags.keys():
        artwork = f.tags['APIC:'].data
        with open('image.jpg', 'wb') as img:
            img.write(artwork)

class Mp3LengthChecker (RemoteURLChecker):
    """Verify that the length of mp3 files is what we expect it to be."""
    
    warningDelta: float # Print a notice if the mp3 file length difference exceeds this
    invalidateDelta: float # Report an invalid link if the mp3 file length difference exceeds this
    def __init__(self,warningDelta: float = 1.0,invalidateDelta = 5.0):
        super().__init__(True)
        self.warningDelta = warningDelta
        self.invalidateDelta = invalidateDelta

    def ValidateContents(self,url:str,item:dict,contents:BinaryIO) -> bool:
        parsed = urlparse(url)
        if not parsed.path.lower().endswith(".mp3"):
            return True
        
        try:
            contents.seek(0)
            data = contents
        except IOError:
            data = BytesIO()
            data.write(contents.read())
            data.seek(0)

        audio = MP3(data)
        length = audio.info.length
        expectedLengthStr = item.get("duration","0")
        expectedLength = Utils.StrToTimeDelta(expectedLengthStr).total_seconds()
        diff = abs(length - expectedLength)
        lengthStr = Utils.TimeDeltaToStr(timedelta(seconds=length))
        # Alert.extra(url,"actual",lengthStr,"expected",expectedLengthStr)
        if diff >= self.invalidateDelta:
            Alert.warning(item,"indicates a duration of",expectedLengthStr,"but its mp3 file has duration",lengthStr,"This invalidates",url)
            return False
        elif diff >= self.warningDelta:
            Alert.caution(item,"indicates a duration of",expectedLengthStr,"but its mp3 file at",url,"has duration",lengthStr)
        return True

remoteKey = { # Specify the dictionary key indicating the remote URL for each item type
    ItemType.SESSION: "remoteMp3Url",
    ItemType.EXCERPT: "",
    ItemType.REFRENCE: "remoteUrl"
}

class Linker:
    """For a given type of item (session,excerpt,reference), determine which mirror it should link to.
    """
    itemType: ItemType # The type of item we are linking to
    validator: LinkValidator

    def __init__(self,itemType: ItemType,validator: LinkValidator):
        self.itemType = itemType
        self.validator = validator
    
    def _UncheckedMirrors(self,item: dict) -> list[str]:
        """Return a list of the mirrors that we haven't yet checked for item."""
        currentMirror = item.get("mirror","")
        midSearch = currentMirror.endswith("*")
        if currentMirror and not midSearch:
            return [] # If the item specifies a mirror, no need to search further

        mirrorList = getattr(gOptions,self.itemType)
        if midSearch:
            return mirrorList[mirrorList.index(currentMirror.rstrip("*")):]
        else:
            return mirrorList

    def Filename(self,item: dict) -> str:
        "Return the file name for a given item."
        if self.itemType == ItemType.EXCERPT:
            return Utils.PosixJoin(item["event"],Utils.ItemCode(item) + ".mp3")
        elif self.itemType == ItemType.SESSION:
            return Utils.PosixJoin(item["event"],item["filename"])
        else:
            return item["filename"]

    def URL(self,item: dict,mirror: str = "") -> str:
        """Return the URL of this item in a given mirror; if mirror is None, use item["mirror"]"""
        if not mirror:
            mirror = item.get("mirror","")
        if not mirror:
            return ""
        
        if mirror == "remote":
            url = item.get(remoteKey[self.itemType],"")
            if Utils.RemoteURL(url):
                return url
            else: 
                return Utils.PosixJoin(gOptions.prototypeDir,"indexes",url)
                # If the remote link specifies a local file, the path will be relative to prototypeDir/indexes.
                # This occurs only with references.

        return urljoin(gOptions.mirror[self.itemType][mirror],self.Filename(item))

    def LinkItem(self,item: dict) -> str:
        """Search the available mirrors and set item["mirror"] to the name of the first valid mirror.
        If there is no valid mirror, set it to "".
        Returns the name of the mirror or ""."""

        currentMirror = item.get("mirror","")
        if currentMirror and not currentMirror.endswith("*"):
            return item["mirror"]

        for mirror in self._UncheckedMirrors(item):
            if self.validator.ValidLink(self.URL(item,mirror),item):
                item["mirror"] = mirror
                return mirror
        
        item["mirror"] = ""
        return ""
    
    def LocalItemNeeded(self,item: dict) -> bool:
        """Check through the available mirrors until we either reach a valid item or the local mirror.
        If the latter, report true and stop the search so that a local item can be acquired."""
        
        for mirror in self._UncheckedMirrors(item):
            if self.validator.ValidLink(self.URL(item,mirror),item):
                item["mirror"] = mirror
                return False
            elif mirror == "local":
                item["mirror"] = "local*"
                return True
        
        return False


def URL(item:dict,directoryDepth:int = 0,mirror:str = "") -> str:
    """Auto-detect the type of this item and return its URL.
    directoryDepth: depth of the html file we are writing relative to the home directory."""

    baseUrl = gLinker[AutoType(item)].URL(item,mirror)

    if not Utils.RemoteURL(baseUrl):
        return ("../" * directoryDepth) + baseUrl
    return baseUrl

def LocalItemNeeded(item:dict) -> bool:
    "Auto-detect the type of this item and return whether a local copy is needed"
    return gLinker[AutoType(item)].LocalItemNeeded(item)


def LinkItems() -> None:
    """Find a valid mirror for all items that haven't already been linked to."""

    with ThreadPoolExecutor(max_workers=1) as pool:
        for itemType,items in gItemLists.items():
            for item in Utils.Contents(items):
                if item.get("fileNumber",1) == 0:
                    continue # Don't link session excerpts

                pool.submit(lambda itemType,item: gLinker[itemType].LinkItem(item),itemType,item)
    
    """for itemType,items in gItemLists.items():
        for item in Utils.Contents(items):
            if item.get("fileNumber",1) == 0:
                continue # Don't link session excerpts

            gLinker[itemType].LinkItem(item)"""

    for itemType,items in gItemLists.items():
        unlinked = []
        mirrorCount = Counter()
        for item in Utils.Contents(items):
            if item.get("fileNumber",1) == 0:
                continue # Don't count session excerpts
            if item.get("mirror",""):
                mirrorCount[item["mirror"]] += 1
            else:
                unlinked.append(item)
        
        if unlinked:
            Alert.warning(itemType + ":",len(unlinked),"unlinked items:",*unlinked)
                          
        Alert.info(itemType + " mirror links:",dict(mirrorCount))

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument("--mirror",type=str,action="append",default=[],help="Specify the URL of a mirror. Format mirror:URL")
    parser.add_argument("--sessionMp3",type=str,default="remote,local",help="Session audio file priority mirror list; default: remote,local")
    parser.add_argument("--excerptMp3",type=str,default="1",help="Excerpt audio file priority mirror list; default: 1 - first mirror specifed")
    parser.add_argument("--reference",type=str,default="remote,local",help="Reference file priority mirror list; default: remote,local")
    parser.add_argument("--sessionMp3Dir",type=str,default="audio/sessions",help="Read session mp3 files from this directory; Default: audio/sessions")
    parser.add_argument("--excerptMp3Dir",type=str,default="audio/excerpts",help="Write excerpt mp3 files from this directory; Default: audio/excerpts")
    parser.add_argument("--referenceDir",type=str,default="references",help="Read session mp3 files from this directory; Default: references")

def ParseArguments() -> None:
    """Set up gOptions.mirror[itemType][mirrorName] as the URL to find items in a named mirror."""

    itemDirs = { # Specifies the directory for each item type
        ItemType.SESSION: gOptions.sessionMp3Dir,
        ItemType.EXCERPT: gOptions.excerptMp3Dir,
        ItemType.REFRENCE: gOptions.referenceDir
    }
    
    mirrorDict = {"local":"./"}
    for mirrorStr in gOptions.mirror:
        mirrorName,url = mirrorStr.split(":",1)
        mirrorDict[mirrorName] = url

    gOptions.mirror = {}
    for itemType,itemDir in itemDirs.items():
        gOptions.mirror[itemType] = {
            mirrorName:Utils.DirectoryURL(urljoin(Utils.DirectoryURL(url),itemDir)) for mirrorName,url in mirrorDict.items()
        }

    def CheckMirrorName(itemType:str,mirrorName: str) -> str:
        "Check if mirrorName is a valid mirror reference and turn numbers into names."
        try:
            mirrorName = list(gOptions.mirror[itemType])[int(mirrorName)]
        except ValueError:
            pass

        if mirrorName not in gOptions.mirror[itemType] and mirrorName != "remote":
            Alert.error(repr(mirrorName),"is not a valid mirror name.")
        return mirrorName

    for itemType in ItemType:
        mirrorList = getattr(gOptions,itemType).split(",")
        mirrorList = [CheckMirrorName(itemType,m) for m in mirrorList]
        setattr(gOptions,itemType,mirrorList)

    if "remote" in gOptions.excerptMp3:
        Alert.error("remote cannot be specified as a mirror for excerpts.")


gLinker:dict[ItemType,Linker] = {}

def Initialize() -> None:
    """Configure the linker object."""
    global gLinker

    gLinker = {itemType:Linker(itemType,LinkValidator()) for itemType in ItemType}
        # For now, use the simplest possible Linker object
    #gLinker[ItemType.REFRENCE].validator = Mp3LengthChecker()

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy
gItemLists:dict[ItemType:dict|list] = {}

def main() -> None:
    global gItemLists
    gItemLists = {
        ItemType.EXCERPT: gDatabase["excerpts"],
        ItemType.SESSION: gDatabase["sessions"],
        ItemType.REFRENCE: gDatabase["reference"]
    }
    
    LinkItems()