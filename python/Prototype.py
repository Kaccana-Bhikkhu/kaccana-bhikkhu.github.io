"""A module to create various prototype versions of the website for testing purposes"""

import os, json
from typing import List
from airium import Airium
from Utils import slugify, Mp3FileName

def WriteIndentedTagDisplayList(fileName):
    with open(fileName,'w',encoding='utf-8') as file:
        for item in gDatabase["Tag_DisplayList"]:
            indent = "    " * (item["Level"] - 1)
            indexStr = item["Index #"] + ". " if item["Index #"] else ""
            
            
            tagFromText = item['Text'].split(' [')[0].split(' {')[0] # Extract the text before either ' [' or ' {'
            if tagFromText != item['Tag']:
                reference = " -> " + item['Tag']
            else:
                reference = ""
            
            print(''.join([indent,indexStr,item['Text'],reference]),file = file)

def WriteHtmlFile(fileName: str,title: str,body: str,additionalHead:str = "",customHead:str = None):
    """Write a complete html file given a title, body, and header.
        fileName - name of the file to write
        title - internal title of the html page
        body - website body page - can be quite a long string
        additionalHead - text written after the default header
        customHead - text written instead of default header; ignore additionalHead when provided"""
    
    a = Airium()

    a('<!DOCTYPE html>')
    with a.html(lang="en"):
        with a.head():
            a.meta(charset="utf-8")
            a.title(_t=title)

        with a.body():
            a(body)
    
    with open(fileName,'wb') as file:
        file.write(bytes(a))

"""    "Right mindfulness": {
      "Tag": "Right mindfulness",
      "Pāli": "sammā sati",
      "Full tag": "Right mindfulness",
      "Full Pāli": "sammā sati",
      "#": "4",
      "Alt. trans.": [],
      "See also": [
        "Mindfulness"
      ],
      "Virtual": false,
      "Subtags": [
        "Mindfulness of body",
        "Mindfulness of feeling",
        "Mindfulness of mind",
        "Mindfulness of dhammas"
      ],
      "Supertags": [
        "Eightfold Path"
      ],
      "Copies": 1,
      "Primaries": 0,
      "List index": 20,
      "Question count": 6
    },
"""

def ListItems(title:str, items:List[str], plural:str = "s", joinStr:str = ", ",titleEnd:str = ": ",newLine:str = "<br>") -> str:
    "Format a list of items as a single line in html code"
    
    if not items:
        return ""
    if len(items) > 1:
        title += plural
    
    listStr = joinStr.join(items)
    
    return title + titleEnd + listStr + newLine

def HtmlTagLink(tag:str, relativeTagDir:str = "") -> str:
    """Turn a tag name into a hyperlink to that tag.
    relativeTagDir - the tag directory relative to the directory this link is embedded in."""
    
    try:
        ref = gDatabase["Tag"][tag]["html file"]
    except KeyError:
        ref = gDatabase["Tag"][gDatabase["Tag_Subsumed"][tag]]["html file"]
    
    return f'<a href = "{ref}">{tag}</a>'


def ListLinkedTags(title:str, tags:List[str],*args,**kwargs) -> str:
    "Write a list of hyperlinked tags"
    
    linkedTags = [HtmlTagLink(tag) for tag in tags]
    return ListItems(title,linkedTags,*args,**kwargs)

"""{
      "Event": "TG2013",
      "Session #": 1,
      "Question #": 4,
      "Start time": "22:38 ",
      "End time": "",
      "Teacher": [
        "AP"
      ],
      "Question text": "Thank you for the wonderful teachings...Can you further discuss dispassion and nonattachment in the context of the 'middle way.' (particularly for a layperson in a loving relationship)",
      "Tags": [
        "Relationships",
        "Dispassion"
      ]
    },"""

def QuestionDesc(question: dict) -> str:
    """Returns a html-format string describing a single question in the database"""
    
    a = Airium()
    
    a.a(href = "../../audio/questions/" + question["Event"] + "/" + Mp3FileName(question["Event"],question['Session #'],question['Question #'])).img(src = "../../images/audio.png",width = "30")
    a(f'“{question["Question text"]}”')
    a(gDatabase["Event"][question["Event"]]["Title"] + ",")
    a(f"Session {question['Session #']}, Question {question['Question #']}")
    
    return str(a)

def WriteTagPages(tagPageDir: str) -> None:
    """Write a html file for each tag in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
    
    WriteHtmlFile(os.path.join(tagPageDir,'TestTag.html'),"Test page","<p>This is a test page</p>")
    
    qDB = gDatabase["Questions"]
    
    for tag in gDatabase["Tag"]:
        tagInfo = gDatabase["Tag"][tag]
        if not tagInfo["html file"]:
            continue
    
        a = Airium()
        
        with a.h1():
            a(f"{tag} [{tagInfo['Pāli']}]")
        
        with a.h3():
            a(ListItems("Alternative translations",tagInfo['Alt. trans.'],plural = ""))
        
        with a.h2():
            a(ListLinkedTags("Parent topic",tagInfo['Supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['Subtags']))
            a(ListLinkedTags("See also",tagInfo['See also'],plural = ""))
        
        relevantQs = [n for n in range(len(qDB)) if tag in qDB[n]["Tags"]]
        for qNum in relevantQs:
            with a.p():
                a(QuestionDesc(qDB[qNum]))
        
        WriteHtmlFile(os.path.join(tagPageDir,tagInfo["html file"]),tag,str(a))

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
    
    WriteTagPages(os.path.join(gOptions.prototypeDir,"tags"))
    