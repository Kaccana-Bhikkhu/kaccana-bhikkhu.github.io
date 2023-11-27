"""Add a "mirror" field to each session, excerpt and reference indicating which hyperlink the item should use.
LinkValidator and its subclasses determine whether a given hyperlink is valid.
"""

from __future__ import annotations

import os
from functools import reduce
from datetime import timedelta
from io import BytesIO
import Utils, Alert
from urllib.parse import urljoin,urlparse,quote,urlunparse
import urllib.request, urllib.error
import shutil
from mutagen.mp3 import MP3
from typing import Tuple, Type, Callable, Iterable, BinaryIO
from enum import Enum
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import contextlib
class StrEnum(str,Enum):
    pass

class ItemType(StrEnum): # The kinds of items we will link to
    SESSION = "sessionMp3"
    EXCERPT = "excerptMp3"
    REFERENCE = "reference"

def AutoType(item:dict) -> ItemType:
    if "fileNumber" in item:
        return ItemType.EXCERPT
    elif "sessionTitle" in item:
        return ItemType.SESSION
    elif "pdfPageOffset" in item:
        return ItemType.REFERENCE
    
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
    
    def DownloadValidLink(self,url:str,item:dict,downloadLocation:str) -> bool:
        """If the link is valid, download the file to downloadLoaction.
        Return True if the link is valid and the file has been sucessfully downloaded."""

        if self.ValidLink(url,item):
            try:
                with (Utils.OpenUrlOrFile(url) as remoteFile, open(downloadLocation,"wb") as localFile):
                    shutil.copyfileobj(remoteFile, localFile)
                return True
            except (OSError,urllib.error.HTTPError) as error:
                Alert.warning("Error",error,"when trying to download",item,"from",url)
                return False
        else:
            return False


class NoValidation (LinkValidator):
    "Perform no link validation whatsoever."
    def ValidLink(self,url:str,item:dict) -> bool:
        return True

class RemoteURLChecker (LinkValidator):
    """Check to see if the remote URL exists before reporting it to be valid.
    Subclasses can override ValidateContents to implement additional checks."""
    
    openLocalFiles: bool # Do we open local files as well as remote ones?

    def __init__(self,openLocalFiles = False):
        self.openLocalFiles = openLocalFiles
    
    def ValidLink(self,url:str,item:dict) -> bool:
        if not url.strip():
            return False
        if Utils.RemoteURL(url):
            url = Utils.QuotePath(url)
            try:
                with urllib.request.urlopen(url) as request:
                    result,_ = self.ValidateContents(url,item,request)
                    return result
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
                except OSError as error:
                    Alert.warning(error,"when opening",url,"when processing",item)
                    return False
            else:
                return super().ValidLink(url,item)
    
    def ValidateContents(self,url:str,item:dict,contents:BinaryIO) -> (bool,BinaryIO):
        """This method should be overriden by subclasses that validate file contents.
        It returns a tuple (valid,contents).
        valid is True if we have determined the file contents to be valid.
        contents is a file-like object representing a potentially local copy of the file.
        This prevents us from having to download a remote file twice."""
        return True,contents

def RemoteMp3Tags(url:str) -> dict:
    """Read the id3 tags from a remote mp3 file"""
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
        super().__init__(openLocalFiles=True)
        self.warningDelta = warningDelta
        self.invalidateDelta = invalidateDelta

    def ValidateContents(self,url:str,item:dict,contents:BinaryIO) -> bool:
        parsed = urlparse(url)
        if not parsed.path.lower().endswith(".mp3"):
            return True,contents
        
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
            return False,data
        elif diff >= self.warningDelta:
            Alert.caution(item,"indicates a duration of",expectedLengthStr,"but its mp3 file at",url,"has duration",lengthStr)
        return True,data

remoteKey = { # Specify the dictionary key indicating the remote URL for each item type
    ItemType.SESSION: "remoteMp3Url",
    ItemType.EXCERPT: "",
    ItemType.REFERENCE: "remoteUrl"
}

