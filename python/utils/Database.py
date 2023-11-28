"""Functions for reading and writing the json databases used in QSArchive."""

import json
import SplitMp3

def LoadDatabase(filename: str) -> dict:
    """Read the database indicated by filename"""

    with open(filename, 'r', encoding='utf-8') as file: # Otherwise read the database from disk
        newDB = json.load(file)
    
    for x in newDB["excerpts"]:
        if "clips" in x:
            x["clips"] = [SplitMp3.Clip(*c) for c in x["clips"]]
    
    return newDB