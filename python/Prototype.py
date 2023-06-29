"""A module to create various prototype versions of the website for testing purposes"""

from __future__ import annotations

import os
from typing import List, Type, Tuple 
from airium import Airium
import Utils
from datetime import timedelta
import re
from collections import namedtuple
import pyratemp
from functools import lru_cache

def WriteIndentedTagDisplayList(fileName):
    with open(fileName,'w',encoding='utf-8') as file:
        for item in gDatabase["tagDisplayList"]:
            indent = "    " * (item["level"] - 1)
            indexStr = item["indexNumber"] + ". " if item["indexNumber"] else ""
            
            
            tagFromText = item['text'].split(' [')[0].split(' {')[0] # Extract the text before either ' [' or ' {'
            if tagFromText != item['tag']:
                reference = " -> " + item['tag']
            else:
                reference = ""
            
            print(''.join([indent,indexStr,item['text'],reference]),file = file)

MenuItem = namedtuple("MenuItem",["name","link"])

def HorizontalMenu(items: List[MenuItem],spaces: int = 5) -> str:
    """Return an html-formatted horizontal menu"""
    
    menuItems = []
    for name,link in items:
        itemText = Airium(source_minify=True)
        with itemText.a(href = link):
            itemText(name)
        menuItems.append(str(itemText))
    
    return (" " + "&nbsp"*spaces).join(menuItems)

"Create the default html header"
head = Airium()
head.meta(charset="utf-8")
head.meta(name="robots", content="noindex, nofollow")
with head.style():
    head('body {background-image: url("../images/PrototypeWatermark.png"); }')
    head('p {font-size: 110%;}')
gDefaultHead = str(head)
del head # Clean up the global namespace

"Create the top navigation guide"
nav = Airium(source_minify=True)
mainMenu = []
mainMenu.append(MenuItem("Homepage","../homepage.html"))
mainMenu.append(MenuItem("Tag/subtag hierarchy","../indexes/AllTags.html"))
mainMenu.append(MenuItem("Most common tags","../indexes/SortedTags.html"))
mainMenu.append(MenuItem("Events","../indexes/AllEvents.html"))
mainMenu.append(MenuItem("Teachers","../indexes/AllTeachers.html"))
mainMenu.append(MenuItem("All excerpts","../indexes/AllExcerpts.html"))
nav(HorizontalMenu(mainMenu))
gNavigation = str(nav)
del nav

gWrittenHtmlFiles = set()

@lru_cache(maxsize = None)
def GlobalTemplate(directoryDepth:int = 1) -> pyratemp.Template:
    with open(gOptions.globalTemplate,encoding='utf-8') as file:
        temp = file.read()

    temp = temp.replace('"../','"' + '../' * directoryDepth)
    return pyratemp.Template(temp)

def WriteHtmlFile(fileName: str,title: str,body: str,directoryDepth:int = 1,titleInBody:str|None = None) -> None:
    """Write a complete html file given a title, body, and header.
        fileName - name of the file to write
        title - internal title of the html page
        body - website body page - can be quite a long string
       directoryDepth - how deep is the file we're writing?"""
    
    globalTemplate = GlobalTemplate(directoryDepth)
    navigation = gNavigation.replace('"../','"' + '../' * directoryDepth)

    if not titleInBody:
        titleInBody = title

    with open(fileName,'w',encoding='utf-8') as file:
        print(globalTemplate(title = title,body = body,mainMenu=navigation,titleInBody = titleInBody),file=file)
    
    gWrittenHtmlFiles.add(fileName)

def DeleteUnwrittenHtmlFiles() -> None:
    """Remove old html files from previous runs to keep things neat and tidy."""

    dirs = ["events","tags","indexes","teachers"]
    dirs = [os.path.join(gOptions.prototypeDir,dir) for dir in dirs]

    for dir in dirs:
        fileList = next(os.walk(dir), (None, None, []))[2]
        for fileName in fileList:
            fullPath = os.path.join(dir,fileName)
            if fullPath not in gWrittenHtmlFiles:
                os.remove(fullPath)

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
        ref = gDatabase["tag"][tag]["htmlFile"]
        if fullTag:
            tag = gDatabase["tag"][tag]["fullTag"]
    except KeyError:
        ref = gDatabase["tag"][gDatabase["tagSubsumed"][tag]]["htmlFile"]
    
    return f'<a href = "../tags/{ref}">{tag}</a>'


