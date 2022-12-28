"""A module to create various prototype versions of the website for testing purposes"""

import os, json
from typing import List, Type
from airium import Airium
from Utils import slugify, Mp3FileName, ReformatDate, StrToTimeDelta, TimeDeltaToStr
from datetime import timedelta
import re

def SessionIndex(event:str ,sessionNum: int, sessionIndexCache:dict = None) -> int:
    "Return the index of a session specified by event and sessionNum."
    
    if not sessionIndexCache:
        sessionIndexCache = {}
        s = gDatabase["Sessions"]
        for index in range(len(s)):
            sessionIndexCache[(s[index]["Event"],s[index]["Session #"])] = index
    
    try:
        return sessionIndexCache[(event,sessionNum)]
    except KeyError:
        raise ValueError(f"Can't locate session {sessionNum} of event {event}")

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
head.meta(name="robots", content="noindex, nofollow")
with head.style():
    head('body {background-image: url("../images/PrototypeWatermark.png"); }')
gDefaultHead = str(head)
del head # Clean up the global namespace

"Create the top navigation guide"
nav = Airium(source_minify=True)
with nav.h1():
    nav("The Ajahn Pasanno Question and Answer Archive")
with nav.p():
    with nav.a(href = "../Index.html"):
        nav("Homepage")
    nav("&nbsp"*5)
    with nav.a(href = "../indexes/AllTags.html"):
        nav("Tag/subtag hierarchy")
    nav("&nbsp"*5)
    with nav.a(href = "../indexes/SortedTags.html"):
        nav(" Most common tags")
    nav("&nbsp"*5)
    with nav.a(href = "../indexes/AllEvents.html"):
        nav(" All events")
    nav("&nbsp"*5)
    with nav.a(href = "../indexes/AllQuestions.html"):
        nav(" All questions")
    nav.hr()
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

def ItemList(items:List[str], joinStr:str = ", ", lastJoinStr:str = None):
    """Format a list of items"""
    
    if lastJoinStr is None:
        lastJoinStr = joinStr
    
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    
    firstItems = joinStr.join(items[:-1])
    return lastJoinStr.join([firstItems,items[-1]])

def TitledList(title:str, items:List[str], plural:str = "s", joinStr:str = ", ",lastJoinStr:str = None,titleEnd:str = ": ",endStr:str = "<br>") -> str:
    """Format a list of items with a title as a single line in html code."""
    
    if not items:
        return ""
    if len(items) > 1:
        title += plural
    
    listStr = ItemList(items,joinStr,lastJoinStr)
    #listStr = joinStr.join(items)
    
    return title + titleEnd + listStr + endStr

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
    return TitledList(title,linkedTags,*args,**kwargs)
    
def ListLinkedTeachers(teachers:List[str],*args,**kwargs) -> str:
    """Write a list of hyperlinked teachers.
    teachers is a list of abbreviated teacher names"""
    
    fullNameList = [gDatabase["Teacher"][t]["Full name"] for t in teachers]
    
    return ItemList(fullNameList,*args,**kwargs)

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
    
    # Sort descending by number of questions and in alphabetical order
    tagsSortedByQCount = sorted((tag for tag in gDatabase["Tag"] if QuestionCount(tag)),key = lambda tag: (-QuestionCount(tag),tag))
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

def AudioIcon(hyperlink: str,iconWidth = "30") -> str:
    "Return an audio icon with the given hyperlink"
    
    a = Airium(source_minify=True)
    a.a(href = hyperlink, style="text-decoration: none;").img(src = "../images/audio.png",width = iconWidth)
        # text-decoration: none ensures the icon isn't underlined
    return str(a)