class Linker:
    """For a given type of item (session,excerpt,reference), determine which mirror it should link to.
    """
    itemType: ItemType # The type of item we are linking to
    mirrorValidator: dict[str,LinkValidator] # The list of mirrors and the validator for each mirror

    def __init__(self,itemType: ItemType,mirrorValidator: dict[str,LinkValidator]):
        self.itemType = itemType
        self.mirrorValidator = mirrorValidator
    
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

    def FileName(self,item: dict) -> str:
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
        
        fileName = self.FileName(item)
        if fileName:
            return urljoin(gOptions.mirror[self.itemType][mirror],self.FileName(item))
        else:
            return ""

    def LinkItem(self,item: dict) -> str:
        """Search the available mirrors and set item["mirror"] to the name of the first valid mirror.
        If there is no valid mirror, set it to "".
        Returns the name of the mirror or ""."""

        currentMirror = item.get("mirror","")
        if currentMirror and not currentMirror.endswith("*"):
            return item["mirror"]

        for mirror in self._UncheckedMirrors(item):
            url = self.URL(item,mirror)
            try:
                if self.mirrorValidator[mirror].ValidLink(url,item):
                    item["mirror"] = mirror
                    return mirror
            except Exception as error:
                Alert.warning(error,"when trying to access",url,"for item",item)
        
        item["mirror"] = ""
        return ""
    
    def LocalItemNeeded(self,item: dict) -> bool:
        """Check through the available mirrors until we either reach a valid item, the local mirror, or the upload mirror.
        In the latter two cases, report true and stop the search so that a local item can be acquired."""
        
        if item.get("mirror","").endswith("*"):
            return True # Have we tried to find a local item before?
        for mirror in self._UncheckedMirrors(item):
            mirrorToCheck = mirror
            if mirror == gOptions.uploadMirror:
                mirrorToCheck = "local"
            
            if self.mirrorValidator[mirrorToCheck].ValidLink(self.URL(item,mirrorToCheck),item):
                item["mirror"] = mirror
                return False
            elif mirrorToCheck == "local":
                item["mirror"] = mirror + "*"
                return True
        
        return False

    def DownloadItem(self,item: dict) -> bool:
        """If needed, attempt to download this item from any available mirrors.
        Return True if the item was needed and has been downloaded; False otherwise."""
        fileName = self.URL(item,"local")
        if not fileName:
            return False
        if self.itemType == ItemType.REFERENCE and not fileName.lower().endswith(".pdf"):
            return False # Download only html files
        
        if self.LocalItemNeeded(item):
            tempDownloadLocation = fileName + ".download"

            remainingMirrors = self._UncheckedMirrors(item)[1:]
            localMirrors = ("local",gOptions.uploadMirror)
            for mirror in remainingMirrors:
                if mirror not in localMirrors:
                    url = self.URL(item,mirror)
                    #if self.mirrorValidator[mirror].ValidLink(url,item):
                    #    Alert.extra("Will try to download",item,"from",url,"to",tempDownloadLocation)
                    if self.mirrorValidator[mirror].DownloadValidLink(self.URL(item,mirror),item,tempDownloadLocation):
                        with contextlib.suppress(FileNotFoundError):
                            os.remove(fileName)
                        os.rename(tempDownloadLocation,fileName)
                        item["mirror"] = item["mirror"].rstrip("*")
                        Alert.extra("Downloaded",item,"to",fileName)
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

def DownloadItem(item:dict) -> bool:
    """Auto-detect the type of this item. If a local copy is needed, try to download one.
    Returns True if an item was sucessfully downloaded."""
    return gLinker[AutoType(item)].DownloadItem(item)

def LinkItems() -> None:
    """Find a valid mirror for all items that haven't already been linked to."""

    multiThread = True

    if multiThread:
        with ThreadPoolExecutor() as pool:
            for itemType,items in gItemLists.items():
                for item in Utils.Contents(items):
                    if item.get("fileNumber",1) == 0:
                        continue # Don't link session excerpts

                    pool.submit(lambda itemType,item: gLinker[itemType].LinkItem(item),itemType,item)
    else:
        for itemType,items in gItemLists.items():
            for item in Utils.Contents(items):
                if item.get("fileNumber",1) == 0:
                    continue # Don't link session excerpts

                gLinker[itemType].LinkItem(item)

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

def CheckMirrorName(itemType:str,mirrorName: str) -> str:
    "Check if mirrorName is a valid mirror reference and turn numbers into names."
    try:
        mirrorName = list(gOptions.mirror[itemType])[int(mirrorName)]
    except ValueError:
        pass
    except IndexError:
        Alert.error(mirrorName,"is beyond the number of available mirrors:",list(gOptions.mirror[itemType]))

    if mirrorName not in gOptions.mirror[itemType] and mirrorName != "remote":
        Alert.error(repr(mirrorName),"is not a valid mirror name.")
    return mirrorName

