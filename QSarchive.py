"""Main program to create the Ajahn Pasanno Question and Story Archive website
"""

from __future__ import annotations

import argparse, shlex
import importlib
import os, sys
import json
from typing import Tuple

scriptDir,_ = os.path.split(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(scriptDir,'python/modules')) # Look for modules in these subdirectories of the directory containing QAarchive.py
sys.path.append(os.path.join(scriptDir,'python/utils'))

import Utils, Alert, Filter
Alert.ObjectPrinter = Utils.ItemRepr

def PrintModuleSeparator(moduleName:str) -> None:
    if moduleName:
        Alert.structure(f"{'-'*10} {moduleName} {'-'*(25 - len(moduleName))}")
    else:
        Alert.structure('-'*37)

def ReadJobOptions(jobName: str) -> list[str]:
    "Read a list of job options from the .vscode/launch.json"
    
    with open(".vscode/launch.json", "r") as file:
        fixed_json = ''.join(line for line in file if not line.lstrip().startswith('//'))
        config = json.loads(fixed_json)
    
    for job in config["configurations"]:
        if job["name"] == jobName:
            return job["args"]
    
    allJobs = [job["name"] for job in config["configurations"]]
    if jobName:
        print(f"{repr(jobName)} does not appear in .vscode/launch.json.")
    print(f"Available jobs: {allJobs}")
    quit()

def ApplyDefaults(argsFileName: str,parser: argparse.ArgumentParser) -> None:
    "Read the specified .args file and apply these as default values to parser."
    with open(argsFileName,"r",encoding="utf-8") as argsFile:
        argumentStrings = []
        for line in argsFile:
            line = line.strip()
            if line and not line.startswith("//"):
                argumentStrings.append(line)

        commandArgs = ["DummyOp"] + shlex.split(" ".join(argumentStrings))
        defaultArgs = parser.parse_args(commandArgs)
        parser.set_defaults(**vars(defaultArgs))

def LoadDatabaseAndAddMissingOps(opSet: set(str)) -> Tuple[dict,set(str)]:
    "Scan the list of specified ops to see if we can load a database to save time. Add any ops needed to support those specified."

    newDB = {}
    opSet = set(opSet) # Clone opSet

    if 'DownloadCSV' in opSet:
        if len(opSet) > 1: # If we do anything other than DownloadCSV, we need to parse the newly-downloaded files
            opSet.add('ParseCSV')
        else:
            return newDB,opSet
    
    requireSpreadsheetDB = {'SplitMp3','Render'}
    requireRenderedDB = {'Document','Prototype','TagMp3'}

    if opSet.intersection(requireRenderedDB):
        if 'ParseCSV' not in opSet and not opSet.intersection(requireSpreadsheetDB):
            try:
                with open(clOptions.renderedDatabase, 'r', encoding='utf-8') as file: # Otherwise read the database from disk
                    newDB = json.load(file)
                    return newDB,opSet
            except OSError:
                pass
        opSet.add('Render')
    
    if 'ParseCSV' not in opSet and opSet.intersection(requireSpreadsheetDB):
        try:
            with open(clOptions.spreadsheetDatabase, 'r', encoding='utf-8') as file: # Otherwise read the database from disk
                newDB = json.load(file)
                return newDB,opSet
        except OSError:
            opSet.add('ParseCSV')
    
    return newDB,opSet

# The list of code modules/ops to implement
moduleList = ['DownloadCSV','ParseCSV','SplitMp3','Render','Document','Prototype','TagMp3']

modules = {modName:importlib.import_module(modName) for modName in moduleList}

parser = argparse.ArgumentParser(description="""Create the Ajahn Pasanno Question and Story Archive website from mp3 files and the 
AP QA archive main Google Sheet.""")

parser.add_argument('ops',type=str,help="""A comma-separated list of operations to perform. No spaces allowed. Available operations:
DownloadCSV - download csv files from the Google Sheet.
ParseCSV - convert the csv files downloaded from the Google Sheet to SpreadsheetDatabase.json.
SplitMp3 - split mp3 files into individual excerpts based on the times in SpreadsheetDatabase.json.
Render - use pryatemp and markdown to convert excerpts into html and saves to RenderedDatabase.json.
Document - create the .md files in documentation/about from documentation/aboutSources.
Prototype - create html files for all menus and excerpts.
TagMp3 - update the ID3 tags on excerpt mp3 files.
All - run all the above modules in sequence.
""")

