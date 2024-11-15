"""A template for creating new modules.
"""

from __future__ import annotations

import os, shutil
from typing import NamedTuple, Iterable
import Utils, Alert
import ReviewDatabase, Database, Filter, Link

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    # parser.add_argument('--option',**Utils.STORE_TRUE,help='This is an option.')
    parser.add_argument('--exportPath',type=str,default="../exportedAudio",help="Directory to export audio to.")

def ParseArguments() -> None:
    pass    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:
    os.makedirs(gOptions.exportPath,exist_ok=True)
    with open(Utils.PosixJoin(gOptions.exportPath,"Catalog.tsv"),mode="w",encoding="utf-8") as catalog:
        firstCluster = True
        for subtopicOrTag in Database.SubtopicsAndTags():
            summary = ReviewDatabase.FeaturedExcerptSummary(subtopicOrTag["tag"],printHeading=firstCluster,printFTag=True)
            if summary:
                print(summary,file=catalog)
                print(file=catalog)
            firstCluster = False

            isSubtopic = "topicCode" in subtopicOrTag
            if isSubtopic:
                tags = [subtopicOrTag["tag"]] + list(subtopicOrTag["subtags"])
            else:
                tags = [subtopicOrTag["tag"]]
            featuredExcerpts = Filter.FTag(tags)(gDatabase["excerpts"])
            featuredExcerpts = sorted(featuredExcerpts,key=lambda x: Database.FTagOrder(x,tags))

            if not featuredExcerpts:
                continue
            
            path = Utils.PosixJoin(gOptions.exportPath,"subtopics" if isSubtopic else "tags",Utils.slugify(subtopicOrTag["tag"]))
            os.makedirs(path,exist_ok=True)
            for excerpt in featuredExcerpts:
                audioFile = Link.LocalFile(excerpt)
                if audioFile:
                    shutil.copy2(audioFile,Utils.PosixJoin(path,Utils.PosixSplit(audioFile)[1]))
                else:
                    Alert.warning("Could not copy audio file for",excerpt)
