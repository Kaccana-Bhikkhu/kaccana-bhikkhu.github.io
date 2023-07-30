"""A module to create various prototype versions of the website for testing purposes"""

from __future__ import annotations

import os
from typing import List, Iterator, Tuple, Callable
from airium import Airium
import Utils, PageDesc, Alert, Filter
from datetime import timedelta
import re, copy, itertools
from collections import namedtuple
import pyratemp, markdown
from functools import lru_cache
import contextlib

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

gWrittenHtmlFiles = set()

@lru_cache(maxsize = None)
def GlobalTemplate(directoryDepth:int = 1) -> pyratemp.Template:
    with open(gOptions.globalTemplate,encoding='utf-8') as file:
        temp = file.read()

    temp = temp.replace('"../','"' + '../' * directoryDepth)
    return pyratemp.Template(temp)

def WritePage(page: PageDesc) -> None:
    """Write an html file for page using the global template"""
    page.WriteFile(gOptions.globalTemplate,gOptions.prototypeDir)
    gWrittenHtmlFiles.add(Utils.PosixJoin(gOptions.prototypeDir,page.info.file))
    Alert.debug.Show(f"Write file: {page.info.file}")

def DeleteUnwrittenHtmlFiles() -> None:
    """Remove old html files from previous runs to keep things neat and tidy."""

    dirs = ["events","tags","indexes","teachers","drilldown","about"]
    dirs = [Utils.PosixJoin(gOptions.prototypeDir,dir) for dir in dirs]

    for dir in dirs:
        fileList = next(os.walk(dir), (None, None, []))[2]
        for fileName in fileList:
            fullPath = Utils.PosixJoin(dir,fileName)
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
    Simplying assumption: All html pages (except homepage.html and index.html) are in a subdirectory of prototype.
    Thus ../tags will reference the tags directory from any other html pages.
    If fullTag, the link text contains the full tag name."""
    
    try:
        ref = gDatabase["tag"][tag]["htmlFile"]
        if fullTag:
            tag = gDatabase["tag"][tag]["fullTag"]
    except KeyError:
        ref = gDatabase["tag"][gDatabase["tagSubsumed"][tag]]["htmlFile"]
    
    if "tags" in gOptions.buildOnly:
        return f'<a href = "../tags/{ref}">{tag}</a>'
    else:
        return tag


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
        if "teachers" in gOptions.buildOnly:
            return f'<a href = {htmlFile}>{matchObject[1]}</a>'
        else:
            return matchObject[1]

    return re.sub(gTeacherRegex,HtmlTeacherLink,text)


def ListLinkedTeachers(teachers:List[str],*args,**kwargs) -> str:
    """Write a list of hyperlinked teachers.
    teachers is a list of abbreviated teacher names"""
    
    fullNameList = [gDatabase["teacher"][t]["fullName"] for t in teachers]
    
    return LinkTeachersInText(ItemList(fullNameList,*args,**kwargs))

def ExcerptCount(tag:str) -> int:
    try:
        return gDatabase["tag"][tag]["excerptCount"]
    except KeyError:
        return 0

def IndentedHtmlTagList(expandSpecificTags:set[int]|None = None,expandDuplicateSubtags:bool = True,expandTagLink:Callable[[int],str]|None = None) -> str:
    """Generate html for an indented list of tags.
    If expandSpecificTags is specified, then expand only tags with index numbers in this set.
    If not, then expand all tags if expandDuplicateSubtags; otherwise expand only tags with primary subtags.
    If expandTagLink, add boxes to expand and contract each tag with links given by this function."""
    
    tabMeasurement = 'em'
    tabLength = 2
    
    a = Airium()
    
    tagList = gDatabase["tagDisplayList"]
    skipSubtagLevel = 999 # Skip subtags indented more than this value; don't skip any to start with
    for index, item in enumerate(tagList):
        if item["level"] > skipSubtagLevel:
            continue

        skipSubtags = False
        if expandSpecificTags is not None:
            if index not in expandSpecificTags:
                skipSubtags = True
        elif not expandDuplicateSubtags:
            if item["tag"] and gDatabase["tag"][item["tag"]]["listIndex"] != index: # If the primary tag is at another position in the list (i.e. it's not us)
                skipSubtags = True

        if skipSubtags:
            skipSubtagLevel = item["level"] # skip tags deeper than this level
        else:
            skipSubtagLevel = 999 # otherwise don't skip anything
        
        with a.p(style = f"margin-left: {tabLength * (item['level']-1)}{tabMeasurement};"):
            drilldownLink = ''
            if expandTagLink:
                if index < len(tagList) - 1 and tagList[index + 1]["level"] > item["level"]: # Can the tag be expanded?
                    if index in expandSpecificTags: # Is it already expanded?
                        tagAtPrevLevel = -1
                        for reverseIndex in range(index - 1,-1,-1):
                            if tagList[reverseIndex]["level"] < item["level"]:
                                tagAtPrevLevel = reverseIndex
                                break
                        drilldownLink = f'<a href="../drilldown/{expandTagLink(tagAtPrevLevel)}#_keep_scroll">⊟</a>'
                    else:
                        drilldownLink = f'<a href="../drilldown/{expandTagLink(index)}#_keep_scroll">⊞</a>'
                else:
                    drilldownLink = "&nbsp"

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
            
            joinBits = [s for s in [drilldownLink,indexStr,nameStr,paliStr,seeAlsoStr] if s]
            a(' '.join(joinBits))
    
    return str(a)

def DrilldownPageFile(tagNumber: int) -> str:
    "Return the name of the page that has this numbered tag expanded."
    if tagNumber == -1:
        tagNumber = 999
    fileName = f"tag-{tagNumber:03d}.html"
    return fileName

def DrilldownTags(pageInfo: PageDesc.PageInfo) -> Iterator[PageDesc.PageAugmentorType]:
    """Write a series of html files to create a hierarchial drill-down list of tags."""

    tagList = gDatabase["tagDisplayList"]

    for n,tag in enumerate(tagList[:-1]):
        if tagList[n+1]["level"] > tag["level"]: # If the next tag is deeper, then we can expand this one
            tagsToExpand = {n}
            reverseIndex = n - 1
            nextLevelToExpand = tag["level"] - 1
            while reverseIndex >= 0 and nextLevelToExpand > 0:
                if tagList[reverseIndex]["level"] <= nextLevelToExpand:
                    tagsToExpand.add(reverseIndex)
                    nextLevelToExpand = tagList[reverseIndex]["level"] - 1
                reverseIndex -= 1
            
            yield (pageInfo._replace(file=Utils.PosixJoin(pageInfo.file,DrilldownPageFile(n))),IndentedHtmlTagList(expandSpecificTags=tagsToExpand,expandTagLink=DrilldownPageFile))

def SortedHtmlTagList(pageDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Write a list of tags sorted by number of excerpts."""
    
    yield PageDesc.PageInfo("Most common tags",Utils.PosixJoin(pageDir,"SortedTags.html"))

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
    
    yield str(a)