parser.add_argument('--homeDir',type=str,default='.',help='All other pathnames are relative to this directory; Default: ./')
parser.add_argument('--defaults',type=str,default='python/config/Default.args,python/config/LocalDefault.args',help='A comma-separated list of .args default argument files; see python/config/Default.args')
parser.add_argument('--events',type=str,default='All',help='A comma-separated list of event codes to process; Default: All')
parser.add_argument('--spreadsheetDatabase',type=str,default='prototype/SpreadsheetDatabase.json',help='Database created from the csv files; keys match spreadsheet headings; Default: prototype/SpreadsheetDatabase.json')
parser.add_argument('--optimizedDatabase',type=str,default='Database.json',help='Database optimised for Javascript web code; Default: Database.json')
parser.add_argument('--sessionMp3',type=str,default='remote',help='Session audio file link location; default: remote - use external Mp3 URL from session database')
parser.add_argument('--excerptMp3',type=str,default='remote',help='Excerpt audio file link location; default: remote - use remoteExcerptMp3URL')
parser.add_argument('--remoteExcerptMp3URL',type=str, help='remote URL for excerpts')

for mod in modules.values():
    mod.AddArguments(parser)

parser.add_argument('--verbose','-v',default=0,action='count',help='increase verbosity')
parser.add_argument('--quiet','-q',default=0,action='count',help='decrease verbosity')

if sys.argv[1] == "Job" or sys.argv[1] == "Jobs": # If ops == "Job", 
    jobOptionsList = ReadJobOptions(sys.argv[2] if len(sys.argv) >= 3 else None)
    argList = jobOptionsList + sys.argv[3:]
    Alert.essential('python',sys.argv[0]," ".join(argList))
else:
    argList = sys.argv[1:]
PrintModuleSeparator("")

## STEP 1: Parse the command line argument list to set the home directory
baseOptions = parser.parse_args(argList)
if not os.path.exists(baseOptions.homeDir):
    os.makedirs(baseOptions.homeDir)
os.chdir(baseOptions.homeDir)

Alert.verbosity = baseOptions.verbose - baseOptions.quiet
if baseOptions.homeDir != '.':
    Alert.info("Home directory:",baseOptions.homeDir)

## STEP 2: Configure parser with default options read from the .args files
parsedFiles = []
errorFiles = []
for argsFile in baseOptions.defaults.split(","):
    try:
        ApplyDefaults(argsFile,parser)
        parsedFiles.append(argsFile)
    except OSError:
        errorFiles.append(argsFile)
if parsedFiles:
    Alert.structure("Read default values from:",", ".join(parsedFiles))
if errorFiles:
    Alert.structure("Could not read:",", ".join(parsedFiles))

## STEP 3: Parse the command line again to override arguments specified by the .args files
clOptions = parser.parse_args(argList)
clOptions.verbose -= clOptions.quiet
Alert.verbosity = clOptions.verbose

for mod in modules.values():
    mod.ParseArguments(clOptions)
        # Tell each module to parse its own arguments
    mod.gOptions = clOptions
        # And let each module access all arguments
Utils.gOptions = clOptions
if Alert.error.count:
    print("Aborting due to argument parsing errors.")
    quit()

if clOptions.events != 'All':
    clOptions.events = clOptions.events.split(',')
        # clOptions.events is now either the string 'All' or a list of strings

if clOptions.ops.strip() == 'All':
    opSet = set(moduleList)
else:
    opSet = set(verb.strip() for verb in clOptions.ops.split(','))

# Check for unsuppported ops
for verb in opSet:
    if verb not in moduleList:
        Alert.warning("Unsupported operation",verb)

database, newOpSet = LoadDatabaseAndAddMissingOps(opSet)
if newOpSet != opSet:
    Alert.info(f"Will run additional module(s): {newOpSet.difference(opSet)}.")
    opSet = newOpSet

# Set up the global namespace for each module - this allows the modules to call each other out of order
for mod in modules.values():
    mod.gDatabase = database
Utils.gDatabase = database
Filter.gDatabase = database

# Then run the specified operations in sequential order
initialized = False
for moduleName in moduleList:
    if database and not initialized:
        for mod in modules.values():
            mod.Initialize() # Run each module's initialize function when the database fills up
        initialized = True

    if moduleName in opSet:
        PrintModuleSeparator(moduleName)
        modules[moduleName].main()
PrintModuleSeparator("")

if clOptions.ignoreTeacherConsent:
    Alert.warning("Teacher consent has been ignored. This should only be used for testing and debugging purposes.")
if clOptions.ignoreExcludes:
    Alert.warning("Session/excerpt exclusion flags have been ignored. This should only be used for testing and debugging purposes.")

errorCountList = []
for error in [Alert.error, Alert.warning, Alert.caution, Alert.notice]:
    countString = error.CountString()
    if countString:
        errorCountList.append(countString)

if errorCountList:
    Alert.essential("  ***** " + ", ".join(errorCountList) + " *****")
else:
    Alert.status("No errors reported.")

Alert.structure("QSarchive.py finished.")