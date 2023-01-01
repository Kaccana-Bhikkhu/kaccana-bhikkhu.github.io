"""Write the optimized database file Database.json from the contents of the spreadsheet database stored passed in parameter database"""

import os, json, re, unicodedata
from Utils import StrToTimeDelta, Mp3FileName
from typing import List
from copy import deepcopy

def SortDict(d: dict) -> dict:
    "Return a new dict sorted by its keys."
    keys = list(d.keys())
    keys.sort()
    return {k : d[k] for k in keys}

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--keyTranslationTable',type=str,default='prototype/OptimizedKeys.json',help='Log of OptimizeDatabase key substitutions; Default: prototype/OptimizedKeys.json')
    
gOptions = None
gDatabase = None
def main(clOptions,database):
    """Write the optimized database file Database.json from the contents of the spreadsheet database stored passed in parameter database"""
    
    global gOptions
    gOptions = clOptions
    
    # Do nothing for the time being. Owen can write his converter code here.
    
    optimizedDatabase = deepcopy(database)
        # A deep copy lets you modify optimizedDatabse in place without touching database, which will be used by subsequent modules
    
    changeLog = {}
    changeLog = SortDict(changeLog)
    
    with open(gOptions.optimizedDatabase, 'w', encoding='utf-8') as file:
        json.dump(optimizedDatabase, file, ensure_ascii=False, indent=2)
    
    with open(gOptions.keyTranslationTable, 'w', encoding='utf-8') as file:
        json.dump(changeLog, file, ensure_ascii=False, indent=2)
    