def Mp3QuestionLink(question: dict) -> str:
    """Return an html-formatted audio icon linking to a given question.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""

    return AudioIcon("../../audio/questions/" + question["Event"] + "/" + Mp3FileName(question["Event"],question['Session #'],question['File #']))

def EventLink(event:str, session: int = 0) -> str:
    "Return a link to a given event and session. If session == 0, link to the top of the event page"
    
    directory = "../events/"
    if session:
        return f"{directory}{event}.html#{event}_S{session}"
    else:
        return f"{directory}{event}.html#"
    
def EventDateStr(event: dict) -> str:
    "Return a string describing when the event occured"
    
    dateStr = ReformatDate(event["Start date"])
    if event["End date"] and event["End date"] != event["Start date"]:
        dateStr += " to " + ReformatDate(event["End date"])
    return dateStr

class Formatter: 
    """A class that formats lists of events, sessions, and questions into html"""
    
    def __init__(self):
        self.questionDefaultTeacher = set() # Don't print the list of teachers if it matches the items in this list / set
        self.questionOmitTags = set() # Don't display these tags in question description
        
        self.questionShortFormat = True
        
        self.headingShowEvent = True # Show the event name in headings?
        self.headingLinks = True # Link to the event page in our website?
        self.headingAudio = False # Link to original session audio?
        
        pass
    
    def FormatQuestion(self,question:dict) -> str:
        "Return question formatted in html according to our stored settings."
        
        a = Airium(source_minify=True)
        
        if set(question["Teachers"]) != set(self.questionDefaultTeacher): # Compare items irrespective of order
            teacherList = [gDatabase["Teacher"][t]["Full name"] for t in question["Teachers"]]
        else:
            teacherList = []
        
        a(Mp3QuestionLink(question))
        if self.questionShortFormat:
            a(' ')
            with a.b(style="text-decoration: underline;"):
                a(f"{question['Question #']}.")
            
        a(f' ({question["Duration"]})')
        a(f' “{question["Question text"]}” ')
        
        if teacherList:
            a(' Answered by ' + ItemList(items = teacherList,lastJoinStr = ' and ') + '. ')
        if not self.questionShortFormat:
            a(gDatabase["Event"][question["Event"]]["Title"] + ",")
            a(f"Session {question['Session #']}, Question {question['Question #']}")
        
        tagStrings = []
        for tag in question["Tags"]:
            if tag not in self.questionOmitTags:
                tagStrings.append('[' + HtmlTagLink(tag) + ']')
        
        a(' '.join(tagStrings))
        
        return str(a)
    
    def FormatSessionHeading(self,session:dict) -> str:
        "Return an html string representing the heading for this section"
        
        a = Airium(source_minify=True)
        event = gDatabase["Event"][session["Event"]]
        
        bookmark = f'{session["Event"]}_S{session["Session #"]}'
        with a.h2(id = bookmark):
            if self.headingShowEvent: 
                if self.headingLinks:
                    with a.a(href = EventLink(session["Event"])):
                        a(event["Title"])
                else:
                    a(event["Title"])
                a(", ")
            
            if self.headingLinks:
                with a.a(href = EventLink(session["Event"],session["Session #"])):
                    a(f'Session {session["Session #"]}')
            else:
                a(f'Session {session["Session #"]}')

            dateStr = ReformatDate(session['Date'])
            teacherList = ListLinkedTeachers(session["Teachers"])
            a(f' – {teacherList} – {dateStr}')
            
            if self.headingAudio and session["external mp3 URL"]:
                durStr = TimeDeltaToStr(StrToTimeDelta(session["Duration"])) # Pretty-print duration by converting it to seconds and back
                a(f' – {AudioIcon(session["external mp3 URL"])} ({durStr}) ')
        
        return str(a)

def QuestionDurationStr(questions: List[dict],countEvents = True,countSessions = True) -> str:
    "Return a string describing the duration of the questions we were passed."
    
    if not questions:
        return "No questions"
    
    events = set(q["Event"] for q in questions)
    sessions = set((q["Event"],q["Session #"]) for q in questions) # Use sets to count unique elements
    duration = sum((StrToTimeDelta(q["Duration"]) for q in questions),start = timedelta())
    
    strItems = []
    
    if len(events) > 1 and countEvents:
        strItems.append(f"{len(events)} events,")
    
    if len(sessions) > 1 and countSessions:
        strItems.append(f"{len(sessions)} sessions,")
    
    if len(questions) > 1:
        strItems.append(f"{len(questions)} questions,")
    else:
        strItems.append(f"{len(questions)} question,")
    
    strItems.append(f"{TimeDeltaToStr(duration)} total duration")
    
    return ' '.join(strItems)

def HtmlQuestionList(questions: List[dict],formatter: Type[Formatter]) -> str:
    """Return a html list of the questions."""
    
    a = Airium()
    
    prevEvent = None
    prevSession = None
    for q in questions:
        if q["Event"] != prevEvent or q["Session #"] != prevSession:
            sessionIndex = SessionIndex(q["Event"],q["Session #"])
            a(formatter.FormatSessionHeading(gDatabase["Sessions"][sessionIndex]))
            prevEvent = q["Event"]
            prevSession = q["Session #"]
            formatter.questionDefaultTeacher = set(gDatabase["Sessions"][sessionIndex]["Teachers"])
            
        with a.p():
            a(formatter.FormatQuestion(q))
    
    return str(a)

def WriteAllQuestions(pageDir: str) -> None:
    """Write a single page containing all questions."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    with a.h1():
        a("All questions:")
    
    with a.h2():
        a(QuestionDurationStr(gDatabase["Questions"]))
        a.br()
    
    with a.h3():
        a("Use your browser's find command (Ctrl-F or ⌘-F) to search the question text.")
    
    formatter = Formatter()
    formatter.questionDefaultTeacher = ['AP']
    a(HtmlQuestionList(gDatabase["Questions"],formatter))
    
    WriteHtmlFile(os.path.join(pageDir,"AllQuestions.html"),"All questions",str(a))