def PlayerTitle(item:dict) -> str:
    """Generate a title string for the audio player for an excerpt or session.
    The string will be no longer than gOptions.maxPlayerTitleLength characters."""

    sessionNumber = item.get("sessionNumber",None)
    excerptNumber = item.get("excerptNumber",None)
    titleItems = []
    if sessionNumber:
        titleItems.append(f"S{sessionNumber}")
    if excerptNumber:
        titleItems.append(f"E{excerptNumber}")
    
    lengthSoFar = len(" ".join(titleItems))
    fullEventTitle = gDatabase['event'][item['event']]['title']
    if titleItems:
        fullEventTitle += ","
    titleItems.insert(0,Utils.EllideText(fullEventTitle,gOptions.maxPlayerTitleLength - lengthSoFar - 1))
    return " ".join(titleItems)
    

def AudioIcon(hyperlink: str,title: str, iconWidth:str = "30",linkKind = None,preload:str = "metadata",dataDuration:str = "") -> str:
    "Return an audio icon with the given hyperlink"
    
    if not linkKind:
        linkKind = gOptions.audioLinks

    a = Airium(source_minify=True)
    if linkKind == "img":
        a.a(href = hyperlink, title = title, style="text-decoration: none;").img(src = "../images/audio.png",width = iconWidth)
            # text-decoration: none ensures the icon isn't underlined
    elif linkKind == "audio":
        with a.audio(controls = "", src = hyperlink, title = title, preload = preload, style="vertical-align: middle;"):
            with a.a(href = hyperlink):
                a(f"Download audio")
            a(f" ({dataDuration})")
        a.br()
    else:
        durationDict = {}
        if dataDuration:
            durationDict = {"data-duration": str(Utils.StrToTimeDelta(dataDuration).seconds)}
        with a.get_tag_('audio-chip')(src = hyperlink, title = title, **durationDict):
            with a.a(href = hyperlink):
                a(f"Download audio")
            a(f" ({dataDuration})")
        a.br()
	
    return str(a)

