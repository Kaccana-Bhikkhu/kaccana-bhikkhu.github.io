"""Main program to create the Ajahn Pasanno Question and Answer Archive website
"""

import argparse
import importlib
import os, sys
import json

scriptDir,_ = os.path.split(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(scriptDir,'python')) # Look for modules in the ./python in the same directory as QAarchive.py

def PrintModuleSeparator(moduleName:str):
    if clOptions.verbose >= 0:
            print(f"{'-'*10} {moduleName} {'-'*(25 - len(moduleName))}")

# The list of code modules/ops to implement
moduleList = ['ParseCSV','OptimizeDatabase','SplitMp3','Prototype']
modules = {modName:importlib.import_module(modName) for modName in moduleList}

parser = argparse.ArgumentParser(description="""Create the Ajahn Pasanno Question and Answer Archive website from mp3 files and the 
AP QA archive main Google Sheet.""")

parser.add_argument('ops',type=str,help="""A comma-separated list of operations to perform. No spaces allowed. Available operations:
ParseCSV - convert the csv files downloaded from the Google Sheet to Database.json.
SplitMp3 - split mp3 files into individual questions based on the times in Database.json.
Prototype - create various files to illustrate how Database.json should be interpreted.
All - run all the above modules in sequence.
""")

parser.add_argument('--homeDir',type=str,default='.',help='All other pathnames are relative to this directory; Default: ./')
parser.add_argument('--spreadsheetDatabase',type=str,default='prototype/SpreadsheetDatabase.json',help='Database created from the csv files; keys match spreadsheet headings; Default: prototype/SpreadsheetDatabase.json')
parser.add_argument('--optimizedDatabase',type=str,default='Database.json',help='Database optimised for Javascript web code; Default: Database.json')
parser.add_argument('--sessionMp3',type=str,default='remote',help='Session audio file link location; default: remote - use external Mp3 URL from session database')
parser.add_argument('--questionMp3',type=str,default='remote',help='Question audio file link location; default: remote - use remoteQuestionMp3URL')
parser.add_argument('--remoteQuestionMp3URL',type=str,default='http://storage.googleapis.com/apqa_archive/audio/questions/',help='remote URL for questions; default: storage.googleapis.com/apqa_archive/audio/questions/')

for mod in modules:
    modules[mod].AddArguments(parser)

parser.add_argument('--verbose','-v',default=0,action='count',help='increase verbosity')
parser.add_argument('--quiet','-q',default=0,action='count',help='decrease verbosity')

clOptions = parser.parse_args()
clOptions.verbose -= clOptions.quiet

os.chdir(clOptions.homeDir)

if clOptions.ops.strip() == 'All':
    opList = moduleList
else:
    opList = [verb.strip() for verb in clOptions.ops.split(',')]

# Check for unsuppported ops
for verb in opList:
    if verb not in moduleList:
        print("Unsupported operation "+verb)

if 'ParseCSV' in opList:
    database = {} # If we're going to execute ParseCSV, let it fill up the database
else:
    with open(clOptions.spreadsheetDatabase, 'r', encoding='utf-8') as file: # Otherwise read the database from disk
        database = json.load(file)
    
# Then run the specified operations in sequential order
for moduleName in moduleList:
    if moduleName in opList:
        PrintModuleSeparator(moduleName)
        modules[moduleName].main(clOptions,database)

if clOptions.ignoreTeacherConsent:
    print("WARNING: Teacher consent has been ignored. This should only be used for testing and debugging purposes.")
if clOptions.ignoreExcludes:
    print("WARNING: Session/question exclusion flags have been ignored. This should only be used for testing and debugging purposes.")
