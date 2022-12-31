"""Write the optimized database file Database.json from the contents of the spreadsheet database stored passed in parameter database"""

import os, json, re, unicodedata
from Utils import StrToTimeDelta, Mp3FileName
from typing import List
from copy import deepcopy

def CamelCase(text: str) -> str: 
    """Convert a string to camel case and remove all diacritics and special characters
    "Based on https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-96.php"""
    
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    text = text.replace("#"," Number")
    #text = text.replace("."," ")
    #text = text.replace("/"," ")
    #text = text.replace("_"," ")
    
    s = re.sub(r"[(_|)?+\.\/-]", " ", text).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])

def ConvertKeysToCamelCase(db: dict) -> None:
    "Recusively convert all keys in a database to camel case strings."
    
    for key,value in db.items(): # First recursively change the case of subdictionaries
        if type(value) == dict:
            ConvertKeysToCamelCase(value)
        elif type(value) == list:
            for item in value:
                if type(item) == dict:
                    ConvertKeysToCamelCase(item)
    
    
    keys = list(k for k in db.keys() if k != CamelCase(k))
    
    for key in keys: # Then change the keys in this dictionary
        db[CamelCase(key)] = db[key]
        del db[key]

def OptimizeDatabaseKeys(db: dict) -> (dict, dict):
    """Take the input database and optimize the keys for use with Javascript.
    Keep a log of the changes.
    Returns the tuple (optimizedDatabase, substitutedKeys) """
    
    outDict = deepcopy(db)
    
    ConvertKeysToCamelCase(outDict)

    return (outDict,{})

def AddArguments(parser):
    "Add command-line arguments used by this module"
    pass
    
gOptions = None
gDatabase = None
def main(clOptions,database):
    """Write the optimized database file Database.json from the contents of the spreadsheet database stored passed in parameter database"""
    
    global gOptions
    gOptions = clOptions
    
    optimizedDatabase, changeLog = OptimizeDatabaseKeys(database)
    
    with open(gOptions.optimizedDatabase, 'w', encoding='utf-8') as file:
        json.dump(optimizedDatabase, file, ensure_ascii=False, indent=2)
    
    print("Here.")