def Mp3ExcerptLink(excerpt: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given excerpt.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
        
    return AudioIcon(Utils.Mp3Link(excerpt),dataDuration = excerpt["duration"],**kwArgs)
    
def Mp3SessionLink(session: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given session.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
        
    return AudioIcon(Utils.Mp3Link(session),dataDuration = session["duration"],**kwArgs)
    
def EventLink(event:str, session: int = 0) -> str:
    "Return a link to a given event and session. If session == 0, link to the top of the event page"
    
    directory = "../events/"
    if session:
        return f"{directory}{event}.html#{event}_S{session:02d}"
    else:
        return f"{directory}{event}.html"

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
        
        a(" ")
        if self.excerptPreferStartTime and excerpt.get("startTime","") and excerpt['excerptNumber']:
            a(f'[{excerpt["startTime"]}] ')
        elif gOptions.audioLinks != "chip":
            a(f'({excerpt["duration"]}) ')

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

        bookmark = Utils.ItemCode(session)
        with a.div(Class = "title",id = bookmark):
            if self.headingShowEvent: 
                if self.headingLinks:
                    with (a.a(href = EventLink(session["event"]))) if "events" in gOptions.buildOnly else contextlib.nullcontext():
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
                with a.a(href = EventLink(session["event"],session["sessionNumber"])) if "events" in gOptions.buildOnly else contextlib.nullcontext():
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

            if linkSessionAudio and (gOptions.audioLinks == "img" or gOptions.audioLinks =="chip"):
                audioLink = Mp3SessionLink(session,title = PlayerTitle(session))
                if gOptions.audioLinks == "img":
                    durStr = f' ({Utils.TimeDeltaToStr(Utils.StrToTimeDelta(session["duration"]))})' # Pretty-print duration by converting it to seconds and back
                else:
                    durStr = ''
                itemsToJoin.append(audioLink + durStr + ' ')
            
            a(' – '.join(itemsToJoin))

            if self.headingShowTags:
                a(' ')
                tagStrings = []
                for tag in session["tags"]:
                    tagStrings.append('[' + HtmlTagLink(tag) + ']')
                a(' '.join(tagStrings))
            
        if linkSessionAudio and gOptions.audioLinks == "audio":
            a(Mp3SessionLink(session,title = PlayerTitle(session)))
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
    
    localFormatter = copy.deepcopy(formatter) # Make a copy in case the formatter object is reused
    for count,x in enumerate(excerpts):
        if x["event"] != prevEvent or x["sessionNumber"] != prevSession:
            session = Utils.FindSession(gDatabase["sessions"],x["event"],x["sessionNumber"])

            linkSessionAudio = formatter.headingAudio and not (x["startTime"] == "Session" and x["body"])
                # Omit link to the session audio if the first excerpt is a session excerpt with a body that will include it
            hr = x["startTime"] != "Session" or x["body"]
                # Omit the horzional rule if the first excerpt is a session excerpt with no body
                
            a(localFormatter.FormatSessionHeading(session,linkSessionAudio,hr))
            prevEvent = x["event"]
            prevSession = x["sessionNumber"]
            if localFormatter.headingShowTeacher and len(session["teachers"]) == 1: 
                    # If there's only one teacher who is mentioned in the session heading, don't mention him/her in the excerpts
                localFormatter.excerptDefaultTeacher = set(session["teachers"])
            else:
                localFormatter.excerptDefaultTeacher = formatter.excerptDefaultTeacher
            
        if count > 20:
            options = {"preload": "none"}
        else:
            options = {}
        if x["body"]:
            with a.p(id = Utils.ItemCode(x)):
                a(localFormatter.FormatExcerpt(x,title=PlayerTitle(x),**options))
        
        tagsAlreadyPrinted = set(x["tags"])
        for annotation in x["annotations"]:
            if annotation["body"]:
                with a.p(style = f"margin-left: {tabLength * (annotation['indentLevel'])}{tabMeasurement};"):
                    a(localFormatter.FormatAnnotation(annotation,tagsAlreadyPrinted))
                tagsAlreadyPrinted.update(annotation.get("tags",()))
        
        if (gOptions.audioLinks == "audio" or gOptions.audioLinks == "chip") and x is not lastExcerpt:
            a.hr()
        
    return str(a)

def MultiPageExcerptList(basePage: PageDesc.PageDesc,excerpts: List[dict],formatter: Formatter,itemLimit:int = 0) -> Iterator[PageDesc.PageAugmentorType]:
    """Split an excerpt list into multiple pages, yielding a series of PageAugmentorType objects
        basePage: Content of the page above the menu and excerpt list. Later pages add "-N" to the file name.
        excerpts, formatter: As in HtmlExcerptList
        itemLimit: Limit lists to roughly this many items, but break pages only at session boundaries."""

    pageNumber = 1
    menuItems = []
    excerptsInThisPage = []
    prevSession = None
    baseName,ext = os.path.splitext(basePage.info.file)
    if itemLimit == 0:
        itemLimit = gOptions.excerptsPerPage

    def PageHtml() -> PageDesc.PageAugmentorType:
        if pageNumber > 1:
            fileName = f"{baseName}-{pageNumber}{ext}"
        else:
            fileName = basePage.info.file
        menuItem = PageDesc.PageInfo(str(pageNumber),fileName,basePage.info.titleInBody)
        
        pageHtml = HtmlExcerptList(excerptsInThisPage,formatter)
        return menuItem,(basePage.info._replace(file=fileName),pageHtml)

    for x in excerpts:
        thisSession = (x["event"],x["sessionNumber"])
        if prevSession != thisSession:
            if itemLimit and len(excerptsInThisPage) >= itemLimit:
                menuItems.append(PageHtml())
                pageNumber += 1
                excerptsInThisPage = []

        excerptsInThisPage.append(x)
        prevSession = thisSession
    
    if excerptsInThisPage or not menuItems:
        menuItems.append(PageHtml())
    
    if len(menuItems) > 1:
        yield from basePage.AddMenuAndYieldPages(menuItems,wrapper=PageDesc.Wrapper("<p>Page: " + 2*"&nbsp","</p>"))
    else:
        clone = basePage.Clone()
        clone.AppendContent(menuItems[0][1][1])
        yield clone

def FilteredExcerptsMenuItem(excerpts:list[dict], filter:Filter, formatter:Formatter, mainPageInfo:PageDesc.PageInfo, menuTitle:str, fileExt:str = "") -> PageDesc.PageDescriptorMenuItem:
    """Describes a menu item generated by applying a filter to a list of excerpts.
    excerpts: the list of excerpts.
    filter: the filter to apply.
    formatter: the formatter object to pass to HtmlExcerptList.
    mainPageInfo: description of the main page
    menuTitle: the title in the menu.
    fileExt: the extension to add to the main page file for the filtered page."""

    filteredExcerpts = list(Filter.Apply(excerpts,filter))

    if not filteredExcerpts:
        return []

    if fileExt:
        pageInfo = mainPageInfo._replace(file = Utils.AppendToFilename(mainPageInfo.file,"-" + fileExt))
    else:
        pageInfo = mainPageInfo
    menuItem = pageInfo._replace(title=f"{menuTitle} ({len(filteredExcerpts)})")

    blankPage = PageDesc.PageDesc(pageInfo)
    return itertools.chain([menuItem],MultiPageExcerptList(blankPage,filteredExcerpts,formatter))

def AllExcerpts(pageDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Generate a single page containing all excerpts."""

    pageInfo = PageDesc.PageInfo("All excerpts",Utils.PosixJoin(pageDir,"AllExcerpts.html"))
    yield pageInfo

    a = Airium()
    
    with a.p():
        a(ExcerptDurationStr(gDatabase["excerpts"]))
        a.br()
        a("Use your browser's find command (Ctrl-F or ⌘-F) to search the excerpt text.")

    basePage = PageDesc.PageDesc(pageInfo)
    basePage.AppendContent(str(a))

    formatter = Formatter()
    # formatter.excerptDefaultTeacher = ['AP']
    formatter.headingShowSessionTitle = True

    excerpts = gDatabase["excerpts"]
    filterMenu = [
        FilteredExcerptsMenuItem(excerpts,Filter.PassAll,formatter,pageInfo,"All excerpts"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(category="Questions"),formatter,pageInfo,"Questions","question"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(category="Stories"),formatter,pageInfo,"Stories","story"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(category="Quotes"),formatter,pageInfo,"Quotes","quote"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(category="Meditations"),formatter,pageInfo,"Meditations","meditation"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(category="Teachings"),formatter,pageInfo,"Teachings","teaching"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(kind={"Sutta","Vinaya","Commentary"}),formatter,pageInfo,"Texts","text"),
        FilteredExcerptsMenuItem(excerpts,Filter.Kind(kind={"Reference"}),formatter,pageInfo,"References","ref")
    ]

    filterMenu = [f for f in filterMenu if f] # Remove blank menu items
    yield from basePage.AddMenuAndYieldPages(filterMenu,wrapper=PageDesc.Wrapper("<p>","</p>"))

def ListDetailedEvents(events: list[dict]) -> str:
    """Generate html containing a detailed list of all events."""
    
    a = Airium()
    
    firstEvent = True
    for e in events:
        eventCode = e["code"]
        if not firstEvent:
            a.hr()
        firstEvent = False
        with a.h3(style = "line-height: 1.3;"):
            with a.a(href = EventLink(eventCode) if "events" in gOptions.buildOnly else contextlib.nullcontext()):
                a(e["title"])            
        
        a(f'{ListLinkedTeachers(e["teachers"],lastJoinStr = " and ")}')
        a.br()
        a(EventSeriesAndDateStr(e))
        a.br()
        eventExcerpts = [x for x in gDatabase["excerpts"] if x["event"] == eventCode]
        a(ExcerptDurationStr(eventExcerpts))
                
    return str(a)

def EventSeries(event: dict) -> str:
    return event["series"]

def EventDescription(event: dict) -> str:
    if "events" in gOptions.buildOnly:
        href = PageDesc.Wrapper(f"<a href = {EventLink(event['code'])}>","</a>")
    else:
        href = PageDesc.Wrapper()
    return f"<p> {href.Wrap(event['title'])} ({event['excerpts']}) </p>"

def ListEventsBySeries(events: list[dict]) -> str:
    """Return html code listing these events by series."""

    def SeriesIndex(event: dict) -> int:
        "Return the index of the series of this event for sorting purposes"
        return list(gDatabase["series"]).index(event["series"])
    
    eventsSorted = sorted(events,key=SeriesIndex)
    return str(PageDesc.ListWithHeadings(eventsSorted,lambda e: (e["series"],EventDescription(e)) ))

def ListEventsByYear(events: list[dict]) -> str:
    """Return html code listing these events by series."""
    
    return str(PageDesc.ListWithHeadings(events,lambda e: (str(Utils.ParseDate(e["startDate"]).year),EventDescription(e)) ,countItems=False))

def EventsMenu(indexDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Create the Events menu item and its associated submenus."""

    seriesInfo = PageDesc.PageInfo("Series",Utils.PosixJoin(indexDir,"EventsBySeries.html"),"Events – By series")
    chronologicalInfo = PageDesc.PageInfo("Chronological",Utils.PosixJoin(indexDir,"EventsChronological.html"),"Events – Chronological")
    detailInfo = PageDesc.PageInfo("Detailed",Utils.PosixJoin(indexDir,"EventDetails.html"),"Events – Detailed view")

    yield seriesInfo._replace(title="Events")

    eventMenu = [
        [seriesInfo,ListEventsBySeries(gDatabase["event"].values())],
        [chronologicalInfo,ListEventsByYear(gDatabase["event"].values())],
        [detailInfo,ListDetailedEvents(gDatabase["event"].values())],
        EventPages("events")
    ]

    baseTagPage = PageDesc.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(eventMenu,menuSection = "subMenu")

def TagPages(tagPageDir: str) -> Iterator[PageDesc.PageAugmentorType]:
    """Write a html file for each tag in the database"""
            
    for tag,tagInfo in gDatabase["tag"].items():
        if not tagInfo["htmlFile"]:
            continue

        relevantExcerpts = list(Filter.Apply(gDatabase["excerpts"],Filter.Tag(tag)))

        a = Airium()
        
        with a.strong():
            a(TitledList("Alternative translations",tagInfo['alternateTranslations'],plural = ""))
            
            a(ListLinkedTags("Parent topic",tagInfo['supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['subtags']))
            a(ListLinkedTags("See also",tagInfo['related'],plural = ""))
            a(ExcerptDurationStr(relevantExcerpts,False,False))
        
        a.hr()

        formatter = Formatter()
        formatter.excerptBoldTags = set([tag])
        formatter.headingShowTags = False
        formatter.excerptOmitSessionTags = False
        
        if tagInfo['fullPali'] and tagInfo['pali'] != tagInfo['fullTag']:
            tagPlusPali = f"{tagInfo['fullTag']} [{tagInfo['fullPali']}]"
        else:
            tagPlusPali = tag

        pageInfo = PageDesc.PageInfo(tag,Utils.PosixJoin(tagPageDir,tagInfo["htmlFile"]),tagPlusPali)
        basePage = PageDesc.PageDesc(pageInfo)
        basePage.AppendContent(str(a))

        if len(relevantExcerpts) >= gOptions.minSubsearchExcerpts:
            questions = Filter.Apply(relevantExcerpts,Filter.Kind(category="Questions"))
            qTags,aTags = Filter.Partition(questions,Filter.QTag(tag))

            filterMenu = []
            filterMenu.append(FilteredExcerptsMenuItem(relevantExcerpts,Filter.PassAll,formatter,pageInfo,"All excerpts"))
            filterMenu.append(FilteredExcerptsMenuItem(qTags,Filter.PassAll,formatter,pageInfo,"Questions about","qtag"))
            filterMenu.append(FilteredExcerptsMenuItem(aTags,Filter.PassAll,formatter,pageInfo,"Answers involving","atag"))
            filterMenu.append(FilteredExcerptsMenuItem(relevantExcerpts,Filter.Tag(tag,category="Stories"),formatter,pageInfo,"Stories","story"))
            filterMenu.append(FilteredExcerptsMenuItem(relevantExcerpts,Filter.Tag(tag,category="Quotes"),formatter,pageInfo,"Quotes","quote"))
            filterMenu.append(FilteredExcerptsMenuItem(relevantExcerpts,Filter.Tag(tag,kind={"Sutta","Vinaya","Commentary"}),formatter,pageInfo,"Texts","text"))
            filterMenu.append(FilteredExcerptsMenuItem(relevantExcerpts,Filter.Tag(tag,kind={"Reference"}),formatter,pageInfo,"References","ref"))

            filterMenu = [f for f in filterMenu if f] # Remove blank menu items
            if len(filterMenu) > 1:
                yield from basePage.AddMenuAndYieldPages(filterMenu,wrapper=PageDesc.Wrapper("<p>","</p>"))
            else:
                yield from MultiPageExcerptList(basePage,relevantExcerpts,formatter)
        else:
            yield from MultiPageExcerptList(basePage,relevantExcerpts,formatter)

def TeacherPages(teacherPageDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Yield a page for each individual teacher"""
    
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
        relevantExcerpts = list(Filter.Apply(xDB,Filter.Teacher(t)))
    
        a = Airium()
        
        excerptInfo = ExcerptDurationStr(relevantExcerpts,False,False)
        teacherPageData[t] = excerptInfo
        a(excerptInfo)
        a.hr()

        formatter = Formatter()
        formatter.headingShowTags = False
        formatter.headingShowTeacher = False
        formatter.excerptOmitSessionTags = False
        formatter.excerptDefaultTeacher = set([t])

        pageInfo = PageDesc.PageInfo(tInfo["fullName"],Utils.PosixJoin(teacherPageDir,tInfo["htmlFile"]))
        basePage = PageDesc.PageDesc(pageInfo)
        basePage.AppendContent(str(a))

        if len(relevantExcerpts) >= gOptions.minSubsearchExcerpts:

            filterMenu = [
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.PassAll,formatter,pageInfo,"All excerpts"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.Teacher(t,category="Questions"),formatter,pageInfo,"Questions","question"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.Teacher(t,category="Stories"),formatter,pageInfo,"Stories","story"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.Teacher(t,category="Quotes"),formatter,pageInfo,"Quotes","quote"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.Teacher(t,category="Meditations"),formatter,pageInfo,"Meditations","meditation"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.Teacher(t,category="Teachings"),formatter,pageInfo,"Teachings","teaching"),
            ]

            filterMenu = [f for f in filterMenu if f] # Remove blank menu items
            yield from basePage.AddMenuAndYieldPages(filterMenu,wrapper=PageDesc.Wrapper("<p>","</p>"))
        else:
            yield from MultiPageExcerptList(basePage,relevantExcerpts,formatter)

def TeacherDescription(teacher: dict) -> str:
    if "teachers" in gOptions.buildOnly:
        href = PageDesc.Wrapper(f"<a href = {TeacherLink(teacher['teacher'])}>","</a>")
    else:
        href = PageDesc.Wrapper()
    return f"<p> {href.Wrap(teacher['fullName'])} ({teacher['excerptCount']}) </p>"

def ListTeachersChronological(teachers: list[dict]) -> str:
    """Return html code listing these teachers by group and chronologically."""
    
    groups = list(gDatabase["group"])
    chronological = sorted(teachers,key=lambda t: float(t["sortBy"]) if t["sortBy"] else 9999)
    chronological.sort(key=lambda t: groups.index(t["group"]))
    return str(PageDesc.ListWithHeadings(chronological,lambda t: (t["group"],TeacherDescription(t)) ))

def ListTeachersLineage(teachers: list[dict]) -> str:
    """Return html code listing teachers by lineage."""
    
    lineages = list(gDatabase["lineage"])
    hasLineage = [t for t in teachers if t["lineage"]]
    hasLineage.sort(key=lambda t: float(t["sortBy"]) if t["sortBy"] else 9999)
        # NOTE: We will sort by teacher date once this information gets into the spreadsheet
    hasLineage.sort(key=lambda t: lineages.index(t["lineage"]))
    return str(PageDesc.ListWithHeadings(hasLineage,lambda t: (t["lineage"],TeacherDescription(t)) ))

def ListTeachersByExcerpts(teachers: list[dict]) -> str:
    """Return html code listing teachers by lineage."""
    
    sortedByExcerpts = sorted(teachers,key=lambda t: t["excerptCount"],reverse=True)
    return "\n".join(TeacherDescription(t) for t in sortedByExcerpts)

def TeacherMenu(indexDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Create the Teacher menu item and its associated submenus."""

    chronologicalInfo = PageDesc.PageInfo("Chronological",Utils.PosixJoin(indexDir,"TeachersChronological.html"),"Teachers – Chronological")
    lineageInfo = PageDesc.PageInfo("Lineage",Utils.PosixJoin(indexDir,"TeachersLineage.html"),"Teachers – Monastics by lineage")
    excerptInfo = PageDesc.PageInfo("Number of teachings",Utils.PosixJoin(indexDir,"TeachersByExcerpts.html"),"Teachers – By number of teachings")

    yield chronologicalInfo._replace(title="Teachers")

    teachersInUse = [t for t in gDatabase["teacher"].values() if t["excerptCount"]]

    teacherMenu = [
        [chronologicalInfo,ListTeachersChronological(teachersInUse)],
        [lineageInfo,ListTeachersLineage(teachersInUse)],
        [excerptInfo,ListTeachersByExcerpts(teachersInUse)],
        TeacherPages("teachers")
    ]

    baseTagPage = PageDesc.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(teacherMenu,menuSection = "subMenu")


def EventPages(eventPageDir: str) -> Iterator[PageDesc.PageAugmentorType]:
    """Generate html for each event in the database"""
            
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
        
        if eventInfo["website"]:
            with a.a(href = eventInfo["website"]):
                a("External website")
            a.br()
        
        if len(sessions) > 1:
            squish = Airium(source_minify = True) # Temporarily eliminate whitespace in html code to fix minor glitches
            squish("Sessions:")
            for s in sessions:
                squish(4*"&nbsp")
                with squish.a(href = f"#{Utils.ItemCode(s)}"):
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

        yield (PageDesc.PageInfo(eventInfo["title"],Utils.PosixJoin(eventPageDir,eventCode+'.html'),titleInBody),str(a))
        
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

def AboutMenu(aboutDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Read markdown pages from documentation/about, convert them to html, and create a menu out of them. """

    titleInPage = "The Ajahn Pasanno Question and Story Archive"
    homepageFile = PageDesc.PageInfo("About","homepage.html",titleInPage)
    yield homepageFile

    aboutMenu = []
    documentationDir = "documentation/about"

    firstFile = True
    for fileName in sorted(os.listdir(documentationDir)):
        fullPath = Utils.PosixJoin(documentationDir,fileName)
        if not os.path.isfile(fullPath) or not fileName.endswith(".md"):
            continue
        
        with open(fullPath,encoding='utf8') as file:
            html = markdown.markdown(file.read())
        
        html = re.sub(r"&lt;--!HTML(.*?)--&gt;",r"\1",html) 
        # Markdown converts html comment '<--!' to '&lt;--!, so we search for that.

        if firstFile:
            fileInfo = homepageFile
            firstFile = False
        else:
            m = re.match(r"[0-9]*_([^.]*)",fileName)
            fileInfo = PageDesc.PageInfo(m[1].replace("-"," "),Utils.PosixJoin(aboutDir,m[0] + ".html"),titleInPage)
            firstFile = False
        
        """titleMatch = re.search(r"&lt;--!TITLE:(.*?)--&gt;",html)
        if titleMatch:
            fileInfo = fileInfo._replace(titleIB = titleMatch[1]) - Unused code to read title from the page body """
        
        html = re.sub(r"&lt;--!(.*?)--&gt;","",html) # Remove any remaining html comments

        aboutMenu.append([fileInfo,html])
    
    baseTagPage = PageDesc.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(aboutMenu)

    """tagMenu.append(TagHierarchyMenu(indexDir,drilldownDir))
    tagMenu.append(SortedHtmlTagList("indexes"))
    tagMenu.append(TagPages("tags"))

    baseTagPage = PageDesc.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(tagMenu,menuSection = "subMenu")"""

def TagHierarchyMenu(indexDir:str, drilldownDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Create a submentu for the tag drilldown pages."""
    
    drilldownTitle = "Tag/subtag hierarchy"
    drilldownItem = PageDesc.PageInfo(drilldownTitle,drilldownDir,drilldownTitle)
    contractAllItem = drilldownItem._replace(file=Utils.PosixJoin(drilldownDir,DrilldownPageFile(-1)))
    expandAllItem = drilldownItem._replace(file=Utils.PosixJoin(indexDir,"AllTagsExpanded.html"))

    if "drilldown" in gOptions.buildOnly:
        yield contractAllItem
    else:
        yield expandAllItem

    drilldownMenu = []
    if "drilldown" in gOptions.buildOnly:
        drilldownMenu.append([contractAllItem._replace(title="Contract all"),(contractAllItem,IndentedHtmlTagList(expandSpecificTags=set(),expandTagLink=DrilldownPageFile))])
    drilldownMenu.append([expandAllItem._replace(title="Expand all"),(expandAllItem,IndentedHtmlTagList(expandDuplicateSubtags=True))])
    if "drilldown" in gOptions.buildOnly:
        drilldownMenu.append(DrilldownTags(drilldownItem))

    basePage = PageDesc.PageDesc()
    yield from basePage.AddMenuAndYieldPages(drilldownMenu,wrapper=PageDesc.Wrapper("<p>","</p><hr>"))

def TagMenu(indexDir: str) -> PageDesc.PageDescriptorMenuItem:
    """Create the Tags menu item and its associated submenus.
    Also write a page for each tag."""

    drilldownDir = "drilldown"
    yield next(iter(TagHierarchyMenu(indexDir,drilldownDir)))._replace(title="Tags")

    tagMenu = []
    tagMenu.append(TagHierarchyMenu(indexDir,drilldownDir))
    tagMenu.append(SortedHtmlTagList("indexes"))
    tagMenu.append(TagPages("tags"))

    baseTagPage = PageDesc.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(tagMenu,menuSection = "subMenu")

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')
    parser.add_argument('--globalTemplate',type=str,default='prototype/templates/Global.html',help='Template for all pages; Default: prototype/templates/Global.html')
    parser.add_argument('--buildOnly',type=str,default='',help='Build only specified sections. Set of Tags,Drilldown,Events,Teachers,AllExcerpts.')
    parser.add_argument('--audioLinks',type=str,default='chip',help='Options: img (simple image), audio (html 5 audio player), chip (new interface by Owen)')
    parser.add_argument('--excerptsPerPage',type=int,default=100,help='Maximum excerpts per page')
    parser.add_argument('--minSubsearchExcerpts',type=int,default=10,help='Create subsearch pages for pages with at least this many excerpts.')  
    parser.add_argument('--attributeAll',action='store_true',help="Attribute all excerpts; mostly for debugging")
    parser.add_argument('--maxPlayerTitleLength',type=int,default = 30,help="Maximum length of title tag for chip audio player.")
    parser.add_argument('--keepOldHtmlFiles',action='store_true',help="Keep old html files from previous runs; otherwise delete them")

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def ParseBuildSections():
    if type(gOptions.buildOnly) == set:
        return
    allSections = {"tags","drilldown","events","teachers","allexcerpts"}
    if gOptions.buildOnly == "":
        gOptions.buildOnly = allSections
    elif gOptions.buildOnly.lower() == "none":
        gOptions.buildOnly = set()
    else:
        gOptions.buildOnly = set(section.strip().lower() for section in gOptions.buildOnly.split(','))
        if "drilldown" in gOptions.buildOnly:
            gOptions.buildOnly.add("tags")
        unknownSections = gOptions.buildOnly.difference(allSections)
        if unknownSections:
            Alert.warning.Show(f"--buildOnly: Unrecognized section(s) {unknownSections} will be ignored.")
            gOptions.buildOnly = gOptions.buildOnly.difference(unknownSections)
    
    if gOptions.buildOnly != allSections:
        if gOptions.buildOnly:
            Alert.warning.Show(f"Building only section(s) {gOptions.buildOnly}. This should be used only for testing and debugging purposes.")
        else:
            Alert.warning.Show(f"No sections built. This should be used only for testing and debugging purposes.")

def main():
    if not os.path.exists(gOptions.prototypeDir):
        os.makedirs(gOptions.prototypeDir)
    
    # WriteIndentedTagDisplayList(Utils.PosixJoin(gOptions.prototypeDir,"TagDisplayList.txt"))
    ParseBuildSections()

    basePage = PageDesc.PageDesc()

    indexDir ="indexes"
    mainMenu = []
    mainMenu.append(AboutMenu("about"))
    if "tags" in gOptions.buildOnly:
        mainMenu.append(TagMenu(indexDir))
    if "events" in gOptions.buildOnly:
        mainMenu.append(EventsMenu(indexDir))
    if "teachers" in gOptions.buildOnly:
        mainMenu.append(TeacherMenu("teachers"))
    if "allexcerpts" in gOptions.buildOnly:
        mainMenu.append(AllExcerpts(indexDir))

    for newPage in basePage.AddMenuAndYieldPages(mainMenu,menuSection="mainMenu"):
        WritePage(newPage)

    if not gOptions.keepOldHtmlFiles:
        DeleteUnwrittenHtmlFiles()
    