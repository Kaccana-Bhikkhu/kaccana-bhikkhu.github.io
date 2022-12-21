"""Main program to create the Ajahn Pasanno Question and Answer Archive website
"""

import argparse
import importlib
import os, sys

scriptDir,_ = os.path.split(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(scriptDir,'python')) # Look for modules in the ./python in the same directory as QAarchive.py

# The list of code modules/ops to implement
moduleList = ['ParseCSV','SplitMp3','Prototype']
modules = {modName:importlib.import_module(modName) for modName in moduleList}

parser = argparse.ArgumentParser(description="""Create the Ajahn Pasanno Question and Answer Archive website from mp3 files and the 
AP QA archive main Google Sheet.
""")

parser.add_argument('ops',type=str,help="""A comma-separated list of operations to perform. No spaces allowed. Available operations:
ParseCSV - convert the csv files downloaded from the Google Sheet to database.json.
Prototype - create various files to illustrate how database.json should be interpreted.
""")

parser.add_argument('--homeDir',type=str,default='.',help='All other pathnames are relative to this directory; Default: ./')
parser.add_argument('--jsonFile',type=str,default='database.json',help='Read/write this json file; Default: database.json')

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

# Then run the specified operations in sequential order
for moduleName in moduleList:
    if moduleName in opList:
        if clOptions.verbose >= 0:
            print(f"{'-'*10} {moduleName} {'-'*(25 - len(moduleName))}")
        modules[moduleName].main(clOptions)
