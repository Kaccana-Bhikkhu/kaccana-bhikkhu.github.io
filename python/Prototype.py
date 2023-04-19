"""A module to create various prototype versions of the website for testing purposes"""

import os, json
from typing import List, Type, Tuple 
from airium import Airium
import Utils
from datetime import timedelta
import re

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
    nav("The Ajahn Pasanno Question and Story Archive")
with nav.p():
    with nav.a(href = "../index.html"):
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
    with nav.a(href = "../indexes/AllExcerpts.html"):
        nav(" All excerpts")
    nav.hr()
gNavigation = str(nav)
del nav

gWrittenHtmlFiles = set()
def WriteHtmlFile(fileName: str,title: str,body: str,additionalHead:str = "",customHead:str = None,navigation:bool = True) -> None:
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
    
    gWrittenHtmlFiles.add(fileName)

def DeleteUnwrittenHtmlFiles() -> None:
    """Remove old html files from previous runs to keep things neat and tidy."""

    dirs = ["events","tags","indexes"]
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
    
def ListLinkedTeachers(teachers:List[str],*args,**kwargs) -> str:
    """Write a list of hyperlinked teachers.
    teachers is a list of abbreviated teacher names"""
    
    fullNameList = [gDatabase["teacher"][t]["fullName"] for t in teachers]
    
    return ItemList(fullNameList,*args,**kwargs)

def WriteIndentedHtmlTagList(pageDir: str,fileName: str, listDuplicateSubtags = True) -> None:
    """Write an indented list of tags."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    tabMeasurement = 'em'
    tabLength = 2
    
    a = Airium()
    
    with a.h1():
        a("Tag/subtag hierarchy:")
    
    skipSubtagLevel = 999 # Skip subtags indented more than this value; don't skip any to start with
    for index, item in enumerate(gDatabase["tagDisplayList"]):
        if not listDuplicateSubtags:
            if item["level"] > skipSubtagLevel:
                continue
            # print(index,item["tag"])
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
    
    WriteHtmlFile(os.path.join(pageDir,fileName),"All Tags",str(a))

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
    
    with a.h1():
        a("Most common tags:")
    
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

def AudioIcon(hyperlink: str,iconWidth = "30") -> str:
    "Return an audio icon with the given hyperlink"
    
    a = Airium(source_minify=True)
    a.a(href = hyperlink, style="text-decoration: none;").img(src = "../images/audio.png",width = iconWidth)
        # text-decoration: none ensures the icon isn't underlined
    return str(a)

def Mp3ExcerptLink(excerpt: dict) -> str:
    """Return an html-formatted audio icon linking to a given excerpt.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
    
    if gOptions.excerptMp3 == 'local':
        baseURL = "../../audio/excerpts/"
    else:
        baseURL = gOptions.remoteExcerptMp3URL
        
    return AudioIcon(baseURL + excerpt["event"] + "/" + Utils.Mp3FileName(excerpt["event"],excerpt['sessionNumber'],excerpt['fileNumber']))
    
