"""Move unlinked files into xxxNoUpload directories in preparation for uploading the website.
"""

from __future__ import annotations

import os
import Utils, Alert, Link
from typing import Iterable

def SwitchedMoveFile(locationTrue: str,locationFalse: str,switch: bool) -> bool:
    """Move a file to either locationTrue or locationFalse depending on the value of switch.
    Raise FileExistsError if both locations are occupied.
    Return True if the file was moved."""
    if switch:
        moveTo,moveFrom = locationTrue,locationFalse
    else:
        moveTo,moveFrom = locationFalse,locationTrue
    
    if os.path.isfile(moveFrom):
        if os.path.isfile(moveTo):
            raise FileExistsError(f"Cannot move {moveFrom} to overwrite {moveTo}.")
        os.makedirs(Utils.PosixSplit(moveTo)[0],exist_ok=True)
        os.rename(moveFrom,moveTo)
        return True
    return False

def MoveItemsIfNeeded(items: Iterable[dict]) -> (int,int):
    """Move items to/from the xxxNoUpload directories as needed. 
    Return a tuple of counts: (moved to regular location,moved to NoUpload directory)."""
    movedToDir = movedToNoUpload = 0
    for item in items:
        localPath = Link.URL(item,mirror="local")
        noUploadPath = Link.NoUploadPath(item)
        mirror = item.get("mirror","")
        if not localPath or not noUploadPath or not mirror:
            continue
        
        fileNeeded = mirror in ("local",gOptions.uploadMirror)
        if SwitchedMoveFile(localPath,noUploadPath,fileNeeded):
            if fileNeeded:
                movedToDir += 1
            else:
                movedToNoUpload += 1
    
    return movedToDir,movedToNoUpload

def MoveItemsIn(items: list[dict]|dict[dict],name: str) -> None:
    
    movedToDir,movedToNoUpload = MoveItemsIfNeeded(Utils.Contents(items))
    if movedToDir or movedToNoUpload:
        Alert.extra(f"Moved {movedToDir} {name}(s) to usual directory; moved {movedToNoUpload} {name}(s) to NoUpload directory.")

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    pass

def ParseArguments() -> None:
    pass
    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main() -> None:
    MoveItemsIn(gDatabase["audioSource"],"session mp3")
    MoveItemsIn(gDatabase["excerpts"],"excerpt mp3")
    MoveItemsIn(gDatabase["reference"],"reference")
    