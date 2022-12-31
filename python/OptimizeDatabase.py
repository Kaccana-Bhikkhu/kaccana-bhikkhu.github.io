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

def CamelCase(text: str) -> str: 
    """Convert a string to camel case and remove all diacritics and special characters
    "Based on https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-96.php"""
    
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    text = text.replace("#"," Number")
    #text = text.replace("."," ")
    #text = text.replace("/"," ")
    #text = text.replace("_"," ")
    
    s = re.sub(r"[(_|)?+:\.\/-]", " ", text).title().replace(" ", "")
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

def TranslateKey(key: str) -> str:
    "Convert a key to its optimized value"
    return CamelCase(key)

def OptimizeDatabaseKeys(db: dict) -> (dict, dict):
    """Take the input database and optimize the keys for use with Javascript.
    Keep a list of the optimized keys in a new dictionary.
    Returns the tuple (optimizedDatabase, substitutedKeys) """
    
    """ Simplest implementation, but we can do better
    outDict = deepcopy(db)
    ConvertKeysToCamelCase(outDict)
    return (outDict,{})"""
    
    outDict = {}
    substitutions = {}
    for key, value in db.items():
        if type(value) == dict:
            value, newChanges = OptimizeDatabaseKeys(value)
            substitutions = {**substitutions, **newChanges}
        elif type(value) == list:
            newList = []
            for item in value:
                if type(item) == dict:
                    newDict, newChanges = OptimizeDatabaseKeys(item)
                    newList.append(newDict)
                    substitutions = {**substitutions, **newChanges}
                else:
                    newList.append(item)
            value = newList
        
        newKey = TranslateKey(key)
        outDict[newKey] = value
        substitutions[key] = newKey
    
    return outDict,substitutions

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--keyTranslationTable',type=str,default='prototype/OptimizedKeys.json',help='Log of OptimizeDatabase key substitutions; Default: prototype/OptimizedKeys.json')
    
gOptions = None
gDatabase = None
def main(clOptions,database):
    """Write the optimized database file Database.json from the contents of the spreadsheet database stored passed in parameter database"""
    
    global gOptions
    gOptions = clOptions
    
    optimizedDatabase, changeLog = OptimizeDatabaseKeys(database)
    
    changeLog = SortDict(changeLog)
    
    with open(gOptions.optimizedDatabase, 'w', encoding='utf-8') as file:
        json.dump(optimizedDatabase, file, ensure_ascii=False, indent=2)
    
    with open(gOptions.keyTranslationTable, 'w', encoding='utf-8') as file:
        json.dump(changeLog, file, ensure_ascii=False, indent=2)
    