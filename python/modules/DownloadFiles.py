"""Check if a local file is needed for each session, excerpt, and reference.
If so, try to download a valid file from the specified mirrors. 
"""

from __future__ import annotations

import os
import Utils, Alert, Link

def DownloadItems(itemList: list[dict]) -> None:
    """Ascertain whether any items require a local file. If so, try to download them from available mirrors."""
    for item in Utils.Contents(itemList):
        Link.DownloadItem(item)

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
    DownloadItems(gDatabase["reference"])