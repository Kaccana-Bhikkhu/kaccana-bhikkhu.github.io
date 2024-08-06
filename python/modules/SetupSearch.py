"""Create assets/SearchDatabase.json for easily searching the excerpts.
"""

from __future__ import annotations

import os, json, re
import Database
import Utils, Alert, Link, Prototype, Filter
import Html2 as Html
from typing import Iterable, Iterator, Callable

def Enclose(items: Iterable[str],encloseChars: str = "()") -> str:
    """Enclose the strings in items in the specified characters:
    ['foo','bar'] => '(foo)(bar)'
    If encloseChars is length one, put only one character between items."""

    startChar = joinChars = encloseChars[0]
    endChar = encloseChars[-1]
    if len(encloseChars) > 1:
        joinChars = endChar + startChar
    
    return startChar + joinChars.join(items) + endChar


def RawBlobify(item: str) -> str:
    """Convert item to lowercase, remove diacritics, special characters, 
    remove html tags, ++Kind++ markers, and Markdown hyperlinks, and normalize whitespace."""
    output = re.sub(r'[‘’"“”]',"'",item) # Convert all quotes to single quotes
    output = output.replace("–","-").replace("—","-") # Conert all dashes to hypens
    output = Utils.RemoveDiacritics(output.lower())
    output = re.sub(r"\<[^>]*\>","",output) # Remove html tags
    output = re.sub(r"\[([^]]*)\]\([^)]*\)",r"\1",output) # Extract text from Markdown hyperlinks
    output = output.replace("++","") # Remove ++ bold format markers
    output = re.sub(r"[|]"," ",output) # convert these characters to a space
    output = re.sub(r"[][#()@_*]^","",output) # remove these characters
    output = re.sub(r"\s+"," ",output.strip()) # normalize whitespace
    return output

gBlobDict = {}
gInputChars:set[str] = set()
gOutputChars:set[str] = set()
gNonSearchableTeacherRegex = None
def Blobify(items: Iterable[str]) -> Iterator[str]:
    """Convert strings to lowercase, remove diacritics, special characters, 
    remove html tags, ++ markers, and Markdown hyperlinks, and normalize whitespace.
    Also remove teacher names who haven't given search consent."""

    global gNonSearchableTeacherRegex
    if gNonSearchableTeacherRegex is None:
        nonSearchableTeachers = set()
        for teacher in gDatabase["teacher"].values(): # Add teacher names
            if teacher["searchable"]:
                continue
            nonSearchableTeachers.update(RawBlobify(teacher["fullName"]).split(" "))

        for prefix in gDatabase["prefix"]: # But discard generic titles
            nonSearchableTeachers.discard(RawBlobify(prefix))
        Alert.debug(len(nonSearchableTeachers),"non-consenting teachers:",nonSearchableTeachers)

        if nonSearchableTeachers:
            gNonSearchableTeacherRegex = Utils.RegexMatchAny(nonSearchableTeachers,literal=True)
        else:
            gNonSearchableTeacherRegex = "xyzxyz" # Matches nothing


    for item in items:
        gInputChars.update(item)
        blob = re.sub(gNonSearchableTeacherRegex,"",RawBlobify(item)) # Remove nonconsenting teachers
        blob = re.sub(r"\s+"," ",blob.strip()) # Normalize whitespace again
        gOutputChars.update(blob)
        if gOptions.debug:
            gBlobDict[item] = blob
        if blob:
            yield blob

def SearchBlobs(excerpt: dict) -> list[str]:
    """Create a list of search strings corresponding to the items in excerpt."""
    returnValue = []
    teacherDB = gDatabase["teacher"]

    def AllNames(teachers:Iterable[str]) -> Iterator[str]:
        "Yield the names of teachers; include full and attribution names if they differ"
        for t in teachers:
            yield teacherDB[t]["fullName"]
            if teacherDB[t]["attributionName"] != teacherDB[t]["fullName"]:
                yield teacherDB[t]["attributionName"]

    for item in Filter.AllItems(excerpt):
        aTags = item.get("tags",[])
        if item is excerpt:
            qTags = aTags[0:item["qTagCount"]]
            aTags = aTags[item["qTagCount"]:]
        else:
            qTags = []

        bits = [
            Enclose(Blobify([item["text"]]),"^"),
            Enclose(Blobify(AllNames(item.get("teachers",[]))),"{}"),
            Enclose(Blobify(qTags),"[]") if qTags else "",
            "//",
            Enclose(Blobify(aTags),"[]"),
            "|",
            Enclose(Blobify([re.sub("\W","",item["kind"])]),"#"),
            Enclose(Blobify([re.sub("\W","",gDatabase["kind"][item["kind"]]["category"])]),"&")
        ]
        if item is excerpt:
            bits.append(Enclose(Blobify([excerpt["event"] + f"@s{excerpt['sessionNumber']:02d}"]),"@"))
        returnValue.append("".join(bits))
    return returnValue