def ListLinkedTags(title:str, tags:List[str],*args,**kwargs) -> str:
    "Write a list of hyperlinked tags"
    
    linkedTags = [HtmlTagLink(tag) for tag in tags]
    return TitledList(title,linkedTags,*args,**kwargs)

gTeacherRegex = ""
gReverseTeacherLookup = {}
def LinkTeachersInText(text: str) -> str:
    """Search text for the names of teachers with teacher pages and add hyperlinks accordingly."""

    global gTeacherRegex,gReverseTeacherLookup
    if not gTeacherRegex:
        gTeacherRegex = Utils.RegexMatchAny(t["fullName"] for t in gDatabase["teacher"].values() if t["htmlFile"])
        gReverseTeacherLookup = {gDatabase["teacher"][abbr]["fullName"]:abbr for abbr in gDatabase["teacher"]}
    
    def HtmlTeacherLink(matchObject: re.Match) -> str:
        teacher = gReverseTeacherLookup[matchObject[1]]
        htmlFile = TeacherLink(teacher)
        return f'<a href = {htmlFile}>{matchObject[1]}</a>'

    return re.sub(gTeacherRegex,HtmlTeacherLink,text)


def ListLinkedTeachers(teachers:List[str],*args,**kwargs) -> str:
    """Write a list of hyperlinked teachers.
    teachers is a list of abbreviated teacher names"""
    
    fullNameList = [gDatabase["teacher"][t]["fullName"] for t in teachers]
    
    return LinkTeachersInText(ItemList(fullNameList,*args,**kwargs))

def WriteIndentedHtmlTagList(pageDir: str,fileName: str, listDuplicateSubtags = True) -> None:
    """Write an indented list of tags."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    tabMeasurement = 'em'
    tabLength = 2
    
    a = Airium()
    
    skipSubtagLevel = 999 # Skip subtags indented more than this value; don't skip any to start with
    for index, item in enumerate(gDatabase["tagDisplayList"]):
        if not listDuplicateSubtags:
            if item["level"] > skipSubtagLevel:
                continue
            if item["tag"] and gDatabase["tag"][item["tag"]]["listIndex"] != index: # If the primary tag is at another position in the list (i.e. it's not us)
                skipSubtagLevel = item["level"] # skip subsequent subtags
            else:
                skipSubtagLevel = 999 # otherwise don't skip anything
        
        with a.p(style = f"margin-left: {tabLength * (item['level']-1)}{tabMeasurement};"):
            indexStr = item["indexNumber"] + "." if item["indexNumber"] else ""
            
            countStr = f' ({item["excerptCount"]})' if item["excerptCount"] > 0 else ''
            
            if item['tag'] and not item['subsumed']:
                nameStr = HtmlTagLink(item['tag'],True) + countStr
            else:
                nameStr = item['name']
            
            if item['pali'] and item['pali'] != item['name']:
                paliStr = '[' + item['pali'] + ']'
            else:
                paliStr = ''
            
            if item['subsumed']:
                seeAlsoStr = 'see ' + HtmlTagLink(item['tag'],False) + countStr
            else:
                seeAlsoStr = ''
                
            a(' '.join([indexStr,nameStr,paliStr,seeAlsoStr]))
    
    WriteHtmlFile(os.path.join(pageDir,fileName),"Tag/subtag hierarchy",str(a))

def ExcerptCount(tag:str) -> int:
    try:
        return gDatabase["tag"][tag]["excerptCount"]
    except KeyError:
        return 0

def WriteSortedHtmlTagList(pageDir: str) -> None:
    """Write a list of tags sorted by number of excerpts."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    # Sort descending by number of excerpts and in alphabetical order
    tagsSortedByQCount = sorted((tag for tag in gDatabase["tag"] if ExcerptCount(tag)),key = lambda tag: (-ExcerptCount(tag),tag))
    for tag in tagsSortedByQCount:
        with a.p():
            tagDesc = gDatabase["tag"][tag]
            
            xCount = ExcerptCount(tag)
            countStr = f' ({xCount})' if xCount > 0 else ''
            
            tagStr = HtmlTagLink(tagDesc['tag'])
            
            if tagDesc['pali'] and tagDesc['pali'] != tagDesc['tag']:
                paliStr = '[' + tagDesc['pali'] + ']'
            else:
                paliStr = ''
            
            a(' '.join([countStr,tagStr,paliStr]))
    
    WriteHtmlFile(os.path.join(pageDir,"SortedTags.html"),"Most common tags",str(a))

