"""Maintain pages/assets/RandomExcerpts.json, which contains rendered random featured excerpts to display on the homepage.
"""

from __future__ import annotations

import os, json
import random
from typing import NamedTuple, Iterable
import Utils, Alert, Prototype, Filter, Database

def ExcerptEntry(excerpt:dict[str]) -> dict[str]:
    """Return a dictionary containing the information needed to display this excerpt on the front page."""
    
    formatter = Prototype.Formatter()
    formatter.SetHeaderlessFormat()
    html = formatter.FormatExcerpt(excerpt)

    return {
        "code": Database.ItemCode(excerpt),
        "text": excerpt["text"],
        "fTag": excerpt["fTags"][0] if excerpt["fTags"] else "",
        "html": html,
    }

def FeaturedExcerptEntries() -> list[dict[str]]:
    """Return a list of entries corresponding to featured excerpts in key topics."""

    keyTopicFilter = Filter.FTag(Database.KeyTopicTags().keys())
    return [ExcerptEntry(x) for x in keyTopicFilter(gDatabase["excerpts"])]

def RemakeRandomExcerpts(maxLength:int = 0) -> dict[str]:
    """Return a completely new random excerpt dictionary"""

    entries = FeaturedExcerptEntries()
    random.shuffle(entries)
    if maxLength:
        entries = entries[:maxLength]
    
    return {
        "excerpts": entries
    }

def WriteDatabase(newDatabase: dict[str]) -> None:
    """Write newDatabase to the random excerpt .json file"""
    with open(gOptions.randomExcerptDatabase, 'w', encoding='utf-8') as file:
        json.dump(newDatabase, file, ensure_ascii=False, indent=2)

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--randomExcerptDatabase',type=str,default="pages/assets/RandomExcerpts.json",help="Random excerpt database file path.")
    parser.add_argument('--randomExcerptCount',type=int,default=0,help="Include only this many random excerpts in the database.")
    # parser.add_argument('--option',**Utils.STORE_TRUE,help='This is an option.')

def ParseArguments() -> None:
    pass    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:
    random.seed(42)
    database = RemakeRandomExcerpts(maxLength=gOptions.randomExcerptCount)
    WriteDatabase(database)
    