def WriteAllEvents(pageDir: str) -> None:
    """Write a page containing a list of all events."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    with a.h1():
        a("All events:")
        
    for eventCode,e in gDatabase["Event"].items():
        with a.h2(style = "line-height: 1.3;"):
            with a.a(href = EventLink(eventCode)):
                a(e["Title"])            
        
        with a.h3(style = "line-height: 1.3;"):
            a(f'{ListLinkedTeachers(e["Teachers"],lastJoinStr = " and ")}')
            a.br()
            a(EventDateStr(e))
            a.br()
            eventQuestions = [q for q in gDatabase["Questions"] if q["Event"] == eventCode]
            a(QuestionDurationStr(eventQuestions))
                
    WriteHtmlFile(os.path.join(pageDir,"AllEvents.html"),"All events",str(a))

def WriteTagPages(tagPageDir: str) -> None:
    """Write a html file for each tag in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
        
    qDB = gDatabase["Questions"]
    
    for tag,tagInfo in gDatabase["Tag"].items():
        if not tagInfo["html file"]:
            continue
    
        relevantQs = [q for q in qDB if tag in q["Tags"]]
    
        a = Airium()
        
        with a.h1():
            if tagInfo['Pāli'] and tagInfo['Pāli'] != tag:
                a(tag)
                a(f"[{tagInfo['Pāli']}]:")
            else:
                a(tag + ':')
            
        
        with a.h3():
            a(TitledList("Alternative translations",tagInfo['Alt. trans.'],plural = ""))
        
        with a.h3(style = "line-height: 1.5;"):
            a(ListLinkedTags("Parent topic",tagInfo['Supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['Subtags']))
            a(ListLinkedTags("See also",tagInfo['See also'],plural = ""))
            a(QuestionDurationStr(relevantQs,False,False))
        
        formatter = Formatter()
        formatter.questionOmitTags = set([tag])
        a(HtmlQuestionList(relevantQs,formatter))
        
        WriteHtmlFile(os.path.join(tagPageDir,tagInfo["html file"]),tag,str(a))

def WriteEventPages(tagPageDir: str) -> None:
    """Write a html file for each event in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
            
    for eventCode,eventInfo in gDatabase["Event"].items():
        
        sessions = [s for s in gDatabase["Sessions"] if s["Event"] == eventCode]
        questions = [q for q in gDatabase["Questions"] if q["Event"] == eventCode]
        a = Airium()
        
        with a.h1():
            title = eventInfo["Title"]
            if eventInfo["Subtitle"]:
                title += " – " + eventInfo["Subtitle"]
            a(title)
        
        with a.h2(style = "line-height: 1.5;"):
            dateStr = EventDateStr(eventInfo)
            
            a(ListLinkedTeachers(eventInfo["Teachers"],lastJoinStr = " and "))
            a.br()
            
            a(dateStr)
            a.br()
            
            a(f"{eventInfo['Venue']} in {gDatabase['Venue'][eventInfo['Venue']]['Location']}")
            a.br()
            
            a(QuestionDurationStr(questions))
            a.br()
            
            with a.a(href = eventInfo["Website"]):
                a("External website")
            a.br()
            a.br()
            
            squish = Airium(source_minify = True) # Temporarily eliminate whitespace in html code to fix minor glitches
            squish("Sessions:")
            for s in sessions:
                squish(4*"&nbsp")
                with squish.a(href = f"#{eventCode}_S{s['Session #']}"):
                    squish(str(s['Session #']))
                
            a(str(squish))
                    
        a.hr()
        
        formatter = Formatter()
        formatter.headingShowEvent = False
        formatter.headingLinks = False
        formatter.headingAudio = True
        a(HtmlQuestionList(questions,formatter))
        
        WriteHtmlFile(os.path.join(tagPageDir,eventCode+'.html'),eventInfo["Title"],str(a))
        
def ExtractHtmlBody(fileName: str) -> str:
    """Extract the body text from a html page"""
    
    with open(fileName,encoding='utf8') as file:
        htmlPage = file.read()
    
    bodyStart = re.search(r'<body[^>]*>',htmlPage)
    bodyEnd = re.search(r'</body',htmlPage)
    
    if not bodyStart:
        raise ValueError("Cannot find <body> tag in " + fileName)
    if not bodyEnd:
        raise ValueError("Cannot find </body> tag in " + fileName)
    
    return htmlPage[bodyStart.span()[1]:bodyEnd.span()[0]]

def WriteIndexPage(templateName: str,indexPage: str) -> None:
    """Write the index page by extracting the body from a file created by an external editor and calling WriteHtmlFile to convert it to our (extremely minimal) style.
    templateName: the file created by an external editor
    indexPage: the name of the page to write - usually Index.html"""
    
    htmlBody = ExtractHtmlBody(templateName)
    
    head = gDefaultHead.replace('"../','"') # Index.html lives in the root directory, so modify directory paths accordingly.
    nav = gNavigation.replace('"../','"')
    
    WriteHtmlFile(indexPage,"The Ajahn Pasanno Q&A Archive",nav + '\n' + htmlBody,customHead = head,navigation = False)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')
    parser.add_argument('--indexHtmlTemplate',type=str,default='prototype/templates/Index.html',help='Use this file to create Index.html; Default: prototype/templates/Index.html')
    

gOptions = None
gDatabase = None
def main(clOptions,database):
    
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    gDatabase = database
    
    if not os.path.exists(gOptions.prototypeDir):
        os.makedirs(gOptions.prototypeDir)
    
    WriteIndentedTagDisplayList(os.path.join(gOptions.prototypeDir,"TagDisplayList.txt"))
    
    indexDir = os.path.join(gOptions.prototypeDir,"indexes")
    WriteIndentedHtmlTagList(indexDir)
    WriteSortedHtmlTagList(indexDir)
    WriteAllQuestions(indexDir)
    WriteAllEvents(indexDir)
    
    WriteTagPages(os.path.join(gOptions.prototypeDir,"tags"))
    
    WriteEventPages(os.path.join(gOptions.prototypeDir,"events"))
    
    WriteIndexPage(gOptions.indexHtmlTemplate,os.path.join(gOptions.prototypeDir,"Index.html"))
    