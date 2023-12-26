"""Create assets/SearchDatabase.json for easily searching the excerpts.
"""

from __future__ import annotations

import os, json, re
import Utils, Alert, Link, Prototype, Filter
from typing import Iterable,Iterator

def Enclose(items: Iterable[str],encloseChars: str = "()") -> str:
    """Enclose the strings in items in the specified characters:
    ['foo','bar'] => '(foo)(bar)'
    If encloseChars is length one, put only one character between items."""

    startChar = joinChars = encloseChars[0]
    endChar = encloseChars[-1]
    if len(encloseChars) > 1:
        joinChars = endChar + startChar
    
    return startChar + joinChars.join(items) + endChar

blobDict = {}
inputChars:set[str] = set()
outputChars:set[str] = set()
def Blobify(items: Iterable[str]) -> Iterator[str]:
    """Convert strings to lowercase, remove diacritics, special characters, 
    remove html tags, ++Kind++ markers, and Markdown hyperlinks, and normalize whitespace.
    (Later on) remove non-searchable teacher names."""
    for item in items:
        inputChars.update(item)
        output = item.replace("‘","'").replace("’","'").replace("–","-").replace("—","-")
        output = Utils.RemoveDiacritics(item.lower())
        output = re.sub(r"\<[^>]*\>","",output) # Remove html tags
        output = re.sub(r"\[([^]]*)\]\([^)]*\)",r"\1",output) # Extract text from Markdown hyperlinks
        output = re.sub(r"\+\+[^+]*\+\+","",output) # Remove ++Kind++ tags
        output = re.sub(r"[|]"," ",output) # convert these characters to a space
        output = re.sub(r"[][#()@]^","",output) # remove these characters
        output = re.sub(r"\s+"," ",output.strip()) # normalize whitespace

        outputChars.update(output)
        if gOptions.debug:
            blobDict[item] = output
        yield output

def SearchBlobs(excerpt: dict) -> list[str]:
    """Create a list of search strings corresponding to the items in excerpt."""
    returnValue = []
    for item in Filter.AllItems(excerpt):
        bits = [
            Enclose(Blobify([item["kind"]]),"#"),
            Enclose(Blobify([item["text"]]),"^"),
            Enclose(Blobify(gDatabase["teacher"][teacher]["fullName"] for teacher in item.get("teachers",[])),"{}"),
            Enclose(Blobify(item.get("tags",[])),"[]"),
            Enclose(Blobify([excerpt["event"]]),"@")
        ]
        returnValue.append("".join(bits))
    return returnValue

def OptimizedExcerpts() -> list[dict]:
    returnValue = []
    formatter = Prototype.Formatter()
    formatter.excerptOmitSessionTags = False
    formatter.showHeading = False
    for x in gDatabase["excerpts"]:
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
        "sessionHeader": SessionHeader(),
        "blobDict":list(blobDict.values())
    }

    Alert.debug("Removed these chars:","".join(sorted(inputChars - outputChars)))
    Alert.debug("Characters remaining in blobs:","".join(sorted(outputChars)))

    with open(Utils.PosixJoin(gOptions.prototypeDir,"assets","SearchDatabase.json"), 'w', encoding='utf-8') as file:
        json.dump(optimizedDB, file, ensure_ascii=False, indent=2)