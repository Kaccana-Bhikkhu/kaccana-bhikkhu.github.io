"""Check links in the documentation and events directories using BeautifulSoup.
"""

from __future__ import annotations

import os, bisect
from functools import lru_cache
import Database
import Utils, Database, Alert
from typing import NamedTuple, Iterable

@lru_cache(maxsize=None)
def AllKeyTopicTags() -> set[str]:
    """Return the set of tags included under any key topic."""

    keyTopicTags = set()
    for subtopic in gDatabase["subtopic"].values():
        keyTopicTags.add(subtopic["tag"])
        keyTopicTags.update(subtopic["subtags"])
    
    return keyTopicTags

@lru_cache(maxsize=None)
def SignificantSubtagsWithoutFTags() -> set[str]:
    """Return the set of tags that: 
    1) Are included under a subtopic but are not the subtopic itself.
    2) The subtopic is not marked as reviewed
    3) Have no featured excerpts.
    4) Have more excerpts than the significance threshold.
    5) Have more than signficantSubtagPercent of the total excerpts in their subtag"""

    tags = set()
    for subtopic in gDatabase["subtopic"].values():
        if subtopic["reviewed"]:
            continue
        for tagName in Database.SubtagIterator(subtopic):
            tag = gDatabase["tag"][tagName]
            excerptCount = tag.get("excerptCount",0)
            if not tag.get("fTagCount",0) and \
                    excerptCount >= gOptions.significantTagThreshold and \
                    excerptCount >= gOptions.signficantSubtagPercent * subtopic["excerptCount"] // 100:
                tags.add(tagName)
            
    return tags

def OptimalFTagCount(tagOrSubtopic: dict[str],database:dict[str] = {}) -> tuple[int,int,int]:
    """For a given tag or subtopic, returns the tuple (minFTags,maxFTags,difference).
    tagOrSubtopic: a tag or subtopic dict
    database: the under-construction database if gDatabase isn't yet initialized.
    minFTags,maxFTags: heuristic estimates of the optimal number of featured excerpts.
    difference: the difference between the actual number of fTags and these limits;
        0 if minFTags <= fTagCount <= maxFTags"""

    if not database:
        database = gDatabase
    subtopic = "subtags" in tagOrSubtopic

    # Start with an estimate based on the number of excerpts for this tag/subtopic
    if subtopic:
        minFTags = bisect.bisect_right((6,18,54,144,384,1024),tagOrSubtopic["excerptCount"])
    else:
        minFTags = bisect.bisect_right((10,25,60,150,400,1065),tagOrSubtopic["excerptCount"])
    maxFTags = bisect.bisect_right((4,8,16,32,80,200,500,1250),tagOrSubtopic["excerptCount"])

    # Then add fTags to subtopics with many significant subtags
    significantTags = 0
    insignificantTags = -1
    for subtag in Database.SubtagIterator(tagOrSubtopic):
        if database["tag"][subtag].get("excerptCount",0) >= gOptions.significantTagThreshold:
            significantTags += 1
        else:
            insignificantTags += 1

    # oldMin,oldMax = minFTags,maxFTags
    minFTags += (2*significantTags + insignificantTags) // 10
    maxFTags += (4*significantTags + 2*insignificantTags) // 10

    #if oldMax != maxFTags:
    #    Alert.extra(tagOrSubtopic,"now needs",minFTags,"-",maxFTags,"fTags. Subtags:",significantTags,"significant;",insignificantTags,"insignificant.")

    difference = min(tagOrSubtopic["fTagCount"] - minFTags,0) or max(tagOrSubtopic["fTagCount"] - maxFTags,0)

    return minFTags,maxFTags,difference

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--significantTagThreshold',type=int,default=12,help='Tags count as significant if they have this many excerpts.')
    parser.add_argument('--signficantSubtagPercent',type=int,default=25,help="Subtags count as significant if they account for more than this percentage of their subtopics' excerpts.")

def ParseArguments() -> None:
    pass    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:
    Alert.extra("Ran this module.")
    