def RemoveAllExceptFirst(ioList: list,itemsToRemove: list) -> None:
    "Remove all items in itemsToRemove from ioList except the first occurence."

    index = 0
    firstItem = True
    while index < len(ioList):
        if ioList[index] in itemsToRemove:
            if firstItem:
                index += 1
                firstItem = False
            else:
                del ioList[index]
        else:
            index += 1

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument("--mirror",type=str,action="append",default=[],help="Specify the URL of a mirror. Format mirror:URL")
    parser.add_argument("--sessionMp3",type=str,default="remote,local",help="Session audio file priority mirror list; default: remote,local")
    parser.add_argument("--excerptMp3",type=str,default="1",help="Excerpt audio file priority mirror list; default: 1 - first mirror specifed")
    parser.add_argument("--reference",type=str,default="remote,local",help="Reference file priority mirror list; default: remote,local")
    parser.add_argument("--uploadMirror",type=str,default="local",help="Files will be uploaded to this mirror; default: local")

    parser.add_argument("--sessionMp3Dir",type=str,default="audio/sessions",help="Read session mp3 files from this directory; Default: audio/sessions")
    parser.add_argument("--excerptMp3Dir",type=str,default="audio/excerpts",help="Write excerpt mp3 files from this directory; Default: audio/excerpts")
    parser.add_argument("--referenceDir",type=str,default="references",help="Read session mp3 files from this directory; Default: references")

    parser.add_argument("--linkCheckLevel",type=str,action="append",default=["1"],help="Integer link check level. [ItemType]:[mirror]:LEVEL")

    """Link check levels are interpreted as follows:
        0: No link checking whatsoever (NoValidation)
        1: Check that local files exist and that remote URLs aren't blank (LinkValidator base class)
        2: Perform checks that require reading local cache files
        3: Perform checks that require reading file metadata and headers
        4: Perform checks that require reading the entire file (Mp3LengthChecker)

        Round down if a given level is not implemented for a given file type.
    """

def ParseArguments() -> None:
    """Set up gOptions.mirror[itemType][mirrorName] as the URL to find items in a named mirror."""

    itemDirs = { # Specifies the directory for each item type
        ItemType.SESSION: gOptions.sessionMp3Dir,
        ItemType.EXCERPT: gOptions.excerptMp3Dir,
        ItemType.REFERENCE: gOptions.referenceDir
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

    gOptions.uploadMirror = CheckMirrorName(ItemType.EXCERPT,gOptions.uploadMirror)

    for itemType in ItemType:
        mirrorList = getattr(gOptions,itemType).split(",")
        mirrorList = [CheckMirrorName(itemType,m) for m in mirrorList]
        RemoveAllExceptFirst(mirrorList,["local",gOptions.uploadMirror])
        setattr(gOptions,itemType,mirrorList)

    if "remote" in gOptions.excerptMp3:
        Alert.error("remote cannot be specified as a mirror for excerpts.")

    # Parse --linkCheckLevel entries to form a dict
    linkCheckLevels = copy.deepcopy(gOptions.mirror) # Copy the structure of the mirrors
    linkCheckLevels[ItemType.REFERENCE]["remote"] = 1
    linkCheckLevels[ItemType.SESSION]["remote"] = 1
    mirrorNames = set(mirrorDict)
    mirrorNames.add("remote")
    for levelCode in gOptions.linkCheckLevel:
        parts = levelCode.split(":")
        try:
            level = int(parts[-1])
        except ValueError:
            Alert.error(parts[-1],"must be an integer in --linkCheckLevel",levelCode)
        mirrors = set()
        itemTypes = set()
        for mirrorOrItemTypes in parts[0:-1]:
            for mirrorOrItemType in mirrorOrItemTypes.split(","):
                if mirrorOrItemType in mirrorNames:
                    mirrors.add(mirrorOrItemType)
                elif mirrorOrItemType in linkCheckLevels:
                    itemTypes.add(mirrorOrItemType)
                else:
                    Alert.error("Unknown mirror or item type",mirrorOrItemType,"in --linkCheckLevel",levelCode)
        for it in linkCheckLevels:
            for m in linkCheckLevels[it]:
                if (not mirrors or m in mirrors) and (not itemTypes or it in itemTypes):
                    linkCheckLevels[it][m] = level
    gOptions.linkCheckLevel = linkCheckLevels            

gLinker:dict[ItemType,Linker] = {}

def Initialize() -> None:
    """Configure the linker object."""
    global gLinker

    def ChooseLinkChecker(itemType:ItemType, level:int) -> LinkValidator:
        "Choose a Linker object for a given item type and link checking level."
        if level == 0:
            return NoValidation()
        if level <= 2:
            return LinkValidator()
        elif level == 3 or (level > 3 and itemType == ItemType.REFERENCE):
            return RemoteURLChecker()
        else:
            return Mp3LengthChecker()

        
    def MirrorValidatorDict(itemType:ItemType, mirrors:list[str]) -> dict[str,LinkValidator]:
        return {m:ChooseLinkChecker(itemType,gOptions.linkCheckLevel[itemType][m]) for m in mirrors}

    gLinker = {it:Linker(it,MirrorValidatorDict(it,mirrors)) for it,mirrors in gOptions.linkCheckLevel.items()}

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy
gItemLists:dict[ItemType:dict|list] = {}

def main() -> None:
    global gItemLists
    gItemLists = {
        ItemType.EXCERPT: gDatabase["excerpts"],
        ItemType.SESSION: gDatabase["sessions"],
        ItemType.REFERENCE: gDatabase["reference"]
    }
    
    LinkItems()