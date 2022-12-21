"""A module to create various prototype versions of the website for testing purposes"""

import os, json

def WriteIndentedTagDisplayList(fileName):
    with open(fileName,'w', encoding='utf-8') as file:
        for item in gDatabase["Tag_DisplayList"]:
            indent = "    " * (item["Level"] - 1)
            indexStr = item["Index #"] + ". " if item["Index #"] else ""
            print(f"{indent}{indexStr}{item['Text']} -> {item['Tag']}",file = file)
    

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')

gOptions = None
gDatabase = None
def main(clOptions):
    
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    with open(gOptions.jsonFile, 'r', encoding='utf-8') as file:
        gDatabase = json.load(file)
    
    if not os.path.exists(gOptions.prototypeDir):
        os.makedirs(gOptions.prototypeDir)
    
    WriteIndentedTagDisplayList(os.path.join(gOptions.prototypeDir,"TagDisplayList.txt"))
    
    