def OptimizedExcerpts() -> list[dict]:
    returnValue = []
    formatter = Prototype.Formatter()
    formatter.excerptOmitSessionTags = False
    formatter.showHeading = False
    formatter.headingShowTeacher = False
    for x in gDatabase["excerpts"]:
        xDict = {"session": Database.ItemCode(event=x["event"],session=x["sessionNumber"]),
                 "blobs": SearchBlobs(x),
                 "html": Prototype.HtmlExcerptList([x],formatter)}
        returnValue.append(xDict)
    return returnValue

def SessionHeader() -> dict[str,str]:
    "Return a dict of session headers rendered into html."
    returnValue = {}
    formatter = Prototype.Formatter()
    formatter.headingShowTags = False
    formatter.headingShowTeacher = False

    for s in gDatabase["sessions"]:
        returnValue[Database.ItemCode(s)] = formatter.FormatSessionHeading(s,horizontalRule=False)
    
    return returnValue

def TagBlob(tag) -> str:
    "Make a search blob from this tag."
    bits = [
        Enclose(Blobify(sorted({tag["tag"],tag["fullTag"]})),"[]"), # Use sets to remove duplicates
        Enclose(Blobify(sorted({tag["pali"],tag["fullPali"]})),"<>"),
        Enclose(Blobify(tag["alternateTranslations"] + tag["glosses"]),"^^"),
    ]
    if tag["number"]:
        bits.append("^" + tag["number"] + "^")
    return "".join(bits)

def TagBlobs() -> Iterator[dict]:
    """Return a blob for each tag, sorted alphabetically."""

    def AlphabetizeName(string: str) -> str:
        return Utils.RemoveDiacritics(string).lower()

    alphabetizedTags = [(AlphabetizeName(tag["fullTag"]),tag["tag"]) for tag in gDatabase["tag"].values() if tag["htmlFile"]]
    alphabetizedTags.sort()

    def HtmlTagDisplay(tagInfo: dict) -> str:
        bits = [
            Prototype.DrilldownIconLink(tagInfo['tag'],iconWidth = 14),
            f"[{Prototype.HtmlTagLink(tagInfo['tag'],fullTag = True)}]"
        ]
        if tagInfo["fullPali"] and tagInfo["fullPali"] != tagInfo["fullTag"]:
            bits.append(f"({tagInfo['fullPali']})")
        if tagInfo.get("excerptCount",0):
            bits.append(f"({tagInfo['excerptCount']})")
        return " ".join(bits)

    for _,tag in alphabetizedTags:
        yield {
            "blobs": [TagBlob(gDatabase["tag"][tag])],
            "html": HtmlTagDisplay(gDatabase["tag"][tag])
        } 

def AddSearch(searchList: dict[str,dict],code: str,name: str,blobsAndHtml: Iterator[dict],wrapper:Html.Wrapper = Html.Tag("p"),separator:str = "",plural:str = "s",itemsPerPage = 5) -> None:
    """Add the search (tags, teachers, etc.) to searchList.
    code: a one-letter code to identify the search.
    name: the name of the search.
    blobsAndHtml: an iterator that yields a dict for each search item.
    separator: the html code to separate each displayed search result.
    plural: the plural name of the search. 's' means just add s.
    itemsPerPage: the number of items to show per search display page."""

    searchList[code] = {
        "code": code,
        "name": name,
        "plural": name + "s" if plural == "s" else plural,
        "prefix": wrapper.prefix,
        "suffix": wrapper.suffix,
        "separator": separator,
        "items": [b for b in blobsAndHtml],
        "itemsPerPage": itemsPerPage
    }

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
    optimizedDB = {"searches": {}}

    AddSearch(optimizedDB["searches"],"x","excerpt",OptimizedExcerpts(),wrapper = Html.Wrapper(),separator="<hr>",itemsPerPage=100)
    optimizedDB["searches"]["x"]["sessionHeader"] = SessionHeader()
    AddSearch(optimizedDB["searches"],"g","tag",TagBlobs(),itemsPerPage=100)

    optimizedDB["blobDict"] = list(gBlobDict.values())

    Alert.debug("Removed these chars:","".join(sorted(gInputChars - gOutputChars)))
    Alert.debug("Characters remaining in blobs:","".join(sorted(gOutputChars)))

    with open(Utils.PosixJoin(gOptions.prototypeDir,"assets","SearchDatabase.json"), 'w', encoding='utf-8') as file:
        json.dump(optimizedDB, file, ensure_ascii=False, indent=2)