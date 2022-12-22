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

"Create the default html header"
head = Airium()
head.meta(charset="utf-8")
gDefaultHead = str(head)
del head # Clean up the global namespace

"Create the top navigation guide"
nav = Airium()
with nav.p():
    with nav.a(href = "../indexes/AllTags.html"):
        nav("Tag/subtag hierarchy")
    nav("&nbsp"*5)
    with nav.a(href = "../indexes/SortedTags.html"):
        nav("Most common tags")
gNavigation = str(nav)
del nav

def WriteHtmlFile(fileName: str,title: str,body: str,additionalHead:str = "",customHead:str = None,navigation:bool = True):
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
            a.title(_t=title)
            if customHead is None:
                a(gDefaultHead)
                a(additionalHead)
            else:
                a(customHead)

        with a.body():
            if navigation:
                a(gNavigation)
            a(body)
    
    with open(fileName,'wb') as file:
        file.write(bytes(a))



def ListItems(title:str, items:List[str], plural:str = "s", joinStr:str = ", ",titleEnd:str = ": ",newLine:str = "<br>") -> str:
    "Format a list of items as a single line in html code"
    
    if not items:
        return ""
    if len(items) > 1:
        title += plural
    
    listStr = joinStr.join(items)
    
    return title + titleEnd + listStr + newLine

def HtmlTagLink(tag:str, fullTag: bool = False) -> str:
    """Turn a tag name into a hyperlink to that tag.
    Simplying assumption: All html pages (except index.html) are in a subdirectory of prototype.
    Thus ../tags will reference the tags directory from any other html pages.
    If fullTag, the link text contains the full tag name."""
    
    try:
        ref = gDatabase["Tag"][tag]["html file"]
        if fullTag:
            tag = gDatabase["Tag"][tag]["Full tag"]
    except KeyError:
        ref = gDatabase["Tag"][gDatabase["Tag_Subsumed"][tag]]["html file"]
    
    return f'<a href = "../tags/{ref}">{tag}</a>'


def ListLinkedTags(title:str, tags:List[str],*args,**kwargs) -> str:
    "Write a list of hyperlinked tags"
    
    linkedTags = [HtmlTagLink(tag) for tag in tags]
    return ListItems(title,linkedTags,*args,**kwargs)

def WriteIndentedHtmlTagList(pageDir: str) -> None:
    """Write an indented list of tags."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    tabMeasurement = 'em'
    tabLength = 2
    
    a = Airium()
    
    with a.h1():
        a("Tag/subtag hierarchy:")
    
    for item in gDatabase["Tag_DisplayList"]:
        with a.p(style = f"margin-left: {tabLength * (item['Level']-1)}{tabMeasurement};"):
            indexStr = item["Index #"] + "." if item["Index #"] else ""
            
            countStr = f' ({item["Question count"]})' if item["Question count"] > 0 else ''
            
            if item['Tag'] and not item['Subsumed']:
                nameStr = HtmlTagLink(item['Tag'],True) + countStr
            else:
                nameStr = item['Name']
            
            if item['Pāli'] and item['Pāli'] != item['Name']:
                paliStr = '[' + item['Pāli'] + ']'
            else:
                paliStr = ''
            
            if item['Subsumed']:
                seeAlsoStr = 'see ' + HtmlTagLink(item['Tag'],False) + countStr
            else:
                seeAlsoStr = ''
                
            a(' '.join([indexStr,nameStr,paliStr,seeAlsoStr]))
    
    WriteHtmlFile(os.path.join(pageDir,"AllTags.html"),"All Tags",str(a))

def QuestionCount(tag:str) -> int:
    try:
        return gDatabase["Tag"][tag]["Question count"]
    except KeyError:
        return 0

def WriteSortedHtmlTagList(pageDir: str) -> None:
    """Write a list of tags sorted by number of questions."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    with a.h1():
        a("Most common tags:")
    
    tagsSortedByQCount = sorted(gDatabase["Tag"],key = QuestionCount,reverse = True)
    for tag in tagsSortedByQCount:
        with a.p():
            tagDesc = gDatabase["Tag"][tag]
            
            qCount = QuestionCount(tag)
            countStr = f' ({qCount})' if qCount > 0 else ''
            
            tagStr = HtmlTagLink(tagDesc['Tag'])
            
            if tagDesc['Pāli'] and tagDesc['Pāli'] != tagDesc['Tag']:
                paliStr = '[' + tagDesc['Pāli'] + ']'
            else:
                paliStr = ''
            
            a(' '.join([countStr,tagStr,paliStr]))
    
    WriteHtmlFile(os.path.join(pageDir,"SortedTags.html"),"Most common tags",str(a))
        

class QuestionFormatter: 
    """A class that formats questions into html"""
    
    def __init__(self):
        pass

def QuestionDesc(question: dict) -> str:
    """Returns a html-format string describing a single question in the database"""
    
    a = Airium()
    
    a.a(href = "../../audio/questions/" + question["Event"] + "/" + Mp3FileName(question["Event"],question['Session #'],question['Question #'])).img(src = "../images/audio.png",width = "30")
    a(f'“{question["Question text"]}”')
    a(gDatabase["Event"][question["Event"]]["Title"] + ",")
    a(f"Session {question['Session #']}, Question {question['Question #']}")
    
    return str(a)

def WriteTagPages(tagPageDir: str) -> None:
    """Write a html file for each tag in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
        
    qDB = gDatabase["Questions"]
    
    for tag in gDatabase["Tag"]:
        tagInfo = gDatabase["Tag"][tag]
        if not tagInfo["html file"]:
            continue
    
        a = Airium()
        
        with a.h1():
            if tagInfo['Pāli'] and tagInfo['Pāli'] != tag:
                a(tag)
                a(f"[{tagInfo['Pāli']}]:")
            else:
                a(tag + ':')
            
        
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
    
    WriteIndentedHtmlTagList(os.path.join(gOptions.prototypeDir,"indexes"))
    WriteSortedHtmlTagList(os.path.join(gOptions.prototypeDir,"indexes"))
    
    WriteTagPages(os.path.join(gOptions.prototypeDir,"tags"))
    