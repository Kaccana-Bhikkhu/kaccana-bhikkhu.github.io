"""Add a "mirror" field to each session, excerpt and reference indicating which hyperlink the item should use.

"""

from __future__ import annotations

import re, os, itertools
import Utils, Render, Alert, Html, Filter
from urllib.parse import urlparse,urljoin
from typing import Tuple, Type, Callable, Iterable
from enum import Enum

class StrEnum(str,Enum):
    pass

class ItemType(StrEnum): # The kinds of items we will link to
    SESSION = "sessionMp3"
    EXCERPT = "excerptMp3"
    REFRENCE = "reference"

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
    
    def Filename(self,item: dict) -> str:
        "Return the file name for a given item."
        if self.itemType == ItemType.EXCERPT:
            return Utils.PosixJoin(item["event"],Utils.ItemCode(item) + ".mp3")
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

        mirrorList = getattr(gOptions,self.itemType)

        for mirror in mirrorList:
            if self.validator.ValidLink(self.URL(item,mirror),item):
                item["mirror"] = mirror
                return mirror
        
        item["mirror"] = ""
        return ""


def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument("--mirror",type=str,action="append",default=[],help="Specify the URL of a mirror. Format mirror:URL")
    parser.add_argument("--sessionMp3",type=str,default="remote,local",help="Session audio file priority mirror list; default: remote,local")
    parser.add_argument("--excerptMp3",type=str,default="1",help="Excerpt audio file priority mirror list; default: 1 - first mirror specifed")
    parser.add_argument("--reference",type=str,default="remote,local",help="Reference file priority mirror list; default: remote,local")
    parser.add_argument("--sessionMp3Dir",type=str,default="audio/sessions",help="Read session mp3 files from this directory; Default: audio/sessions")
    parser.add_argument("--excerptMp3Dir",type=str,default="audio/excerpts",help="Write excerpt mp3 files from this directory; Default: audio/excerpts")
    parser.add_argument("--referenceDir",type=str,default="reference",help="Read session mp3 files from this directory; Default: references")

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

    print(gOptions)

linker:dict[ItemType,Linker] = {}

def Initialize() -> None:
    """Configure the linker object."""
    global linker

    linker = {itemType:Linker(itemType,LinkValidator()) for itemType in ItemType}
        # For now, use the simplest possible Linker object

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main() -> None:
    itemLists = {
        #ItemType.EXCERPT: gDatabase["excerpts"],
        #ItemType.SESSION: gDatabase["sessions"],
        ItemType.REFRENCE: gDatabase["reference"]
    }
    for itemType,items in itemLists.items():
        for item in Utils.Contents(items):
            if not linker[itemType].LinkItem(item):
                Alert.warning("Unable to link item",item)