def AudioIcon(hyperlink: str,iconWidth = "30",linkKind = None,preload = "metadata") -> str:
    "Return an audio icon with the given hyperlink"
    
    if not linkKind:
        linkKind = gOptions.audioLinks

    a = Airium(source_minify=True)
    if linkKind == "img":
        a.a(href = hyperlink, style="text-decoration: none;").img(src = "../images/audio.png",width = iconWidth)
            # text-decoration: none ensures the icon isn't underlined
    else:
        with a.audio(controls = "", src = hyperlink, preload = preload, style="vertical-align: middle;"):
            with a.a(href = hyperlink):
                a("Download audio")
        a.br()
	
    return str(a).replace("<audio", "<audio-chip").replace("</audio", "</audio-chip")

def Mp3ExcerptLink(excerpt: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given excerpt.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
        
    return AudioIcon(Utils.Mp3Link(excerpt),**kwArgs)
    
def Mp3SessionLink(session: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given session.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
        
    return AudioIcon(Utils.Mp3Link(session),**kwArgs)
    
def EventLink(event:str, session: int = 0) -> str:
    "Return a link to a given event and session. If session == 0, link to the top of the event page"
    
    directory = "../events/"
    if session:
        return f"{directory}{event}.html#{event}_S{session}"
    else:
        return f"{directory}{event}.html#"

def TeacherLink(teacher:str) -> str:
    "Return a link to a given teacher page. Return an empty string if the teacher doesn't have a page."
    directory = "../teachers/"

    htmlFile = gDatabase["teacher"][teacher]["htmlFile"]
    if htmlFile:
        return f"{directory}{htmlFile}"
    else:
        return ""
    
def EventDateStr(event: dict) -> str:
    "Return a string describing when the event occured"
    
    dateStr = Utils.ReformatDate(event["startDate"])
    if event["endDate"] and event["endDate"] != event["startDate"]:
        dateStr += " to " + Utils.ReformatDate(event["endDate"])
    return dateStr

def EventSeriesAndDateStr(event: dict) -> str:
    "Return a string describing the event series and date"
    joinItems = []
    series = event["series"]
    if series != "Other":
        joinItems.append(re.sub(r's$','',series))
    joinItems.append(EventDateStr(event))
    return ", ".join(joinItems)

class Formatter: 
    """A class that formats lists of events, sessions, and excerpts into html"""
    
    def __init__(self):
        self.excerptDefaultTeacher = set() # Don't print the list of teachers if it matches the items in this list / set
        self.excerptOmitTags = set() # Don't display these tags in excerpt description
        self.excerptBoldTags = set() # Display these tags in boldface
        self.excerptOmitSessionTags = True # Omit tags already mentioned by the session heading
        self.excerptPreferStartTime = False # Display the excerpt start time instead of duration when available
        
        self.headingShowEvent = True # Show the event name in headings?
        self.headingShowSessionTitle = False # Show the session title in headings?
        self.headingLinks = True # Link to the event page in our website?
        self.headingShowTeacher = True # Include the teacher name in headings?
        self.headingAudio = False # Link to original session audio?
        self.headingShowTags = True # List tags in the session heading
        
        pass
    
    def FormatExcerpt(self,excerpt:dict,**kwArgs) -> str:
        "Return excerpt formatted in html according to our stored settings."
        
        a = Airium(source_minify=True)
        
        a(Mp3ExcerptLink(excerpt,**kwArgs))
        if excerpt['excerptNumber']:
            a(' ')
            with a.b(style="text-decoration: underline;"):
                a(f"{excerpt['excerptNumber']}.")
        
        if self.excerptPreferStartTime and excerpt.get("startTime","") and excerpt['excerptNumber']:
            a(f' [{excerpt["startTime"]}] ')
        else: # elif gOptions.audioLinks != "audio" or kwArgs.get("preload","") == "none":
            a(f' ({excerpt["duration"]}) ')

        def ListAttributionKeys() -> Tuple[str,str]:
            for num in range(1,10):
                numStr = str(num) if num > 1 else ""
                yield ("attribution" + numStr, "teachers" + numStr)

        bodyWithAttributions = excerpt["body"]
        for attrKey,teacherKey in ListAttributionKeys():
            if attrKey not in excerpt:
                break

            if set(excerpt[teacherKey]) != set(self.excerptDefaultTeacher) or "a" in excerpt["flags"]: # Compare items irrespective of order
                teacherList = [gDatabase["teacher"][t]["fullName"] for t in excerpt[teacherKey]]
            else:
                teacherList = []

            if teacherList or gOptions.attributeAll:
                attribution = excerpt[attrKey]
            else:
                attribution = ""
            
            bodyWithAttributions = bodyWithAttributions.replace("{"+ attrKey + "}",attribution)
        
        a(bodyWithAttributions + ' ')
        
        tagStrings = []
        for n,tag in enumerate(excerpt["tags"]):
            omitTags = self.excerptOmitTags
            if self.excerptOmitSessionTags:
                omitTags = set.union(omitTags,set(Utils.FindSession(gDatabase["sessions"],excerpt["event"],excerpt["sessionNumber"])["tags"]))
            
            if n and n == excerpt["qTagCount"]:
                tagStrings.append("//") # Separate QTags and ATags with the symbol //
                
            if tag in self.excerptBoldTags: # Always print boldface tags
                tagStrings.append('<b>[' + HtmlTagLink(tag) + ']</b>')
            elif tag not in omitTags: # Don't print tags which should be omitted
                tagStrings.append('[' + HtmlTagLink(tag) + ']')
            
        a(' '.join(tagStrings))
        
        return str(a)
    
    def FormatAnnotation(self,annotation: dict,tagsAlreadyPrinted: set) -> str:
        "Return annotation formatted in html according to our stored settings. Don't print tags that have appeared earlier in this excerpt"
        
        a = Airium(source_minify=True)

        a(annotation["body"] + " ")
        
        tagStrings = []
        for n,tag in enumerate(annotation.get("tags",())):
            omitTags = tagsAlreadyPrinted.union(self.excerptOmitTags)
            
            if tag in self.excerptBoldTags: # Always print boldface tags
                tagStrings.append('<b>[' + HtmlTagLink(tag) + ']</b>')
            elif tag not in omitTags: # Don't print tags which should be omitted
                tagStrings.append('[' + HtmlTagLink(tag) + ']')
            
        a(' '.join(tagStrings))
        
        return str(a)
        
    def FormatSessionHeading(self,session:dict,linkSessionAudio = None,horizontalRule = True) -> str:
        "Return an html string representing the heading for this section"
        
        if linkSessionAudio is None:
            linkSessionAudio = self.headingAudio

        a = Airium(source_minify=True)
        event = gDatabase["event"][session["event"]]

        bookmark = f'{session["event"]}_S{session["sessionNumber"]}'
        with a.div(Class = "title",id = bookmark):
            if self.headingShowEvent: 
                if self.headingLinks:
                    with a.a(href = EventLink(session["event"])):
                        a(event["title"])
                else:
                    a(event["title"])
                if session["sessionNumber"] > 0:
                    a(", ")
            
            if session["sessionNumber"] > 0:
                sessionTitle = f'Session {session["sessionNumber"]}'
                if self.headingShowSessionTitle and session["sessionTitle"]:
                    sessionTitle += ': ' + session["sessionTitle"]
            else:
                sessionTitle = ""
            
            if self.headingLinks:
                with a.a(href = EventLink(session["event"],session["sessionNumber"])):
                    a(sessionTitle)
            else:
                a(sessionTitle)
            
            itemsToJoin = []
            if self.headingShowEvent or sessionTitle:
                itemsToJoin.append("") # add an initial - if we've already printed part of the heading
            
            teacherList = ListLinkedTeachers(session["teachers"],lastJoinStr = " and ")
            
            if teacherList and self.headingShowTeacher:
                itemsToJoin.append(teacherList)
            
            itemsToJoin.append(Utils.ReformatDate(session['date']))

            if linkSessionAudio and gOptions.audioLinks == "img":
                durStr = Utils.TimeDeltaToStr(Utils.StrToTimeDelta(session["duration"])) # Pretty-print duration by converting it to seconds and back
                itemsToJoin.append(f'{Mp3SessionLink(session)} ({durStr}) ')
            
            a(' – '.join(itemsToJoin))

            if self.headingShowTags:
                a(' ')
                tagStrings = []
                for tag in session["tags"]:
                    tagStrings.append('[' + HtmlTagLink(tag) + ']')
                a(' '.join(tagStrings))
            
        if linkSessionAudio and gOptions.audioLinks == "audio":
            a(Mp3SessionLink(session))
            if horizontalRule:
                a.hr()
        
        return str(a)

def ExcerptDurationStr(excerpts: List[dict],countEvents = True,countSessions = True) -> str:
    "Return a string describing the duration of the excerpts we were passed."
    
    if not excerpts:
        return "No excerpts"
    
    events = set(x["event"] for x in excerpts)
    sessions = set((x["event"],x["sessionNumber"]) for x in excerpts) # Use sets to count unique elements
    duration = sum((Utils.StrToTimeDelta(x["duration"]) for x in excerpts),start = timedelta())
    
    strItems = []
    
    if len(events) > 1 and countEvents:
        strItems.append(f"{len(events)} events,")
    
    if len(sessions) > 1 and countSessions:
        strItems.append(f"{len(sessions)} sessions,")
    
    if len(excerpts) > 1:
        strItems.append(f"{len(excerpts)} excerpts,")
    else:
        strItems.append(f"{len(excerpts)} excerpt,")
    
    strItems.append(f"{Utils.TimeDeltaToStr(duration)} total duration")
    
    return ' '.join(strItems)

def HtmlExcerptList(excerpts: List[dict],formatter: Formatter) -> str:
    """Return a html list of the excerpts."""
    
    a = Airium()
    tabMeasurement = 'em'
    tabLength = 2
    
    prevEvent = None
    prevSession = None
    if excerpts:
        lastExcerpt = excerpts[-1]
    else:
        lastExcerpt = None
    
    for count,x in enumerate(excerpts):
        if x["event"] != prevEvent or x["sessionNumber"] != prevSession:
            session = Utils.FindSession(gDatabase["sessions"],x["event"],x["sessionNumber"])

            linkSessionAudio = formatter.headingAudio and not (x["startTime"] == "Session" and x["body"])
                # Omit link to the session audio if the first excerpt is a session excerpt with a body that will include it
            hr = x["startTime"] != "Session" or x["body"]
                # Omit the horzional rule if the first excerpt is a session excerpt with no body
                
            a(formatter.FormatSessionHeading(session,linkSessionAudio,hr))
            prevEvent = x["event"]
            prevSession = x["sessionNumber"]
            if formatter.headingShowTeacher and len(session["teachers"]) == 1: 
                    # If there's only one teacher who is mentioned in the session heading, don't mention him/her in the excerpts
                formatter.excerptDefaultTeacher = set(session["teachers"])
            else:
                formatter.excerptDefaultTeacher = set()
            
        if count > 20:
            options = {"preload": "none"}
        else:
            options = {}
        if x["body"]:
            with a.p():
                a(formatter.FormatExcerpt(x,**options))
        
        tagsAlreadyPrinted = set(x["tags"])
        for annotation in x["annotations"]:
            if annotation["body"]:
                with a.p(style = f"margin-left: {tabLength * (annotation['indentLevel'])}{tabMeasurement};"):
                    a(formatter.FormatAnnotation(annotation,tagsAlreadyPrinted))
                tagsAlreadyPrinted.update(annotation.get("tags",()))
        
        if gOptions.audioLinks == "audio" and x is not lastExcerpt:
            a.hr()
        
    return str(a)

def WriteAllExcerpts(pageDir: str) -> None:
    """Write a single page containing all excerpts."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    a(ExcerptDurationStr(gDatabase["excerpts"]))
    a.br()
    
    a("Use your browser's find command (Ctrl-F or ⌘-F) to search the excerpt text.")
    
    formatter = Formatter()
    formatter.excerptDefaultTeacher = ['AP']
    formatter.headingShowSessionTitle = True
    a(HtmlExcerptList(gDatabase["excerpts"],formatter))
    
    WriteHtmlFile(os.path.join(pageDir,"AllExcerpts.html"),"All excerpts",str(a))

def WriteAllEvents(pageDir: str) -> None:
    """Write a page containing a list of all events."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    firstEvent = True
    for eventCode,e in gDatabase["event"].items():
        if not firstEvent:
            a.hr()
        firstEvent = False
        with a.h3(style = "line-height: 1.3;"):
            with a.a(href = EventLink(eventCode)):
                a(e["title"])            
        
        a(f'{ListLinkedTeachers(e["teachers"],lastJoinStr = " and ")}')
        a.br()
        a(EventSeriesAndDateStr(e))
        a.br()
        eventExcerpts = [x for x in gDatabase["excerpts"] if x["event"] == eventCode]
        a(ExcerptDurationStr(eventExcerpts))
                
    WriteHtmlFile(os.path.join(pageDir,"AllEvents.html"),"All events",str(a))

def WriteTagPages(tagPageDir: str) -> None:
    """Write a html file for each tag in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
        
    xDB = gDatabase["excerpts"]
    
    for tag,tagInfo in gDatabase["tag"].items():
        if not tagInfo["htmlFile"]:
            continue
    
        relevantQs = [x for x in xDB if tag in Utils.AllTags(x)]
    
        a = Airium()
        
        with a.strong():
            a(TitledList("Alternative translations",tagInfo['alternateTranslations'],plural = ""))
            
            a(ListLinkedTags("Parent topic",tagInfo['supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['subtags']))
            a(ListLinkedTags("See also",tagInfo['related'],plural = ""))
            a(ExcerptDurationStr(relevantQs,False,False))
        
        a.hr()

        formatter = Formatter()
        formatter.excerptBoldTags = set([tag])
        formatter.headingShowTags = False
        formatter.excerptOmitSessionTags = False
        a(HtmlExcerptList(relevantQs,formatter))
        
        if tagInfo['fullPali'] and tagInfo['pali'] != tagInfo['fullTag']:
            tagPlusPali = f"{tagInfo['fullTag']} [{tagInfo['fullPali']}]"
        else:
            tagPlusPali = tag

        WriteHtmlFile(os.path.join(tagPageDir,tagInfo["htmlFile"]),tag,str(a),titleInBody=tagPlusPali)

def WriteTeacherPages(teacherPageDir: str,indexDir: str) -> None:
    """Write a html file for each teacher in the database and an index page for all teachers"""
    
    if not os.path.exists(teacherPageDir):
        os.makedirs(teacherPageDir)
        
    xDB = gDatabase["excerpts"]
    teacherDB = gDatabase["teacher"]

    teacherPageData = {}

    for t,tInfo in teacherDB.items():
        if not tInfo["htmlFile"]:
            continue

        """ For the time being, teacher pages list only excerpts by the teacher, not about the teacher.
        if tInfo["fullName"] in gDatabase["tag"]:
            relevantQs = [x for x in xDB if t in Utils.AllTeachers(x) or tInfo["fullName"] in Utils.AllTags(x)]
        else: """
        relevantQs = [x for x in xDB if t in Utils.AllTeachers(x)]
    
        a = Airium()
        
        excerptInfo = ExcerptDurationStr(relevantQs,False,False)
        teacherPageData[t] = excerptInfo
        a(excerptInfo)
        a.hr()

        formatter = Formatter()
        formatter.headingShowTags = False
        formatter.headingShowTeacher = False
        formatter.excerptOmitSessionTags = False
        formatter.excerptDefaultTeacher = set([t])
        a(HtmlExcerptList(relevantQs,formatter))
        
        WriteHtmlFile(os.path.join(teacherPageDir,tInfo["htmlFile"]),tInfo["fullName"],str(a))
    
    # Now write a page with the list of teachers:
    a = Airium()
        
    for t in teacherPageData:
        tInfo = teacherDB[t]
        with a.h3(style = "line-height: 1.3;"):
            with a.a(href = TeacherLink(t)):
                a(tInfo["fullName"])

        a(teacherPageData[t])
        a.hr()

    WriteHtmlFile(os.path.join(indexDir,"AllTeachers.html"),"Teachers",str(a))


def WriteEventPages(tagPageDir: str) -> None:
    """Write a html file for each event in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
            
    for eventCode,eventInfo in gDatabase["event"].items():
        
        sessions = [s for s in gDatabase["sessions"] if s["event"] == eventCode]
        excerpts = [x for x in gDatabase["excerpts"] if x["event"] == eventCode]
        a = Airium()
        
        with a.strong():
            a(ListLinkedTeachers(eventInfo["teachers"],lastJoinStr = " and "))
        a.br()

        a(EventSeriesAndDateStr(eventInfo))
        a.br()
        
        with a.strong():
            a(f"{eventInfo['venue']} in {gDatabase['venue'][eventInfo['venue']]['location']}")
            a.br()
            
            a(ExcerptDurationStr(excerpts))
        a.br()
        
        if eventInfo["description"]:
            with a.p():
                a(eventInfo["description"])

        with a.a(href = eventInfo["website"]):
            a("External website")
        a.br()
        
        if len(sessions) > 1:
            squish = Airium(source_minify = True) # Temporarily eliminate whitespace in html code to fix minor glitches
            squish("Sessions:")
            for s in sessions:
                squish(4*"&nbsp")
                with squish.a(href = f"#{eventCode}_S{s['sessionNumber']}"):
                    squish(str(s['sessionNumber']))
            
            a(str(squish))
        
        a.hr()
        
        formatter = Formatter()
        formatter.headingShowEvent = False
        formatter.headingShowSessionTitle = True
        formatter.headingLinks = False
        formatter.headingAudio = True
        formatter.excerptPreferStartTime = True
        a(HtmlExcerptList(excerpts,formatter))
        
        titleInBody = eventInfo["title"]
        if eventInfo["subtitle"]:
            titleInBody += " – " + eventInfo["subtitle"]

        WriteHtmlFile(os.path.join(tagPageDir,eventCode+'.html'),eventInfo["title"],str(a),titleInBody = titleInBody)
        
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
    indexPage: the name of the page to write - usually index.html"""
    
    htmlBody = ExtractHtmlBody(templateName)
    
    head = gDefaultHead.replace('"../','"') # index.html lives in the root directory, so modify directory paths accordingly.
    styleInfo = Airium()
    with styleInfo.style(type="text/css"):
        styleInfo("p { line-height: 1.3; }")
    
    nav = gNavigation.replace('"../','"')
    
    sourceComment = f"<!-- The content below has been extracted from the body of {templateName} -->"
    
    WriteHtmlFile(indexPage,"The Ajahn Pasanno Question and Story Archive",'\n'.join([sourceComment,htmlBody]),directoryDepth=0)
    
    # Now write prototype/README.md to make this material easily readable on github
    
    with open(os.path.join(gOptions.prototypeDir,'README.md'), 'w', encoding='utf-8') as readMe:
        print(sourceComment, file = readMe)
        readMe.write(htmlBody)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')
    parser.add_argument('--globalTemplate',type=str,default='prototype/templates/Global.html',help='Template for all pages; Default: prototype/templates/Global.html')
    parser.add_argument('--indexHtmlTemplate',type=str,default='prototype/templates/homepage.html',help='Use this file to create homepage.html; Default: prototype/templates/homepage.html')    
    parser.add_argument('--audioLinks',type=str,default='audio',help='Options: img (simple image), audio (html 5 audio player)')
    parser.add_argument('--attributeAll',action='store_true',help="Attribute all excerpts; mostly for debugging")
    parser.add_argument('--keepOldHtmlFiles',action='store_true',help="Keep old html files from previous runs; otherwise delete them")

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main():
    if not os.path.exists(gOptions.prototypeDir):
        os.makedirs(gOptions.prototypeDir)
    
    WriteIndentedTagDisplayList(os.path.join(gOptions.prototypeDir,"TagDisplayList.txt"))
    
    indexDir = os.path.join(gOptions.prototypeDir,"indexes")
    WriteIndentedHtmlTagList(indexDir,"AllTags.html",False)
    WriteIndentedHtmlTagList(indexDir,"AllTagsExpanded.html",True)
    WriteSortedHtmlTagList(indexDir)
    WriteAllExcerpts(indexDir)
    WriteAllEvents(indexDir)
    
    WriteTagPages(os.path.join(gOptions.prototypeDir,"tags"))

    WriteTeacherPages(os.path.join(gOptions.prototypeDir,"teachers"),indexDir)
    
    WriteEventPages(os.path.join(gOptions.prototypeDir,"events"))
    
    WriteIndexPage(gOptions.indexHtmlTemplate,os.path.join(gOptions.prototypeDir,"homepage.html"))

    if not gOptions.keepOldHtmlFiles:
        DeleteUnwrittenHtmlFiles()
    