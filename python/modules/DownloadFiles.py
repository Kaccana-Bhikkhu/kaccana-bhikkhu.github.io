"""Check if a local file is needed for each session, excerpt, and reference.
If so, try to download a valid file from the specified mirrors. 
"""

from __future__ import annotations

import os
import Utils, Alert, Link
from concurrent.futures import ThreadPoolExecutor

def DownloadItems(itemList: list[dict]) -> int:
    """Ascertain whether any items require a local file. If so, try to download them from available mirrors."""
    downloadCount = 0

    def DownloadItem(item: dict) -> None:
        nonlocal downloadCount
        if Link.DownloadItem(item):
                downloadCount += 1

    multithreading = True
    with ThreadPoolExecutor() if multithreading else Utils.MockThreadPoolExecutor() as pool:
        for item in Utils.Contents(itemList):
            pool.submit(DownloadItem,item)
    
    return downloadCount

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
    downloadCount = DownloadItems(gDatabase["audioSource"])
    Alert.info("Downloaded",downloadCount,"audio source (session) mp3(s)")

    downloadCount = DownloadItems(gDatabase["excerpts"])
    Alert.info("Downloaded",downloadCount,"excerpt mp3(s)")

    downloadCount = DownloadItems(gDatabase["reference"])
    Alert.info("Downloaded",downloadCount,"reference(s)")