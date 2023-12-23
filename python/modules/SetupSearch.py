"""Create assets/SearchDatabase.json for easily searching the excerpts.
"""

from __future__ import annotations

import os, json
import Utils, Alert, Link
from typing import Iterable

def OptimizedExcerpts() -> list[dict]:
    returnValue = []
    for x in gDatabase["excerpts"][0:10]:
        xDict = {"html":x["body"]}
        returnValue.append(xDict)
    return returnValue

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    pass

def ParseArguments() -> None:
    pass
    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:
    optimizedDB = {
        "excerpts":OptimizedExcerpts()
    }

    with open(Utils.PosixJoin(gOptions.prototypeDir,"assets","SearchDatabase.json"), 'w', encoding='utf-8') as file:
        json.dump(optimizedDB, file, ensure_ascii=False, indent=2)