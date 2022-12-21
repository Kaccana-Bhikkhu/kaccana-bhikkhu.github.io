"""A module to create various prototype versions of the website for testing purposes"""

import os, json

def WriteIndentedTagDisplayList(fileName):
    with open(fileName,'w', encoding='utf-8') as file:
        for item in gDatabase["Tag_DisplayList"]:
            indent = "    " * (item["Level"] - 1)
            indexStr = item["Index #"] + ". " if item["Index #"] else ""
            
            
            tagFromText = item['Text'].split(' [')[0].split(' {')[0] # Extract the text before either ' [' or ' {'
            if tagFromText != item['Tag']:
                reference = " -> " + item['Tag']
            else:
                reference = ""
            
            print(''.join([indent,indexStr,item['Text'],reference]),file = file)
    

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
    
    