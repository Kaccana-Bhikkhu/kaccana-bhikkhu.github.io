"""Create assets/SearchDatabase.json for easily searching the excerpts.
"""

from __future__ import annotations

import os, json
import Utils, Alert, Link, Prototype, Filter
from typing import Iterable

def Enclose(items: Iterable[str],encloseChars: str = "()") -> str:
    """Enclose the strings in items in the specified characters:
    ['foo','bar'] => '(foo)(bar)'
    If encloseChars is length one, put only one character between items."""

    startChar = joinChars = encloseChars[0]
    endChar = encloseChars[-1]
    if len(encloseChars) > 1:
        joinChars = endChar + startChar
    
    return startChar + joinChars.join(items) + endChar

def SearchBlobs(excerpt: dict) -> list[str]:
    """Create a list of search strings corresponding to the items in excerpt."""
    returnValue = []
    for item in Filter.AllItems(excerpt):
        bits = [
            Enclose([item["kind"]],"#"),
            Enclose([item["text"]],"|"),
            Enclose((gDatabase["teacher"][teacher]["fullName"] for teacher in item.get("teachers",[])),"{}"),
            Enclose(item.get("tags",""),"[]"),
            Enclose([excerpt["event"]],"@")
        ]
        returnValue.append("".join(bits))
    return returnValue

def OptimizedExcerpts() -> list[dict]:
    returnValue = []
    formatter = Prototype.Formatter()
    formatter.excerptOmitSessionTags = False
    formatter.showHeading = False
    for x in gDatabase["excerpts"][0:100]:
        xDict = {"session": Utils.ItemCode(event=x["event"],session=x["sessionNumber"]),
                 "blobs": SearchBlobs(x),
                 "html": Prototype.HtmlExcerptList([x],formatter)}
        returnValue.append(xDict)
    return returnValue

def SessionHeader() -> dict[str,str]:
    "Return a dict of session headers rendered into html."
    returnValue = {}
    formatter = Prototype.Formatter()
    formatter.headingShowTags = False

    for s in gDatabase["sessions"]:
        returnValue[Utils.ItemCode(s)] = formatter.FormatSessionHeading(s,horizontalRule=False)
    
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
        "excerpts": OptimizedExcerpts(),
        "sessionHeader": SessionHeader()
    }

    with open(Utils.PosixJoin(gOptions.prototypeDir,"assets","SearchDatabase.json"), 'w', encoding='utf-8') as file:
        json.dump(optimizedDB, file, ensure_ascii=False, indent=2)