def Mp3SessionLink(session: dict) -> str:
    """Return an html-formatted audio icon linking to a given session.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
    
    if gOptions.sessionMp3 == "local":
        url = "../../audio/events/" + "/" + session["event"] + "/" + session["filename"]
    else:
        url = session["remoteMp3Url"]
        
    return AudioIcon(url)
    
    

def EventLink(event:str, session: int = 0) -> str:
    "Return a link to a given event and session. If session == 0, link to the top of the event page"
    
    directory = "../events/"
    if session:
        return f"{directory}{event}.html#{event}_S{session}"
    else:
        return f"{directory}{event}.html#"
    
def EventDateStr(event: dict) -> str:
    "Return a string describing when the event occured"
    
    dateStr = Utils.ReformatDate(event["startDate"])
    if event["endDate"] and event["endDate"] != event["startDate"]:
        dateStr += " to " + Utils.ReformatDate(event["endDate"])
    return dateStr

class Formatter: 
    """A class that formats lists of events, sessions, and excerpts into html"""
    
    def __init__(self):
        self.excerptDefaultTeacher = set() # Don't print the list of teachers if it matches the items in this list / set
        self.excerptOmitTags = set() # Don't display these tags in excerpt description
        self.excerptBoldTags = set() # Display these tags in boldface
        self.excerptOmitSessionTags = True # Omit tags already mentioned by the session heading
        self.excerptPreferStartTime = False # Display the excerpt start time instead of duration when available
        self.excerptShortFormat = True

        
        self.headingShowEvent = True # Show the event name in headings?
        self.headingShowSessionTitle = False # Show the session title in headings?
        self.headingLinks = True # Link to the event page in our website?
        self.headingAudio = False # Link to original session audio?
        self.headingShowTags = True # List tags in the session heading
        
        pass
    
    def FormatExcerpt(self,excerpt:dict) -> str:
        "Return excerpt formatted in html according to our stored settings."
        
        a = Airium(source_minify=True)
        
        a(Mp3ExcerptLink(excerpt))
        if self.excerptShortFormat:
            a(' ')
            with a.b(style="text-decoration: underline;"):
                a(f"{excerpt['excerptNumber']}.")
        
        if self.excerptPreferStartTime and excerpt.get("startTime",""):
            a(f' [{excerpt["startTime"]}] ')
        else:
            a(f' ({excerpt["duration"]}) ')

        def ListAttributionKeys() -> Tuple[str,str]:
            for num in range(1,10):
                numStr = str(num) if num > 1 else ""
                yield ("attribution" + numStr, "teachers" + numStr)

        bodyWithAttributions = excerpt["body"]
        for attrKey,teacherKey in ListAttributionKeys():
            if attrKey not in excerpt:
                break

            if set(excerpt[teacherKey]) != set(self.excerptDefaultTeacher): # Compare items irrespective of order
                teacherList = [gDatabase["teacher"][t]["fullName"] for t in excerpt[teacherKey]]
            else:
                teacherList = []

            if teacherList or gOptions.attributeAll:
                attribution = excerpt[attrKey]
            else:
                attribution = ""
            
            bodyWithAttributions = bodyWithAttributions.replace("{"+ attrKey + "}",attribution)
        
        a(bodyWithAttributions + ' ')
        
        if not self.excerptShortFormat:
            a(gDatabase["event"][excerpt["event"]]["title"] + ",")
            a(f"Session {excerpt['sessionNumber']}, Excerpt {excerpt['excerptNumber']}")
        
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
        
    def FormatSessionHeading(self,session:dict) -> str:
        "Return an html string representing the heading for this section"
        
        a = Airium(source_minify=True)
        event = gDatabase["event"][session["event"]]
        
        bookmark = f'{session["event"]}_S{session["sessionNumber"]}'
        with a.h2(id = bookmark):
            if self.headingShowEvent: 
                if self.headingLinks:
                    with a.a(href = EventLink(session["event"])):
                        a(event["title"])
                else:
                    a(event["title"])
                a(", ")
            
            sessionTitle = f'Session {session["sessionNumber"]}'
            if self.headingShowSessionTitle and session["sessionTitle"]:
                sessionTitle += ': ' + session["sessionTitle"]
            
            if self.headingLinks:
                with a.a(href = EventLink(session["event"],session["sessionNumber"])):
                    a(sessionTitle)
            else:
                a(sessionTitle)

            dateStr = Utils.ReformatDate(session['date'])
            teacherList = ListLinkedTeachers(session["teachers"])
            a(f' – {teacherList} – {dateStr}')
            
            if self.headingAudio:
                durStr = Utils.TimeDeltaToStr(Utils.StrToTimeDelta(session["duration"])) # Pretty-print duration by converting it to seconds and back
                a(f' – {Mp3SessionLink(session)} ({durStr}) ')
            
            if self.headingShowTags:
                a(' ')
                tagStrings = []
                for tag in session["tags"]:
                    tagStrings.append('[' + HtmlTagLink(tag) + ']')
                a(' '.join(tagStrings))
        
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

def HtmlExcerptList(excerpts: List[dict],formatter: Type[Formatter]) -> str:
    """Return a html list of the excerpts."""
    
    a = Airium()
    
    tabMeasurement = 'em'
    tabLength = 2
    
    prevEvent = None
    prevSession = None
    for x in excerpts:
        if x["event"] != prevEvent or x["sessionNumber"] != prevSession:
            session = Utils.FindSession(gDatabase["sessions"],x["event"],x["sessionNumber"])
            a(formatter.FormatSessionHeading(session))
            prevEvent = x["event"]
            prevSession = x["sessionNumber"]
            formatter.excerptDefaultTeacher = set(session["teachers"])
            
        with a.p():
            a(formatter.FormatExcerpt(x))
        
        tagsAlreadyPrinted = set(x["tags"])
        for annotation in x["annotations"]:
            if annotation["body"]:
                with a.p(style = f"margin-left: {tabLength * (annotation['indentLevel'])}{tabMeasurement};"):
                    a(formatter.FormatAnnotation(annotation,tagsAlreadyPrinted))
                tagsAlreadyPrinted.update(annotation.get("tags",()))
    
    return str(a)

def WriteAllExcerpts(pageDir: str) -> None:
    """Write a single page containing all excerpts."""
    if not os.path.exists(pageDir):
        os.makedirs(pageDir)
    
    a = Airium()
    
    with a.h1():
        a("All excerpts:")
    
    with a.h2():
        a(ExcerptDurationStr(gDatabase["excerpts"]))
        a.br()
    
    with a.h3():
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
    
    with a.h1():
        a("All events:")
        
    for eventCode,e in gDatabase["event"].items():
        with a.h2(style = "line-height: 1.3;"):
            with a.a(href = EventLink(eventCode)):
                a(e["title"])            
        
        with a.h3(style = "line-height: 1.3;"):
            a(f'{ListLinkedTeachers(e["teachers"],lastJoinStr = " and ")}')
            a.br()
            a(EventDateStr(e))
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
        
        with a.h1():
            if tagInfo['fullPali'] and tagInfo['pali'] != tagInfo['fullTag']:
                a(tagInfo['fullTag'])
                a(f"[{tagInfo['fullPali']}]:")
            else:
                a(tagInfo['fullTag'] + ':')
            
        
        with a.h3():
            a(TitledList("Alternative translations",tagInfo['alternateTranslations'],plural = ""))
        
        with a.h3(style = "line-height: 1.5;"):
            a(ListLinkedTags("Parent topic",tagInfo['supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['subtags']))
            a(ListLinkedTags("See also",tagInfo['related'],plural = ""))
            a(ExcerptDurationStr(relevantQs,False,False))
        
        formatter = Formatter()
        formatter.excerptBoldTags = set([tag])
        formatter.headingShowTags = False
        formatter.excerptOmitSessionTags = False
        a(HtmlExcerptList(relevantQs,formatter))
        
        WriteHtmlFile(os.path.join(tagPageDir,tagInfo["htmlFile"]),tag,str(a))

def WriteEventPages(tagPageDir: str) -> None:
    """Write a html file for each event in the database"""
    
    if not os.path.exists(tagPageDir):
        os.makedirs(tagPageDir)
            
    for eventCode,eventInfo in gDatabase["event"].items():
        
        sessions = [s for s in gDatabase["sessions"] if s["event"] == eventCode]
        excerpts = [x for x in gDatabase["excerpts"] if x["event"] == eventCode]
        a = Airium()
        
        with a.h1():
            title = eventInfo["title"]
            if eventInfo["subtitle"]:
                title += " – " + eventInfo["subtitle"]
            a(title)
        
        with a.h2(style = "line-height: 1.5;"):
            dateStr = EventDateStr(eventInfo)
            
            a(ListLinkedTeachers(eventInfo["teachers"],lastJoinStr = " and "))
            a.br()
            
            a(dateStr)
            a.br()
            
            a(f"{eventInfo['venue']} in {gDatabase['venue'][eventInfo['venue']]['location']}")
            a.br()
            
            a(ExcerptDurationStr(excerpts))
            a.br()
            
            with a.a(href = eventInfo["website"]):
                a("External website")
            a.br()
            a.br()
            
            squish = Airium(source_minify = True) # Temporarily eliminate whitespace in html code to fix minor glitches
            squish("Sessions:")
            for s in sessions:
                squish(4*"&nbsp")
                with squish.a(href = f"#{eventCode}_S{s['sessionNumber']}"):
                    squish(str(s['sessionNumber']))
                
            a(str(squish))
        
        if eventInfo["description"]:
            with a.p(style = "font-size: 120%;"):
                a(eventInfo["description"])
        
        a.hr()
        
        formatter = Formatter()
        formatter.headingShowEvent = False
        formatter.headingShowSessionTitle = True
        formatter.headingLinks = False
        formatter.headingAudio = True
        formatter.excerptPreferStartTime = True
        a(HtmlExcerptList(excerpts,formatter))
        
        WriteHtmlFile(os.path.join(tagPageDir,eventCode+'.html'),eventInfo["title"],str(a))
        
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
    
    WriteHtmlFile(indexPage,"The Ajahn Pasanno Question and Story Archive",'\n'.join([nav,sourceComment,htmlBody]),customHead = '\n'.join([head,str(styleInfo)]),navigation = False)
    
    # Now write prototype/README.md to make this material easily readable on github
    
    with open(os.path.join(gOptions.prototypeDir,'README.md'), 'w', encoding='utf-8') as readMe:
        print(sourceComment, file = readMe)
        readMe.write(htmlBody)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')
    parser.add_argument('--indexHtmlTemplate',type=str,default='prototype/templates/index.html',help='Use this file to create index.html; Default: prototype/templates/index.html')    
    parser.add_argument('--attributeAll',action='store_true',help="Attribute all excerpts; mostly for debugging")
    parser.add_argument('--keepOldHtmlFiles',action='store_true',help="Keep old html files from previous runs; otherwise delete them")

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
    WriteIndentedHtmlTagList(indexDir,"AllTags.html",False)
    WriteIndentedHtmlTagList(indexDir,"AllTagsExpanded.html",True)
    WriteSortedHtmlTagList(indexDir)
    WriteAllExcerpts(indexDir)
    WriteAllEvents(indexDir)
    
    WriteTagPages(os.path.join(gOptions.prototypeDir,"tags"))
    
    WriteEventPages(os.path.join(gOptions.prototypeDir,"events"))
    
    WriteIndexPage(gOptions.indexHtmlTemplate,os.path.join(gOptions.prototypeDir,"index.html"))

    if not clOptions.keepOldHtmlFiles:
        DeleteUnwrittenHtmlFiles()
    