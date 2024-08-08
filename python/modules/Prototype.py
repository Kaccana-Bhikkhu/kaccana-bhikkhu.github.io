"""A module to create various prototype versions of the website for testing purposes"""

from __future__ import annotations

import os
from typing import List, Iterator, Iterable, Tuple, Callable
from airium import Airium
import Database
import Utils, Alert, Filter, ParseCSV, Document, Render
import Html2 as Html
from datetime import datetime,timedelta
import re, copy, itertools
import pyratemp, markdown
from markdown_newtab_remote import NewTabRemoteExtension
from functools import lru_cache
from typing import NamedTuple, Generator
from collections import defaultdict, Counter
import itertools
import FileRegister
import urllib.parse

MAIN_MENU_STYLE = dict(menuSection="mainMenu")
SUBMENU_STYLE = dict(menuSection="subMenu")
BASE_MENU_STYLE = dict(separator="\n"+6*" ",highlight={"class":"active"})
MAIN_MENU_STYLE |= BASE_MENU_STYLE
SUBMENU_STYLE |= BASE_MENU_STYLE
EXTRA_MENU_STYLE = BASE_MENU_STYLE | dict(wrapper=Html.Tag("div",{"class":"sublink2"}) + "\n<hr>\n")

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

def WritePage(page: Html.PageDesc,writer: FileRegister.HashWriter) -> None:
    """Write an html file for page using the global template"""
    page.gOptions = gOptions

    template = Utils.PosixJoin(gOptions.prototypeDir,gOptions.globalTemplate)
    if page.info.file.endswith("_print.html"):
        template = Utils.AppendToFilename(template,"_print")
    pageHtml = page.RenderWithTemplate(template)
    writer.WriteTextFile(page.info.file,pageHtml)

def DeleteUnwrittenHtmlFiles(writer: FileRegister.HashWriter) -> None:
    """Remove old html files from previous runs to keep things neat and tidy."""

    # Delete files only in directories we have built
    dirs = gOptions.buildOnly & {"events","tags","teachers","drilldown","search"}
    dirs.add("about")
    if gOptions.buildOnly == gAllSections:
        dirs.add("indexes")

    deletedFiles = 0
    for dir in dirs:
        deletedFiles += writer.DeleteUnregisteredFiles(dir,filterRegex=r".*\.html$")
    if deletedFiles:
        Alert.extra(deletedFiles,"html file(s) deleted.")

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

def HtmlTagLink(tag:str, fullTag: bool = False,text:str = "",link = True) -> str:
    """Turn a tag name into a hyperlink to that tag.
    Simplying assumption: All html pages (except homepage.html and index.html) are in a subdirectory of prototype.
    Thus ../tags will reference the tags directory from any other html pages.
    If fullTag, the link text contains the full tag name."""
    
    try:
        ref = gDatabase["tag"][tag]["htmlFile"]
        if fullTag:
            tag = gDatabase["tag"][tag]["fullTag"]
    except KeyError:
        ref = gDatabase["tag"][gDatabase["tagSubsumed"][tag]["subsumedUnder"]]["htmlFile"]
    
    if not text:
        text = tag
    if link:
        splitItalics = text.split("<em>")
        if len(splitItalics) > 1:
            textOutsideLink = " <em>" + splitItalics[1]
        else:
            textOutsideLink = ""
        return f'<a href = "../tags/{ref}">{splitItalics[0].strip()}</a>{textOutsideLink}'
    else:
        return text


def ListLinkedTags(title:str, tags:List[str],*args,**kwargs) -> str:
    "Write a list of hyperlinked tags"
    
    linkedTags = [HtmlTagLink(tag) for tag in tags]
    return TitledList(title,linkedTags,*args,**kwargs)

gAllTeacherRegex = ""
def LinkTeachersInText(text: str,specificTeachers:Iterable[str] = ()) -> str:
    """Search text for the names of teachers with teacher pages and add hyperlinks accordingly."""

    global gAllTeacherRegex
    if not gAllTeacherRegex:
        gAllTeacherRegex = Utils.RegexMatchAny(t["attributionName"] for t in gDatabase["teacher"].values() if t["htmlFile"])
    
    if specificTeachers:
        teacherRegex = Utils.RegexMatchAny(t["attributionName"] for t in gDatabase["teacher"].values() if t["htmlFile"])
    else:
        teacherRegex = gAllTeacherRegex

    def HtmlTeacherLink(matchObject: re.Match) -> str:
        teacher = Database.TeacherLookup(matchObject[1])
        htmlFile = TeacherLink(teacher)
        return f'<a href="{htmlFile}">{matchObject[1]}</a>'

    return re.sub(teacherRegex,HtmlTeacherLink,text)


def ListLinkedTeachers(teachers:List[str],*args,**kwargs) -> str:
    """Write a list of hyperlinked teachers.
    teachers is a list of abbreviated teacher names"""
    
    fullNameList = [gDatabase["teacher"][t]["attributionName"] for t in teachers]
    
    return LinkTeachersInText(ItemList(fullNameList,*args,**kwargs))

def ExcerptCount(tag:str) -> int:
    return gDatabase["tag"][tag].get("excerptCount",0)

def IndentedHtmlTagList(tagList:list[dict] = [],expandSpecificTags:set[int]|None = None,expandDuplicateSubtags:bool = True,expandTagLink:Callable[[int],str]|None = None,showSubtagCount = True) -> str:
    """Generate html for an indented list of tags.
    tagList is the list of tags to print; use the global list if not provided
    If expandSpecificTags is specified, then expand only tags with index numbers in this set.
    If not, then expand all tags if expandDuplicateSubtags; otherwise expand only tags with primary subtags.
    If expandTagLink, add boxes to expand and contract each tag with links given by this function."""
    
    tabMeasurement = 'em'
    tabLength = 2
    
    a = Airium()
    
    if not tagList:
        tagList = gDatabase["tagDisplayList"]
    if expandSpecificTags is None:
        if expandDuplicateSubtags:
            expandSpecificTags = range(len(tagList))
        else:
            expandSpecificTags = set()
            for parent,children in ParseCSV.WalkTags(tagList,returnIndices=True):
                for n in children:
                    tag = tagList[n]["tag"]
                    if n in expandSpecificTags or (tag and gDatabase["tag"][tag]["listIndex"] == n): # If this is a primary tag
                        expandSpecificTags.add(parent) # Then expand the parent tag
    
    baseIndent = tagList[0]["level"]
    skipSubtagLevel = 999 # Skip subtags indented more than this value; don't skip any to start with
    with a.div(Class="listing"):
        for index, item in enumerate(tagList):
            #print(index,item["name"])
            if item["level"] > skipSubtagLevel:
                continue

            if index in expandSpecificTags:
                skipSubtagLevel = 999 # don't skip anything
            else:
                skipSubtagLevel = item["level"] # otherwise skip tags deeper than this level
            
            bookmark = Utils.slugify(item["tag"] or item["name"])
            with a.p(id = bookmark,style = f"margin-left: {tabLength * (item['level']-baseIndent)}{tabMeasurement};"):
                drilldownLink = ''
                if expandTagLink:
                    if index < len(tagList) - 1 and tagList[index + 1]["level"] > item["level"]: # Can the tag be expanded?
                        if index in expandSpecificTags: # Is it already expanded?
                            tagAtPrevLevel = -1
                            for reverseIndex in range(index - 1,-1,-1):
                                if tagList[reverseIndex]["level"] < item["level"]:
                                    tagAtPrevLevel = reverseIndex
                                    break
                            drilldownLink = f'<a href="../drilldown/{expandTagLink(tagAtPrevLevel)}#_keep_scroll"><i class="fa fa-minus-square"></i></a>'
                        else:
                            drilldownLink = f'<a href="../drilldown/{expandTagLink(index)}#_keep_scroll"><i class="fa fa-plus-square"></i></a>'
                    else:
                        drilldownLink = "&nbsp"

                indexStr = item["indexNumber"] + "." if item["indexNumber"] else ""
                
                subtagExcerptCount = showSubtagCount and item.get("subtagExcerptCount",0)
                if item["excerptCount"] or subtagExcerptCount:
                    if subtagExcerptCount:
                        itemCount = item["excerptCount"]
                        if not item['tag']:
                            itemCount = "-"
                        countStr = f' ({itemCount}/{subtagExcerptCount})'
                    else:
                        countStr = f' ({item["excerptCount"]})'
                else:
                    countStr = ""
                
                if item['tag'] and not item['subsumed']:
                    nameStr = HtmlTagLink(item['tag'],True) + countStr
                else:
                    nameStr = item['name'] + ("" if item["subsumed"] else countStr)
                
                if item['pali'] and item['pali'] != item['name']:
                    paliStr = '(' + item['pali'] + ')'
                elif ParseCSV.TagFlag.DISPLAY_GLOSS in item['flags']:
                    paliStr = '(' + gDatabase['tag'][item['tag']]['glosses'][0] + ')'
                    # If specified, use paliStr to display the tag's first gloss
                else:
                    paliStr = ''
                
                if item['subsumed']:
                    seeAlsoStr = 'see ' + HtmlTagLink(item['tag'],False) + countStr
                else:
                    seeAlsoStr = ''
                
                joinBits = [s for s in [drilldownLink,indexStr,nameStr,paliStr,seeAlsoStr] if s]
                a(' '.join(joinBits))
    
    return str(a)

def DrilldownPageFile(tagNumberOrName: int|str,jumpToEntry:bool = False) -> str:
    """Return the name of the page that has this tag expanded.
    The tag can be specified by number in the hierarchy or by name."""

    if type(tagNumberOrName) == str:
        tagNumber = gDatabase["tag"][tagNumberOrName]["listIndex"]
    else:
        tagNumber = tagNumberOrName

    indexStr = ""
    if tagNumber >= 0:
        tagList = gDatabase["tagDisplayList"]
        ourLevel = tagList[tagNumber]["level"]
        if tagNumber + 1 >= len(tagList) or tagList[tagNumber + 1]["level"] <= ourLevel:
            # If this tag doesn't have subtags, find its parent tag
            if ourLevel > 1:
                while tagList[tagNumber]["level"] >= ourLevel:
                    tagNumber -= 1
        
        tagName = tagList[tagNumber]["tag"]
        displayName = tagName or tagList[tagNumber]["name"]
        fileName = Utils.slugify(displayName) + ".html"
        if tagName and gDatabase["tag"][tagName]["listIndex"] != tagNumber:
            # If this is not a primary tag, append an index number to it
            indexStr = "-" + str(sum(1 for n in range(tagNumber) if tagList[n]["tag"] == tagName))
            fileName = Utils.AppendToFilename(fileName,indexStr)
    else:
        fileName = "root.html"

    if jumpToEntry:
        fileName += f"#{fileName.replace('.html','')}"
    return fileName

def DrilldownIconLink(tag: str,iconWidth = 20):
    drillDownPage = "../drilldown/" + DrilldownPageFile(gDatabase["tag"][tag]["listIndex"],jumpToEntry=True)
    return Html.Tag("a",dict(href=drillDownPage,title="Show in tag hierarchy"))(Html.Tag("img",dict(src="../assets/text-bullet-list-tree.svg",width=iconWidth)).prefix)

def DrilldownTags(pageInfo: Html.PageInfo) -> Iterator[Html.PageAugmentorType]:
    """Write a series of html files to create a hierarchial drill-down list of tags."""

    tagList = gDatabase["tagDisplayList"]

    for n,tag in enumerate(tagList):
        if (n + 1 < len(tagList) and tagList[n+1]["level"] > tag["level"]) or tag["level"] == 1: # If the next tag is deeper, then we can expand this one
            tagsToExpand = {n}
            reverseIndex = n - 1
            nextLevelToExpand = tag["level"] - 1
            while reverseIndex >= 0 and nextLevelToExpand > 0:
                if tagList[reverseIndex]["level"] <= nextLevelToExpand:
                    tagsToExpand.add(reverseIndex)
                    nextLevelToExpand = tagList[reverseIndex]["level"] - 1
                reverseIndex -= 1
            
            page = Html.PageDesc(pageInfo._replace(file=Utils.PosixJoin(pageInfo.file,DrilldownPageFile(n))))
            page.keywords.append(tag["name"])
            page.AppendContent(IndentedHtmlTagList(expandSpecificTags=tagsToExpand,expandTagLink=DrilldownPageFile))
            page.specialJoinChar["citationTitle"] = ""
            page.AppendContent(f': {tag["name"]}',section="citationTitle")
            yield page

def TagDescription(tag: dict,fullTag:bool = False,style: str = "tagFirst",listAs: str = "",link = True,drilldownLink = False) -> str:
    "Return html code describing this tag."
    
    xCount = tag.get("excerptCount",0)
    countStr = f' ({xCount})' if xCount > 0 else ''
    
    if not listAs and fullTag:
        listAs = tag["fullTag"]
    tagStr = HtmlTagLink(tag['tag'],fullTag,text = listAs,link=link)

    paliStr = ''
    if tag['pali'] and tag['pali'] != tag['tag']:
        if fullTag:
            paliStr = '(' + tag['fullPali'] + ')'
        else:
            paliStr = '(' + tag['pali'] + ')'
    elif ParseCSV.TagFlag.DISPLAY_GLOSS in tag["flags"]:
        if tag['glosses']:
            paliStr = '(' + tag['glosses'][0] + ')'
        else:
            Alert.caution(tag,"has flag g: DISPLAY_GLOSS but has no glosses.")
    
    if drilldownLink:
        tagStr = DrilldownIconLink(tag["tag"],iconWidth = 12) + " " + tagStr

    if style == "tagFirst":
        return ' '.join([tagStr,paliStr,countStr])
    elif style == "numberFirst":
        return ' '.join([countStr,tagStr,paliStr])
    elif style == "noNumber":
        return ' '.join([tagStr,paliStr])
    elif style == "noPali":
        return ' '.join([tagStr,countStr])

def NumericalTagList(pageDir: str) -> Html.PageDescriptorMenuItem:
    """Write a list of numerical tags sorted by number:
    i.e. Three Refuges, Four Noble Truths, Five Faculties."""

    info = Html.PageInfo("Numerical",Utils.PosixJoin(pageDir,"NumericalTags.html"),"Tags – Numerical")
    yield info
    
    numericalTags = [tag for tag in gDatabase["tag"].values() if tag["number"]]
    numericalTags.sort(key=lambda t: int(t["number"]))

    spaceAfter = {tag1["tag"] for tag1,tag2 in itertools.pairwise(numericalTags) if tag1["number"] == tag2["number"]}
        # Tags which are followed by a tag having the same number should have a space after them

    numberNames = {3:"Threes", 4:"Fours", 5:"Fives", 6:"Sixes", 7:"Sevens", 8:"Eights",
                   9:"Nines", 10:"Tens", 12: "Twelves", 37:"Thiry-sevens"}
    def SubtagList(tag: dict) -> tuple[str,str,str]:
        number = int(tag["number"])
        numberName = numberNames[number]

        fullList = gDatabase["tagDisplayList"]
        baseIndex = tag["listIndex"]
        tagList = [fullList[baseIndex]]
        baseLevel = tagList[0]["level"]

        index = baseIndex + 1
        addedNumberedTag = False
        while index < len(fullList) and fullList[index]["level"] > baseLevel:
            curTag = fullList[index]
            if curTag["level"] == baseLevel + 1:
                if curTag["indexNumber"] or not addedNumberedTag:
                    tagList.append(curTag)
                    if curTag["indexNumber"]:
                        addedNumberedTag = True
            index += 1

        storedNumber = tagList[0]["indexNumber"]
        tagList[0]["indexNumber"] = ""    # Temporarily remove any digit before the first entry.
        content = IndentedHtmlTagList(tagList,showSubtagCount=False)
        tagList[0]["indexNumber"] = storedNumber

        content = content.replace('style="margin-left: 0em;">','style="margin-left: 0em; font-weight:bold;">')
            # Apply boldface to the top line only
        content = re.sub(r"(\s+)</p>",r":\1</p>",content,count = 1)
            # Add a colon at the end of the first paragraph only.
        if tag["tag"] in spaceAfter:
            content += "\n<br>"
        return numberName,content,numberName.lower()

    pageContent = Html.ListWithHeadings(numericalTags,SubtagList,headingWrapper = Html.Tag("h2",dict(id="HEADING_ID")))

    page = Html.PageDesc(info)
    page.AppendContent(pageContent)
    page.AppendContent("Numerical tags",section="citationTitle")
    page.keywords = ["Tags","Numerical tags"]
    yield page 

def MostCommonTagList(pageDir: str) -> Html.PageDescriptorMenuItem:
    """Write a list of tags sorted by number of excerpts."""
    
    info = Html.PageInfo("Most common",Utils.PosixJoin(pageDir,"SortedTags.html"),"Tags – Most common")
    yield info

    a = Airium()
    # Sort descending by number of excerpts and in alphabetical order
    tagsSortedByQCount = sorted((tag for tag in gDatabase["tag"] if ExcerptCount(tag)),key = lambda tag: (-ExcerptCount(tag),tag))
    with a.div(Class="listing"):
        for tag in tagsSortedByQCount:
            with a.p():
                a(TagDescription(gDatabase["tag"][tag],fullTag=True,style="numberFirst",drilldownLink=True))
    
    page = Html.PageDesc(info)
    page.AppendContent(str(a))
    page.AppendContent("Most common tags",section="citationTitle")
    page.keywords = ["Tags","Most common tags"]
    yield page

def ProperNounTag(tag:dict) -> bool:
    """Return true if this tag is a proper noun.
    Tag is a tag dict object."""
    return ParseCSV.TagFlag.PROPER_NOUN in tag["flags"] or (tag["supertags"] and ParseCSV.TagFlag.PROPER_NOUN_SUBTAGS in gDatabase["tag"][tag["supertags"][0]]["flags"])

class _Alphabetize(NamedTuple):
    "Helper tuple to alphabetize a list."
    sortBy: str
    html: str
def Alphabetize(sortBy: str,html: str) -> _Alphabetize:
    return _Alphabetize(Utils.RemoveDiacritics(sortBy).lower(),html)

def LanguageTag(tagString: str) -> str:
    "Return lang (lowercase, no diacritics) when tagString matches <em>LANG</em>. Otherwise return an empty string."
    tagString = Utils.RemoveDiacritics(tagString).lower()
    match = re.search(r"<em>([^<]*)</em>$",tagString)
    if match:
        return match[1]
    else:
        return ""

def RemoveLanguageTag(tagString: str) -> str:
    "Return tagString with any language tag removed."
    return re.sub(r"<em>([^<]*)</em>$","",tagString).strip()

def AlphabeticalTagList(pageDir: str) -> Html.PageDescriptorMenuItem:
    """Write a list of tags sorted alphabetically."""
    
    pageInfo = Html.PageInfo("Alphabetical",Utils.PosixJoin(pageDir,"AlphabeticalTags.html"),"Tags – Alphabetical")
    yield pageInfo

    prefixes = sorted(list(gDatabase["prefix"]),key=len,reverse=True)
        # Sort prefixes so the longest prefix matches first
    prefixes = [p if p.endswith("/") else p + " " for p in prefixes]
        # Add a space to each prefix that doesn't end with "/"
    slashPrefixes = Utils.RegexMatchAny(p for p in prefixes if p.endswith("/"))
    prefixRegex = Utils.RegexMatchAny(prefixes,capturingGroup=True) + r"(.+)"
    noAlphabetize = {"alphabetize":""}
    def AlphabetizeName(string: str) -> str:
        if gDatabase["name"].get(string,noAlphabetize)["alphabetize"]:
            return gDatabase["name"][string]["alphabetize"]
        match = re.match(prefixRegex,string)
        if match:
            return match[2] + ", " + match[1].strip(" /")
        else:
            return string

    def EnglishEntry(tag: dict,tagName: str,fullTag:bool=False,drilldownLink = True) -> _Alphabetize:
        "Return an entry for an English item in the alphabetized list"
        tagName = AlphabetizeName(tagName)
        html = TagDescription(tag,fullTag=fullTag,listAs=tagName,drilldownLink=drilldownLink)
        return Alphabetize(tagName,html)

    def NonEnglishEntry(tag: dict,fullTag:bool = False,drilldownLink = True) -> _Alphabetize:
        count = tag.get('excerptCount',0)
        countStr = f" ({count})" if count else ""
        if fullTag:
            text = tag["fullPali"]
        else:
            text = tag["pali"]
        html = f"{text} [{HtmlTagLink(tag['tag'],fullTag)}]{countStr}"
        if drilldownLink:
            html = DrilldownIconLink(tag["tag"],iconWidth = 12) + " " + html
        return Alphabetize(text,html)

    entries = defaultdict(list)
    for tag in gDatabase["tag"].values():
        if not tag["htmlFile"] or ParseCSV.TagFlag.HIDE in tag["flags"]:
            continue

        nonEnglish = tag["tag"] == tag["pali"]
        properNoun = ProperNounTag(tag)
        englishAlso = ParseCSV.TagFlag.ENGLISH_ALSO in tag["flags"]
        hasPali = tag["pali"] and not LanguageTag(tag["fullPali"])
            # Non-Pāli language full tags end in <em>LANGUAGE</em>

        if nonEnglish: # If this tag has no English entry, add it to the appropriate language list and go on to the next tag
            entry = EnglishEntry(tag,tag["fullPali"],fullTag=False)
            if hasPali:
                if ParseCSV.TagFlag.CAPITALIZE not in tag["flags"]:
                    entry = entry._replace(html=entry.html.lower())
                    # Pali words are in lowercase unless specifically capitalized
                entries["pali"].append(entry)
            else:
                entries["other"].append(entry)
            if properNoun:
                entries["proper"].append(entry) # Non-English proper nouns are listed here as well
            if englishAlso:
                entries["english"].append(entry)
        else:
        
            if properNoun:
                entries["proper"].append(EnglishEntry(tag,tag["fullTag"],fullTag=True))
                if englishAlso:
                    entries["english"].append(entry)
            else:
                entries["english"].append(EnglishEntry(tag,tag["fullTag"],fullTag=True))
                if not AlphabetizeName(tag["fullTag"]).startswith(AlphabetizeName(tag["tag"])):
                    entries["english"].append(EnglishEntry(tag,tag["tag"]))
                    # File the abbreviated tag separately if it's not a simple truncation
            
            if re.match(slashPrefixes,tag["fullTag"]):
                entries["english"].append(Alphabetize(tag["fullTag"],TagDescription(tag,fullTag=True)))
                # Alphabetize tags like History/Thailand under History/Thailand as well as Thailand, History

            if tag["pali"]: # Add an entry for foriegn language items
                entry = NonEnglishEntry(tag)
                if hasPali:
                    entries["pali"].append(entry)
                else:
                    entries["other"].append(entry)
                if englishAlso:
                    entries["english"].append(entry)
            if tag["fullPali"] and tag["fullPali"] != tag["pali"]: # Add an entry for the full Pāli tag
                entry = NonEnglishEntry(tag,fullTag=True)
                if hasPali:
                    entries["pali"].append(entry)
                else:
                    entries["other"].append(entry)
            
            for translation in tag["alternateTranslations"]:
                html = f"{translation} – alternative translation of {NonEnglishEntry(tag,fullTag=True,drilldownLink=False).html}"
                if LanguageTag(translation):
                    entries["other"].append(Alphabetize(translation,html))
                else:
                    entries["english"].append(Alphabetize(translation,html))
            
        for gloss in tag["glosses"]:
            gloss = AlphabetizeName(gloss)
            paliGloss = LanguageTag(gloss) == "pali"
            if not paliGloss or properNoun: # Pali is listed in lowercase
                gloss = gloss[0].capitalize() + gloss[1:]
            if paliGloss:
                gloss = RemoveLanguageTag(gloss)
                
            html = f"{gloss} – see {TagDescription(tag,fullTag=True)}"
            if paliGloss:
                entries["pali"].append(Alphabetize(gloss,html))
            elif LanguageTag(gloss):
                entries["other"].append(Alphabetize(gloss,html))
            else:
                entries["english"].append(Alphabetize(gloss,html))
            if properNoun:
                entries["proper"].append(Alphabetize(gloss,html))
    
    for subsumedTag in gDatabase["tagSubsumed"].values():
        if ParseCSV.TagFlag.HIDE in subsumedTag["flags"]:
            continue

        subsumedUnder = gDatabase["tag"][subsumedTag["subsumedUnder"]]
        referenceText = f" – see {TagDescription(subsumedUnder,fullTag=True)}"
        
        if subsumedTag["tag"] != subsumedTag["pali"]:
            entries["english"].append(Alphabetize(subsumedTag["fullTag"],TagDescription(subsumedTag,fullTag = True,link = False) + referenceText))
            if not AlphabetizeName(subsumedTag["fullTag"]).startswith(AlphabetizeName(subsumedTag["tag"])):
                # File the abbreviated tag separately if it's not a simple truncation
                entries["english"].append(Alphabetize(subsumedTag["tag"],TagDescription(subsumedTag,fullTag = False,link = False) + referenceText))
        
        hasPali = subsumedTag["pali"] and not LanguageTag(subsumedTag["fullPali"])
        if subsumedTag["pali"]:
            entry = Alphabetize(subsumedTag["pali"],f"{subsumedTag['pali']} [{subsumedTag['tag']}]{referenceText}")
            if hasPali:
                entries["pali"].append(entry)
            else:
                entries["other"].append(entry)
            
            if subsumedTag["pali"] != subsumedTag["fullPali"]:
                entry = Alphabetize(subsumedTag["fullPali"],f"{subsumedTag['fullPali']} [{subsumedTag['fullTag']}]{referenceText}")
                if hasPali:
                    entries["pali"].append(entry)
                else:
                    entries["other"].append(entry)
        
        for gloss in subsumedTag["glosses"] + subsumedTag["alternateTranslations"]:
            language = LanguageTag(gloss)
            if language:
                if language == "pali":
                    gloss = RemoveLanguageTag(gloss)
                    entries["pali"].append(Alphabetize(gloss,gloss + referenceText))
                else:
                    entries["other"].append(Alphabetize(gloss,gloss + referenceText))
            else:
                entries["english"].append(Alphabetize(gloss,gloss + referenceText))

    def Deduplicate(iterable: Iterable) -> Iterator:
        iterable = iter(iterable)
        prevItem = next(iterable)
        yield prevItem
        for item in iterable:
            if item != prevItem:
                yield item
                prevItem = item

    for e in entries.values():
        e.sort()
    allList = list(Deduplicate(sorted(itertools.chain.from_iterable(entries.values()))))

    def TagItem(line:Alphabetize) -> str:
        return line.sortBy[0].upper(),"".join(("<p>",line.html,"</p>"))

    def LenStr(items: list) -> str:
        return f" ({len(items)})"
    

    args = dict(addMenu=True,countItems=False,bodyWrapper=Html.Tag("div",{"class":"listing"}))
    subMenu = [
        [pageInfo._replace(title = "All tags"+LenStr(allList)),str(Html.ListWithHeadings(allList,TagItem,**args))],
        [pageInfo._replace(title = "English"+LenStr(entries["english"]),file=Utils.PosixJoin(pageDir,"EnglishTags.html")),
            str(Html.ListWithHeadings(entries["english"],TagItem,**args))],
        [pageInfo._replace(title = "Pāli"+LenStr(entries["pali"]),file=Utils.PosixJoin(pageDir,"PaliTags.html")),
            str(Html.ListWithHeadings(entries["pali"],TagItem,**args))],
        [pageInfo._replace(title = "Other languages"+LenStr(entries["other"]),file=Utils.PosixJoin(pageDir,"OtherTags.html")),
            str(Html.ListWithHeadings(entries["other"],TagItem,**args))],
        [pageInfo._replace(title = "People/places/traditions"+LenStr(entries["proper"]),file=Utils.PosixJoin(pageDir,"ProperTags.html")),
            str(Html.ListWithHeadings(entries["proper"],TagItem,**args))]
    ]

    basePage = Html.PageDesc()
    basePage.keywords = ["Tags","Alphabetical"]
    for page in basePage.AddMenuAndYieldPages(subMenu,**EXTRA_MENU_STYLE):
        titleWithoutLength = " ".join(page.info.title.split(" ")[:-1])
        page.keywords.append(titleWithoutLength)
        citation = f"Alphabetical tags: {titleWithoutLength}"

        page.AppendContent(citation,section="citationTitle")
        yield page

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

    filename = title + ".mp3"

    a = Airium(source_minify=True)
    if linkKind == "img":
        a.a(href = hyperlink, title = title, style="text-decoration: none;").img(src = "../images/audio.png",width = iconWidth)
            # text-decoration: none ensures the icon isn't underlined
    elif linkKind == "linkToPlayerPage":
        with a.a(href = hyperlink,title = "Back to player"):
            a('<i class="fa fa-long-arrow-left"></i> Playable')
        a(" "+4*"&nbsp")
        a.a(href = hyperlink,download = filename,title = "Download").img(src="../assets/download.svg",width="15",style="opacity:50%;",alt="⇓ Download")
        a.br()
    elif linkKind == "audio":
        with a.audio(controls = "", src = hyperlink, title = title, preload = preload, style="vertical-align: middle;"):
            with a.a(href = hyperlink,download=filename):
                a(f"Download audio")
            a(f" ({dataDuration})")
        a.br()
    else:
        durationDict = {}
        if dataDuration:
            durationDict = {"data-duration": str(Utils.StrToTimeDelta(dataDuration).seconds)}
        with a.get_tag_('audio-chip')(src = hyperlink, title = title, **durationDict):
            with a.a(href = hyperlink,download=filename):
                a(f"Download audio")
            a(f" ({dataDuration})")
        a.br()
	
    return str(a)

def Mp3ExcerptLink(excerpt: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given excerpt.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
    
    return AudioIcon(Database.Mp3Link(excerpt),title=PlayerTitle(excerpt),dataDuration = excerpt["duration"],**kwArgs)
    
def Mp3SessionLink(session: dict,**kwArgs) -> str:
    """Return an html-formatted audio icon linking to a given session.
    Make the simplifying assumption that our html file lives in a subdirectory of home/prototype"""
        
    return AudioIcon(Database.Mp3Link(session),title=PlayerTitle(session),dataDuration = session["duration"],**kwArgs)
    
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
        self.audioLinks = gOptions.audioLinks
        
        self.excerptDefaultTeacher = set() # Don't print the list of teachers if it matches the items in this list / set
        self.excerptOmitTags = set() # Don't display these tags in excerpt description
        self.excerptBoldTags = set() # Display these tags in boldface
        self.excerptOmitSessionTags = True # Omit tags already mentioned by the session heading
        self.excerptPreferStartTime = False # Display the excerpt start time instead of duration when available
        
        self.showHeading = True # Show headings at all?
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
        
        a(Mp3ExcerptLink(excerpt,linkKind = self.audioLinks,**kwArgs))
        a(' ')
        if excerpt['excerptNumber']:
            with a.b(style="text-decoration: underline;"):
                a(f"{excerpt['excerptNumber']}.")
        else:
            a(f"[{Html.Tag('span',{'style':'text-decoration: underline;'})('Session')}]")

        a(" ")
        if self.excerptPreferStartTime and excerpt['excerptNumber']:
            a(f'[{excerpt["clips"][0].start}] ')
        elif self.audioLinks != "chip":
            a(f'({excerpt["duration"]}) ')

        def ListAttributionKeys() -> Generator[Tuple[str,str]]:
            for num in range(1,10):
                numStr = str(num) if num > 1 else ""
                yield ("attribution" + numStr, "teachers" + numStr)

        bodyWithAttributions = excerpt["body"]
        for attrKey,teacherKey in ListAttributionKeys():
            if attrKey not in excerpt:
                break

            if set(excerpt[teacherKey]) != set(self.excerptDefaultTeacher) or ParseCSV.ExcerptFlag.ATTRIBUTE in excerpt["flags"]: # Compare items irrespective of order
                teacherList = [gDatabase["teacher"][t]["attributionName"] for t in excerpt[teacherKey]]
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
                omitTags = set.union(omitTags,set(Database.FindSession(gDatabase["sessions"],excerpt["event"],excerpt["sessionNumber"])["tags"]))
            
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

        bookmark = Database.ItemCode(session)
        with a.div(Class = "title",id = bookmark):
            if self.headingShowEvent: 
                if self.headingLinks:
                    with (a.a(href = EventLink(session["event"]))):
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

            if linkSessionAudio and (self.audioLinks == "img" or self.audioLinks =="chip"):
                audioLink = Mp3SessionLink(session,linkKind = self.audioLinks)
                if self.audioLinks == "img":
                    durStr = f' ({Utils.TimeDeltaToStr(Utils.StrToTimeDelta(session["duration"]))})' # Pretty-print duration by converting it to seconds and back
                    itemsToJoin.append(audioLink + durStr + ' ')
                else:
                    itemsToJoin[-1] += ' ' + audioLink
                        # The audio chip goes on a new line, so don't separate with a dash
            
            a(' – '.join(itemsToJoin))

            if self.headingShowTags:
                a(' ')
                tagStrings = []
                for tag in session["tags"]:
                    tagStrings.append('[' + HtmlTagLink(tag) + ']')
                a(' '.join(tagStrings))
            
        if linkSessionAudio and self.audioLinks == "audio":
            a(Mp3SessionLink(session,linkKind = self.audioLinks))
            if horizontalRule:
                a.hr()
        
        return str(a)

def ExcerptDurationStr(excerpts: List[dict],countEvents = True,countSessions = True,countSessionExcerpts = False,sessionExcerptDuration = True) -> str:
    "Return a string describing the duration of the excerpts we were passed."
    
    if not excerpts:
        return "No excerpts"
    
    events = set(x["event"] for x in excerpts)
    sessions = set((x["event"],x["sessionNumber"]) for x in excerpts) # Use sets to count unique elements

    duration = timedelta()
    for _,sessionExcerpts in itertools.groupby(excerpts,lambda x: (x["event"],x["sessionNumber"])):
        sessionExcerpts = list(sessionExcerpts)
        duration += sum((Utils.StrToTimeDelta(x["duration"]) for x in sessionExcerpts if x["fileNumber"] or (sessionExcerptDuration and len(sessionExcerpts) == 1)),start = timedelta())
            # Don't sum session excerpts (fileNumber = 0) unless the session excerpt is the only excerpt in the list
            # This prevents confusing results due to double counting times
    
    strItems = []
    
    if len(events) > 1 and countEvents:
        strItems.append(f"{len(events)} events,")
    
    if len(sessions) > 1 and countSessions:
        strItems.append(f"{len(sessions)} sessions,")
    
    excerptCount = len(excerpts) if countSessionExcerpts else sum(1 for x in excerpts if x["fileNumber"])
    if excerptCount > 1:
        strItems.append(f"{excerptCount} excerpts,")
    else:
        strItems.append(f"{excerptCount} excerpt,")
    
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
        if localFormatter.showHeading and (x["event"] != prevEvent or x["sessionNumber"] != prevSession):
            session = Database.FindSession(gDatabase["sessions"],x["event"],x["sessionNumber"])

            linkSessionAudio = formatter.headingAudio and x["fileNumber"]
                # Omit link to the session audio if the first excerpt is a session excerpt with a body that will include it
            hr = x["fileNumber"] or x["body"]
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
        hasMultipleAnnotations = sum(len(a["body"]) > 0 for a in x["annotations"]) > 1
        if x["body"] or (not x["fileNumber"] and hasMultipleAnnotations):
            """ Render blank session excerpts which have more than one annotation as [Session].
                If a blank session excerpt has only one annotation, [Session] will be added below."""
            with a.p(id = Database.ItemCode(x)):
                a(localFormatter.FormatExcerpt(x,**options))
        
        tagsAlreadyPrinted = set(x["tags"])
        for annotation in x["annotations"]:
            if annotation["body"]:
                indentLevel = annotation['indentLevel']
                if not x["fileNumber"] and not x["body"] and not hasMultipleAnnotations:
                    # If a single annotation follows a blank session excerpt, don't indent and add [Session] in front of it
                    indentLevel = 0
                with a.p(style = f"margin-left: {tabLength * indentLevel}{tabMeasurement};"):
                    if not indentLevel:
                        a(f"[{Html.Tag('span',{'style':'text-decoration: underline;'})('Session')}]")
                    a(localFormatter.FormatAnnotation(annotation,tagsAlreadyPrinted))
                tagsAlreadyPrinted.update(annotation.get("tags",()))
        
        if (localFormatter.audioLinks != "img") and x is not lastExcerpt:
            a.hr()
        
    return str(a)

def MultiPageExcerptList(basePage: Html.PageDesc,excerpts: List[dict],formatter: Formatter,itemLimit:int = 0,allItemsPage = False) -> Iterator[Html.PageAugmentorType]:
    """Split an excerpt list into multiple pages, yielding a series of PageAugmentorType objects
        basePage: Content of the page above the menu and excerpt list. Later pages add "-N" to the file name.
        excerpts, formatter: As in HtmlExcerptList
        itemLimit: Limit lists to roughly this many items, but break pages only at session boundaries.
        allItemsPage: Create a page with all items but without audio players that links back to the separate pages."""

    pageNumber = 1
    menuItems = []
    excerptsInThisPage = []
    prevSession = None
    if itemLimit == 0:
        itemLimit = gOptions.excerptsPerPage
    excerptPage:dict[str:str] = {}
        # Keys are the mp3 file name of each excerpt; values are the html file the excerpt is listed in

    def PageHtml() -> Html.PageAugmentorType:
        if pageNumber > 1:
            fileName = Utils.AppendToFilename(basePage.info.file,f"-{pageNumber}")
        else:
            fileName = basePage.info.file
        menuItem = Html.PageInfo(str(pageNumber),fileName,basePage.info.titleInBody)
        pageHtml = HtmlExcerptList(excerptsInThisPage,formatter)

        excerptPage.update((Database.ItemCode(x),fileName) for x in excerptsInThisPage)

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
    
    def LinkToPage(mp3Link:re.Match) -> str:
        htmlPage = excerptPage.get(mp3Link[1],None)
        if htmlPage:
            return f'href="../{htmlPage}#{mp3Link[1]}"'
        else:
            return mp3Link[0]

    if len(menuItems) > 1:
        if allItemsPage:
            noPlayer = copy.deepcopy(formatter)
            noPlayer.audioLinks = "linkToPlayerPage"
            menuItem = Html.PageInfo(basePage.info.title,Utils.AppendToFilename(basePage.info.file,"-all"),basePage.info.titleInBody)
            
            pageHtml = Html.Tag("p")("""Use your browser's find command (Ctrl+F or Cmd+F) to search the excerpt text.<br> Then click <i class="fa fa-long-arrow-left"></i> Playable to return to a page where you can play the excerpt.""") + "\n"
            pageHtml += HtmlExcerptList(excerpts,noPlayer)
            pageHtml = re.sub(r'href=".*?/([^/]+)\.mp3(?![^>]*download)"',LinkToPage,pageHtml)
                # Match only the non-download link

            menuItems.append((menuItem._replace(title="All/Searchable"),(menuItem,pageHtml)))

        yield from basePage.AddMenuAndYieldPages(menuItems,wrapper=Html.Wrapper('<p class="page-list">Page: ' + 2*"&nbsp","</p>\n"),highlight={"class":"active"})
    else:
        clone = basePage.Clone()
        clone.AppendContent(menuItems[0][1][1])
        yield clone

def ShowDuration(page: Html.PageDesc,filteredExcerpts: list[dict]) -> None:
    durationStr = ExcerptDurationStr(filteredExcerpts,countSessionExcerpts=True,sessionExcerptDuration=False)
    page.AppendContent(Html.Tag("p")(durationStr))

def AddSearchCategory(category: str) -> Callable[[Html.PageDesc,list[dict]],None]:
    """Return a function that customizes a PageDesc object by adding a search category (e.g. Stories)"""
    def _AddSearchCategory(page: Html.PageDesc,_: list[dict],newCategory = category):
        if newCategory:
            page.keywords.append(newCategory)
        page.specialJoinChar["citationTitle"] = " "
        page.AppendContent(f"({newCategory})",section="citationTitle")


    return _AddSearchCategory

def FilteredExcerptsMenuItem(excerpts:Iterable[dict], filter:Filter.Filter, formatter:Formatter, mainPageInfo:Html.PageInfo, menuTitle:str, fileExt:str = "", pageAugmentor:Callable[[Html.PageDesc,list[dict]],None] = lambda page,excerpts:None) -> Html.PageDescriptorMenuItem:
    """Describes a menu item generated by applying a filter to a list of excerpts.
    excerpts: an iterable of the excerpts.
    filter: the filter to apply.
    formatter: the formatter object to pass to HtmlExcerptList.
    mainPageInfo: description of the main page
    menuTitle: the title in the menu.
    fileExt: the extension to add to the main page file for the filtered page.
    pageAugmentor: a function which modifies the base page """
    filteredExcerpts = list(Filter.Apply(excerpts,filter))

    if not filteredExcerpts:
        return []

    if fileExt:
        pageInfo = mainPageInfo._replace(file = Utils.AppendToFilename(mainPageInfo.file,"-" + fileExt))
    else:
        pageInfo = mainPageInfo
    menuItem = pageInfo._replace(title=f"{menuTitle} ({len(filteredExcerpts)})")


    blankPage = Html.PageDesc(pageInfo)
    pageAugmentor(blankPage,filteredExcerpts)

    return itertools.chain([menuItem],MultiPageExcerptList(blankPage,filteredExcerpts,formatter))

def FilteredEventsMenuItem(events:Iterable[dict], filter:Filter.Filter, mainPageInfo:Html.PageInfo, menuTitle:str,fileExt: str = "") -> Html.PageDescriptorMenuItem:
    """Describes a menu item generated by applying a filter to a list of events.
    events: an iterable of the events.
    filter: the filter to apply.
    mainPageInfo: description of the main page.
    menutitle: the title in the menu.
    fileExt: the extension to add to the main page file for the filtered page."""

    filteredEvents = list(Filter.Apply(events,filter))

    if not filteredEvents:
        return []

    if fileExt:
        pageInfo = mainPageInfo._replace(file = Utils.AppendToFilename(mainPageInfo.file,"-" + fileExt))
    else:
        pageInfo = mainPageInfo

    menuItem = pageInfo._replace(title=f"{menuTitle} ({len(filteredEvents)})")

    return menuItem,ListDetailedEvents(filteredEvents)

def AllExcerpts(pageDir: str) -> Html.PageDescriptorMenuItem:
    """Generate a single page containing all excerpts."""

    pageInfo = Html.PageInfo("All excerpts",Utils.PosixJoin(pageDir,"AllExcerpts.html"))
    yield pageInfo

    basePage = Html.PageDesc(pageInfo)

    formatter = Formatter()
    # formatter.excerptDefaultTeacher = ['AP']
    formatter.headingShowSessionTitle = True

    def FilteredItem(filter:Filter,name:str) -> Html.PageDescriptorMenuItem:
        newTitle = "All " + name.lower()
        singular = Utils.Singular(name).lower()
        
        return FilteredExcerptsMenuItem(excerpts,filter,formatter,pageInfo._replace(title=newTitle),name,singular,pageAugmentor= lambda p,x: MostCommonTags(p,x,filter,name))

    def MostCommonTags(page: Html.PageDesc,excerpts: list[dict],filter:Filter = Filter.PassAll, kind: str = "") -> None:
        "Append a list of the most common tags to the beginning of each section"
        ShowDuration(page,excerpts)
        if len(excerpts) < gOptions.minSubsearchExcerpts * 3:
            return
        if kind not in {"","Questions","Stories","Quotes","Readings","Texts","References"}:
            return
        
        tagCount = Counter()
        for x in excerpts:
            tags = set()
            if kind == "Questions":
                tags.update(x["tags"][0:x["qTagCount"]])
            else:
                for item in Filter.AllSingularItems(x):
                    if filter(item):
                        tags.update(item.get("tags",()))
            
            for tag in tags:
                tagCount[tag] += 1
        
        commonTags = sorted(((count,tag) for tag,count in tagCount.items()),key=lambda item:(-item[0],item[1]))
        
        a = Airium()
        with a.p():
            with a.span(style="text-decoration: underline;"):
                a(f"Most common {'topics' if kind else 'tags'}:")
            a.br()
            for count,tag in commonTags[:10]:
                pageToLink = f"tags/{gDatabase['tag'][tag]['htmlFile']}"

                # Link to subpages only if there are enough excerpts that we have generated them
                if gDatabase["tag"][tag]["excerptCount"] >= gOptions.minSubsearchExcerpts:
                    if kind == "Questions":
                        pageToLink = Utils.AppendToFilename(pageToLink,"-qtag")
                    elif kind:
                        pageToLink = Utils.AppendToFilename(pageToLink,"-" + Utils.Singular(kind).lower())

                with a.a(href = f"../{pageToLink}"):
                    a(tag)
                a(f" ({count}){'&nbsp' * 4} ")

        page.AppendContent(str(a))

    excerpts = gDatabase["excerpts"]
    filterMenu = [
        FilteredExcerptsMenuItem(excerpts,Filter.PassAll,formatter,pageInfo,"All excerpts",pageAugmentor=MostCommonTags),
        FilteredItem(Filter.Kind(category="Questions"),"Questions"),
        FilteredItem(Filter.Kind(category="Stories"),"Stories"),
        FilteredItem(Filter.Kind(category="Quotes"),"Quotes"),
        FilteredItem(Filter.Kind(category="Meditations"),"Meditations"),
        FilteredItem(Filter.Kind(category="Teachings"),"Teachings"),
        FilteredItem(Filter.Kind(category="Readings"),"Readings"),
        FilteredItem(Filter.Kind(kind={"Sutta","Vinaya","Commentary"}),"Texts"),
        FilteredItem(Filter.Kind(kind={"Reference"}),"References")
    ]

    filterMenu = [f for f in filterMenu if f] # Remove blank menu items
    yield from basePage.AddMenuAndYieldPages(filterMenu,**SUBMENU_STYLE)

def ListDetailedEvents(events: Iterable[dict]) -> str:
    """Generate html containing a detailed list of all events."""
    
    a = Airium()
    
    firstEvent = True
    for e in events:
        eventCode = e["code"]
        if not firstEvent:
            a.hr()
        firstEvent = False
        with a.h3():
            with a.a(href = EventLink(eventCode)):
                a(e["title"])            
        with a.p():
            a(f'{ListLinkedTeachers(e["teachers"],lastJoinStr = " and ")}')
            a.br()
            a(EventSeriesAndDateStr(e))
            a.br()
            eventExcerpts = [x for x in gDatabase["excerpts"] if x["event"] == eventCode]
            a(ExcerptDurationStr(eventExcerpts))
                
    return str(a)

def EventSeries(event: dict) -> str:
    return event["series"]

def EventDescription(event: dict,showMonth = False) -> str:
    href = Html.Wrapper(f"<a href = {EventLink(event['code'])}>","</a>")
    if showMonth:
        date = Utils.ParseDate(event["startDate"])
        monthStr = f' – {date.strftime("%B")} {int(date.year)}'
    else:
        monthStr = ""
    return f"<p>{href.Wrap(event['title'])} ({event['excerpts']}){monthStr}</p>"

def ListEventsBySeries(events: list[dict]) -> str:
    """Return html code listing these events by series."""

    prevSeries = None

    def SeriesIndex(event: dict) -> int:
        "Return the index of the series of this event for sorting purposes"
        return list(gDatabase["series"]).index(event["series"])
    
    def LinkToAboutSeries(event: dict) -> tuple[str,str,str]:
        htmlHeading = event["series"]
        
        nonlocal prevSeries
        description = ""
        if event["series"] != prevSeries:
            description = gDatabase["series"][event["series"]]["description"]
            if description:
                description = Html.Tag("p",{"class":"smaller"})(description)
            prevSeries = event["series"]
            
        return htmlHeading,description + EventDescription(event,showMonth=True),event["series"]

    eventsSorted = sorted(events,key=SeriesIndex)
    return str(Html.ListWithHeadings(eventsSorted,LinkToAboutSeries))

def ListEventsByYear(events: list[dict]) -> str:
    """Return html code listing these events by series."""
    
    return str(Html.ListWithHeadings(events,lambda e: (str(Utils.ParseDate(e["startDate"]).year),EventDescription(e)) ,countItems=False))

def EventsMenu(indexDir: str) -> Html.PageDescriptorMenuItem:
    """Create the Events menu item and its associated submenus."""

    seriesInfo = Html.PageInfo("Series",Utils.PosixJoin(indexDir,"EventsBySeries.html"),"Events – By series")
    chronologicalInfo = Html.PageInfo("Chronological",Utils.PosixJoin(indexDir,"EventsChronological.html"),"Events – Chronological")
    detailInfo = Html.PageInfo("Detailed",Utils.PosixJoin(indexDir,"EventDetails.html"),"Events – Detailed view")

    yield seriesInfo._replace(title="Events")

    listing = Html.Tag("div",{"class":"listing"})
    eventMenu = [
        [seriesInfo,listing(ListEventsBySeries(gDatabase["event"].values()))],
        [chronologicalInfo,listing(ListEventsByYear(gDatabase["event"].values()))],
        [detailInfo,listing(ListDetailedEvents(gDatabase["event"].values()))],
        [Html.PageInfo("About event series","about/02_Event-series.html")],
        EventPages("events")
    ]

    basePage = Html.PageDesc()
    for page in basePage.AddMenuAndYieldPages(eventMenu,**SUBMENU_STYLE):
        if page.info.titleInBody.startswith("Events – "):
            _,subSection = page.info.titleInBody.split(" – ")
            page.AppendContent(f"Events: {subSection}",section="citationTitle")
            page.keywords = ["Events",subSection]
        yield page

def LinkToTeacherPage(page: Html.PageDesc) -> Html.PageDesc:
    "Link to the teacher page if this tag represents a teacher."

    teacher = Database.TeacherLookup(page.info.title)
    if teacher:
        link = TeacherLink(teacher)
        if link:
            page.AppendContent(f'<a href="{link}">Teachings by {gDatabase["teacher"][teacher]["attributionName"]}</a>',"smallTitle")
    
    return page

def TagPages(tagPageDir: str) -> Iterator[Html.PageAugmentorType]:
    """Write a html file for each tag in the database"""
    
    if gOptions.buildOnlyIndexes:
        return
    
    def SubsumedTagDescription(tagData:dict) -> str:
        """Return a string describing this subsumed tag."""
        additionalBits = []
        if tagData["fullPali"]:
            additionalBits.append(tagData["fullPali"])
        additionalBits += tagData["alternateTranslations"]
        additionalBits += tagData["glosses"]
        if additionalBits:
            return tagData["fullTag"] + f" ({', '.join(additionalBits)})"
        else:
            return tagData["fullTag"]

    subsumesTags = Database.SubsumesTags()
    for tag,tagInfo in gDatabase["tag"].items():
        if not tagInfo["htmlFile"]:
            continue

        relevantExcerpts = list(Filter.Apply(gDatabase["excerpts"],Filter.Tag(tag)))

        a = Airium()
        
        with a.strong():
            if tag in subsumesTags:
                a(TitledList("Subsumes",[SubsumedTagDescription(t) for t in subsumesTags[tag]],plural=""))
            a(TitledList("Alternative translations",tagInfo['alternateTranslations'],plural = ""))
            if ProperNounTag(tagInfo):
                a(TitledList("Other names",[RemoveLanguageTag(name) for name in tagInfo['glosses']],plural = ""))
            else:
                a(TitledList("Glosses",tagInfo['glosses'],plural = ""))
            a(ListLinkedTags("Parent topic",tagInfo['supertags']))
            a(ListLinkedTags("Subtopic",tagInfo['subtags']))
            a(ListLinkedTags("See also",tagInfo['related'],plural = ""))
            a(ExcerptDurationStr(relevantExcerpts,countEvents=False,countSessions=False))
        
        a.hr()

        formatter = Formatter()
        formatter.excerptBoldTags = set([tag])
        formatter.headingShowTags = False
        formatter.excerptOmitSessionTags = False
        formatter.headingShowTeacher = False
        
        tagPlusPali = TagDescription(tagInfo,fullTag=True,style="noNumber",link = False)
        pageInfo = Html.PageInfo(tag,Utils.PosixJoin(tagPageDir,tagInfo["htmlFile"]),DrilldownIconLink(tag,iconWidth = 20) + " &nbsp" + tagPlusPali)
        basePage = Html.PageDesc(pageInfo)
        basePage.AppendContent(str(a))
        basePage.keywords = ["Tag",tagInfo["fullTag"]]
        if tagInfo["fullPali"]:
            basePage.keywords.append(tagInfo["fullPali"])
        basePage.AppendContent(f"Tag: {tagInfo['fullTag']}",section="citationTitle")

        def FilteredTagMenuItem(excerpts: Iterable[dict],filter: Filter,menuTitle: str,fileExt:str = "") -> Html.PageDescriptorMenuItem:
            if not fileExt:
                fileExt = Utils.Singular(menuTitle).lower()
            
            return FilteredExcerptsMenuItem(excerpts=excerpts,filter=filter,formatter=formatter,mainPageInfo=pageInfo,menuTitle=menuTitle,fileExt=fileExt,pageAugmentor=AddSearchCategory(menuTitle))

        if len(relevantExcerpts) >= gOptions.minSubsearchExcerpts:
            questions = Filter.Apply(relevantExcerpts,Filter.Kind(category="Questions"))
            qTags,aTags = Filter.Partition(questions,Filter.QTag(tag))

            filterMenu = [
                FilteredEventsMenuItem(gDatabase["event"].values(),Filter.Tag(tag),pageInfo,"Events","events"),
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.PassAll,formatter,pageInfo,"All excerpts"),
                FilteredTagMenuItem(qTags,Filter.PassAll,"Questions about","qtag"),
                FilteredTagMenuItem(aTags,Filter.PassAll,"Answers involving","atag"),
                FilteredTagMenuItem(relevantExcerpts,Filter.Tag(tag,category="Stories"),"Stories"),
                FilteredTagMenuItem(relevantExcerpts,Filter.Tag(tag,category="Quotes"),"Quotes"),
                FilteredTagMenuItem(relevantExcerpts,Filter.Tag(tag,category="Readings"),"Readings"),
                FilteredTagMenuItem(relevantExcerpts,Filter.Tag(tag,kind={"Sutta","Vinaya","Commentary"}),"Texts"),
                FilteredTagMenuItem(relevantExcerpts,Filter.Tag(tag,kind={"Reference"}),"References")
            ]

            filterMenu = [f for f in filterMenu if f] # Remove blank menu items
            if len(filterMenu) > 1:
                yield from map(LinkToTeacherPage,basePage.AddMenuAndYieldPages(filterMenu,**EXTRA_MENU_STYLE))
            else:
                yield from map(LinkToTeacherPage,MultiPageExcerptList(basePage,relevantExcerpts,formatter))
        else:
            yield from map(LinkToTeacherPage,MultiPageExcerptList(basePage,relevantExcerpts,formatter))

def LinkToTagPage(page: Html.PageDesc) -> Html.PageDesc:
    "Link to the tag page if this teacher has a tag."

    tag = Database.TagLookup(page.info.title)
    if tag:
        page.AppendContent(HtmlTagLink(tag,text = f'Tag [{tag}]'),"smallTitle")

    return page

def TeacherPages(teacherPageDir: str) -> Html.PageDescriptorMenuItem:
    """Yield a page for each individual teacher"""
    
    if gOptions.buildOnlyIndexes:
        return
    xDB = gDatabase["excerpts"]
    teacherDB = gDatabase["teacher"]

    for t,tInfo in teacherDB.items():
        if not tInfo["htmlFile"]:
            continue

        relevantExcerpts = list(Filter.Apply(xDB,Filter.Teacher(t)))
    
        a = Airium()
        
        excerptInfo = ExcerptDurationStr(relevantExcerpts,countEvents=False,countSessions=False,countSessionExcerpts=True)
        a(excerptInfo)
        a.hr()

        formatter = Formatter()
        formatter.headingShowTags = False
        formatter.headingShowTeacher = False
        formatter.excerptOmitSessionTags = False
        formatter.excerptDefaultTeacher = set([t])

        pageInfo = Html.PageInfo(tInfo["fullName"],Utils.PosixJoin(teacherPageDir,tInfo["htmlFile"]))
        basePage = Html.PageDesc(pageInfo)
        basePage.AppendContent(str(a))
        basePage.AppendContent(f"Teacher: {tInfo['fullName']}",section="citationTitle")
        basePage.keywords = ["Teacher",tInfo["fullName"]]

        def FilteredTeacherMenuItem(excerpts: Iterable[dict],filter: Filter,menuTitle: str,fileExt:str = "") -> Html.PageDescriptorMenuItem:
            if not fileExt:
                fileExt = Utils.Singular(menuTitle).lower()
            
            return FilteredExcerptsMenuItem(excerpts=excerpts,filter=filter,formatter=formatter,mainPageInfo=pageInfo,menuTitle=menuTitle,fileExt=fileExt,pageAugmentor=AddSearchCategory(menuTitle))


        if len(relevantExcerpts) >= gOptions.minSubsearchExcerpts:

            filterMenu = [
                FilteredExcerptsMenuItem(relevantExcerpts,Filter.PassAll,formatter,pageInfo,"All excerpts"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,category="Questions"),"Questions"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,category="Stories"),"Stories"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,kind="Quote"),"Direct quotes","d-quote"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,kind="Indirect quote",quotedBy=False),"Quotes others","i-quote"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,kind="Indirect quote",quotesOthers=False),"Quoted by others","quoted-by"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,category="Meditations"),"Meditations"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,category="Teachings"),"Teachings"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,category="Readings"),"Readings from","read-from"),
                FilteredTeacherMenuItem(relevantExcerpts,Filter.Teacher(t,kind="Read by"),"Readings by","read-by")
            ]

            filterMenu = [f for f in filterMenu if f] # Remove blank menu items
            yield from map(LinkToTagPage,basePage.AddMenuAndYieldPages(filterMenu,**EXTRA_MENU_STYLE))
            yield from map(LinkToTagPage,basePage.AddMenuAndYieldPages(filterMenu,**EXTRA_MENU_STYLE))
        else:
            yield from map(LinkToTagPage,MultiPageExcerptList(basePage,relevantExcerpts,formatter))

def TeacherDescription(teacher: dict,nameStr: str = "") -> str:
    href = Html.Tag("a",{"href":TeacherLink(teacher['teacher'])})
    if not nameStr:
        nameStr = teacher['fullName']
    return f"<p> {href.Wrap(nameStr)} ({teacher['excerptCount']}) </p>"

def ListTeachersAlphabetical(teachers: list[dict]) -> str:
    """Return html code listing teachers alphabetically."""
    
    prefixes = sorted(list(p for p in gDatabase["prefix"] if not p.endswith("/")),key=len,reverse=True)
        # Sort prefixes so the longest prefix matches first, and eliminate prefixes ending in / which don't apply to names
    prefixRegex = Utils.RegexMatchAny(prefixes,capturingGroup=True) + r" (.+)"
    
    noAlphabetize = {"alphabetize":""}
    def AlphabetizeName(string: str) -> str:
        if gDatabase["name"].get(string,noAlphabetize)["alphabetize"]:
            return gDatabase["name"][string]["alphabetize"]
        match = re.match(prefixRegex,string)
        if match:
            return match[2] + ", " + match[1]
        else:
            return string

    alphabetized = sorted((AlphabetizeName(t["fullName"]),t) for t in teachers)
    return "\n".join(TeacherDescription(t,name) for name,t in alphabetized)

def TeacherDate(teacher:dict) -> float:
    "Return a teacher's date for sorting purposes."
    try:
        return float(gDatabase["name"][teacher["fullName"]]["sortBy"])
    except (KeyError,ValueError):
        return 9999

def ListTeachersChronological(teachers: list[dict]) -> str:
    """Return html code listing these teachers by group and chronologically."""
    
    teachersWithoutDate = [t["attributionName"] for t in teachers if TeacherDate(t) > 3000]
    if teachersWithoutDate:
        Alert.caution(len(teachersWithoutDate),"teacher(s) do not have dates and will be sorted last.")
        Alert.extra("Teachers without dates:",teachersWithoutDate)
    chronological = sorted(teachers,key=TeacherDate)

    groups = list(gDatabase["group"])
    groups.append("") # Prevent an error if group is blank
    chronological.sort(key=lambda t: groups.index(t["group"]))
    return str(Html.ListWithHeadings(chronological,lambda t: (t["group"],TeacherDescription(t)) ))

def ListTeachersLineage(teachers: list[dict]) -> str:
    """Return html code listing teachers by lineage."""
    
    lineages = list(gDatabase["lineage"])
    lineages.append("") # Prevent an error if group is blank
    hasLineage = [t for t in teachers if t["lineage"] and t["group"] == "Monastics"]
    hasLineage.sort(key=TeacherDate)
        # NOTE: We will sort by teacher date once this information gets into the spreadsheet
    hasLineage.sort(key=lambda t: lineages.index(t["lineage"]))
    return str(Html.ListWithHeadings(hasLineage,lambda t: (t["lineage"],TeacherDescription(t)) ))

def ListTeachersByExcerpts(teachers: list[dict]) -> str:
    """Return html code listing teachers by number of excerpts."""
    
    sortedByExcerpts = sorted(teachers,key=lambda t: t["excerptCount"],reverse=True)
    return "\n".join(TeacherDescription(t) for t in sortedByExcerpts)

def TeacherMenu(indexDir: str) -> Html.PageDescriptorMenuItem:
    """Create the Teacher menu item and its associated submenus."""

    alphabeticalInfo = Html.PageInfo("Alphabetical",Utils.PosixJoin(indexDir,"TeachersAlphabetical.html"),"Teachers – Alphabetical")
    chronologicalInfo = Html.PageInfo("Chronological",Utils.PosixJoin(indexDir,"TeachersChronological.html"),"Teachers – Chronological")
    lineageInfo = Html.PageInfo("Lineage",Utils.PosixJoin(indexDir,"TeachersLineage.html"),"Teachers – Monastics by lineage")
    excerptInfo = Html.PageInfo("Number of teachings",Utils.PosixJoin(indexDir,"TeachersByExcerpts.html"),"Teachers – By number of teachings")

    yield alphabeticalInfo._replace(title="Teachers")

    teachersInUse = [t for t in gDatabase["teacher"].values() if t["htmlFile"]]

    listing = Html.Tag("div",{"class":"listing"})
    teacherMenu = [
        [alphabeticalInfo,listing(ListTeachersAlphabetical(teachersInUse))],
        [chronologicalInfo,listing(ListTeachersChronological(teachersInUse))],
        [lineageInfo,listing(ListTeachersLineage(teachersInUse))],
        [excerptInfo,listing(ListTeachersByExcerpts(teachersInUse))],
        TeacherPages("teachers")
    ]

    basePage = Html.PageDesc()
    for page in basePage.AddMenuAndYieldPages(teacherMenu,**SUBMENU_STYLE):
        if page.info.titleInBody.startswith("Teachers – "):
            _,subSection = page.info.titleInBody.split(" – ")
            page.AppendContent(f"Teachers: {subSection}",section="citationTitle")
            page.keywords = ["Teachers",subSection]
        yield page


def SearchMenu(searchDir: str) -> Html.PageDescriptorMenuItem:
    """Create the Search menu item and its associated submenus."""

    searchPageName = "Text-search.html"
    searchTemplate = Utils.PosixJoin(gOptions.prototypeDir,"templates",searchPageName)
    with open(searchTemplate,encoding='utf8') as file:
        searchPage = file.read()
    
    pageInfo = Html.PageInfo("Search",Utils.PosixJoin(searchDir,searchPageName),titleIB="Search")
    yield pageInfo
    yield (pageInfo._replace(title="Text search"), searchPage)

def AddTableOfContents(sessions: list[dict],a: Airium) -> None:
    """Add a table of contents to the event which is being built."""
    tocPath = Utils.PosixJoin(gOptions.documentationDir,"tableOfContents",sessions[0]["event"] + ".md")
    if os.path.isfile(tocPath):
        with open(tocPath,encoding='utf8') as file:
            template = pyratemp.Template(file.read())
        
        markdownText = template(gOptions = gOptions,gDatabase = gDatabase,Database = Database)

        def ApplyToMarkdownFile(transform: Callable[[str],Tuple[str,int]]) -> int:
            nonlocal markdownText
            markdownText,changeCount = transform(markdownText)
            return changeCount
        
        with Alert.extra.Supress():
            Render.LinkSubpages(ApplyToMarkdownFile)
            Render.LinkKnownReferences(ApplyToMarkdownFile)
            Render.LinkSuttas(ApplyToMarkdownFile)
        
        html = markdown.markdown(markdownText,extensions = ["sane_lists",NewTabRemoteExtension()])
        a.hr()
        with a.div(Class="listing"):
            a(html)
        return

    if len(sessions) > 1:
        if all(s["sessionTitle"] for s in sessions):
            # If all sessions have a title, list sessions by title
            a.hr()
            with a.div(Class="listing"):
                for s in sessions:
                    with a.p():
                        a(f"Session {s['sessionNumber']}:")
                        with a.a(href = f"#{Database.ItemCode(s)}"):
                            a(str(s['sessionTitle']))
        else:
            squish = Airium(source_minify = True) # Temporarily eliminate whitespace in html code to fix minor glitches
            squish("Sessions:")
            for s in sessions:
                squish(" " + 3*"&nbsp")
                with squish.a(href = f"#{Database.ItemCode(s)}"):
                    squish(str(s['sessionNumber']))
            
            a(str(squish))


def EventPages(eventPageDir: str) -> Iterator[Html.PageAugmentorType]:
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
        
        a(f"{eventInfo['venue']} in {gDatabase['venue'][eventInfo['venue']]['location']}")
        a.br()
        
        a(ExcerptDurationStr(excerpts))
        a.br()
        
        if eventInfo["description"]:
            with a.p(Class="smaller"):
                a(eventInfo["description"])
        
        if eventInfo["website"]:
            with a.a(href = eventInfo["website"],target="_blank"):
                a("External website")
            a.br()
        
        AddTableOfContents(sessions,a)
        
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

        page = Html.PageDesc(Html.PageInfo(eventInfo["title"],Utils.PosixJoin(eventPageDir,eventCode+'.html'),titleInBody))
        page.AppendContent(str(a))
        page.keywords = ["Event",eventInfo["title"]]
        page.AppendContent(f"Event: {eventInfo['title']}",section="citationTitle")
        yield page
        
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

def DocumentationMenu(directory: str,makeMenu = True,specialFirstItem:Html.PageInfo|None = None,extraItems:Iterator[Iterator[Html.PageDescriptorMenuItem]] = []) -> Html.PageDescriptorMenuItem:
    """Read markdown pages from documentation/directory, convert them to html, 
    write them in prototype/about, and create a menu out of them.
    specialFirstItem optionally designates the PageInfo for the first item"""

    @Alert.extra.Supress()
    def QuietRender() -> Iterator[Html.PageDesc]:
        return Document.RenderDocumentationFiles(directory,"about",html = True)

    aboutMenu = []
    for page in QuietRender():
        if makeMenu:
            if not aboutMenu:
                if specialFirstItem:
                    if not specialFirstItem.file:
                        specialFirstItem = specialFirstItem._replace(file=page.info.file)
                    page.info = specialFirstItem
                yield page.info
        page.keywords = ["About","Ajahn Pasanno","Question","Story","Archive"]
        citation = "About"
        if page.info.title != "About":
            page.keywords.append(page.info.title)
            citation += f": {page.info.title}"

        page.AppendContent(citation,section="citationTitle")

        aboutMenu.append([page.info,page])
        
    for item in extraItems:
        aboutMenu.append(item)

    if makeMenu:
        basePage = Html.PageDesc()
        yield from basePage.AddMenuAndYieldPages(aboutMenu,**EXTRA_MENU_STYLE)
    else:
        yield from aboutMenu

def TagHierarchyMenu(indexDir:str, drilldownDir: str) -> Html.PageDescriptorMenuItem:
    """Create a submentu for the tag drilldown pages."""
    
    drilldownItem = Html.PageInfo("Hierarchy",drilldownDir,"Tags – Hierarchical")
    contractAllItem = drilldownItem._replace(file=Utils.PosixJoin(drilldownDir,DrilldownPageFile(-1)))
    expandAllItem = drilldownItem._replace(file=Utils.PosixJoin(indexDir,"AllTagsExpanded.html"))
    printableItem = drilldownItem._replace(file=Utils.PosixJoin(indexDir,"Tags_print.html"))

    yield contractAllItem

    drilldownMenu = []
    contractAll = [contractAllItem._replace(title="Contract all")]
    if "drilldown" in gOptions.buildOnly:
        contractAll.append((contractAllItem,IndentedHtmlTagList(expandSpecificTags=set(),expandTagLink=DrilldownPageFile)))
    drilldownMenu.append(contractAll)
    drilldownMenu.append([expandAllItem._replace(title="Expand all"),(expandAllItem,IndentedHtmlTagList(expandDuplicateSubtags=True))])
    drilldownMenu.append([printableItem._replace(title="Printable"),(printableItem,IndentedHtmlTagList(expandDuplicateSubtags=False))])
    if "drilldown" in gOptions.buildOnly:
        drilldownMenu.append(DrilldownTags(drilldownItem))

    basePage = Html.PageDesc()
    basePage.AppendContent("Hierarchical tags",section="citationTitle")
    basePage.keywords = ["Tags","Tag hierarchy"]
    menuStyle = dict(EXTRA_MENU_STYLE)
    menuStyle["wrapper"] += "Numbers in parentheses following tag names: (number of excerpts tagged/number of excerpts tagged with this tag or its subtags).<br><br>"
    yield from basePage.AddMenuAndYieldPages(drilldownMenu,**menuStyle)

def TagMenu(indexDir: str) -> Html.PageDescriptorMenuItem:
    """Create the Tags menu item and its associated submenus.
    Also write a page for each tag."""

    drilldownDir = "drilldown"
    yield next(iter(TagHierarchyMenu(indexDir,drilldownDir)))._replace(title="Tags")

    tagMenu = [
        TagHierarchyMenu(indexDir,drilldownDir),
        AlphabeticalTagList(indexDir),
        NumericalTagList(indexDir),
        MostCommonTagList(indexDir),
        [Html.PageInfo("About tags","about/05_Tags.html")],
        TagPages("tags")
    ]

    baseTagPage = Html.PageDesc()
    yield from baseTagPage.AddMenuAndYieldPages(tagMenu,**SUBMENU_STYLE)

SUBPAGE_SUFFIXES = {"qtag","atag","quote","text","reading","story","reference","from","by","meditation","teaching",
                    }
def WriteSitemapURL(pagePath:str,xml:Airium) -> None:
    "Write the URL of the page at pagePath into an xml sitemap."
    
    if not pagePath.endswith(".html"):
        return

    priority = 1.0
    pathParts = pagePath.split("/")
    directory = pathParts[0]
    if pagePath == "homepage.html":
        pagePath = "index.html"
    elif directory == "about":
        if not re.match("[0-9]+_",pathParts[-1]):
            return
    elif directory == "events":
        priority = 0.9
    else:
        return

    with xml.url():
        with xml.loc():
            xml(f"{gOptions.info.cannonicalURL}{pagePath}")
        with xml.lastmod():
            xml(Utils.ModificationDate(Utils.PosixJoin(gOptions.prototypeDir,pagePath)).strftime("%Y-%m-%d"))
        with xml.changefreq():
            xml("weekly")
        with xml.priority():
            xml(priority)

def XmlSitemap(siteFiles: FileRegister.HashWriter) -> str:
    """Look through the html files we've written and create an xml sitemap."""
    pass

    xml = Airium()
    with xml.urlset(xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"):
        for pagePath in siteFiles.record:
            WriteSitemapURL(pagePath,xml)
    
    return str(xml)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--prototypeDir',type=str,default='prototype',help='Write prototype files to this directory; Default: ./prototype')
    parser.add_argument('--globalTemplate',type=str,default='templates/Global.html',help='Template for all pages relative to prototypeDir; Default: templates/Global.html')
    parser.add_argument('--buildOnly',type=str,default='',help='Build only specified sections. Set of Tags,Drilldown,Events,Teachers,AllExcerpts.')
    parser.add_argument('--buildOnlyIndexes',**Utils.STORE_TRUE,help="Build only index pages")
    parser.add_argument('--audioLinks',type=str,default='chip',help='Options: img (simple image), audio (html 5 audio player), chip (new interface by Owen)')
    parser.add_argument('--excerptsPerPage',type=int,default=100,help='Maximum excerpts per page')
    parser.add_argument('--minSubsearchExcerpts',type=int,default=10,help='Create subsearch pages for pages with at least this many excerpts.')
    parser.add_argument('--attributeAll',**Utils.STORE_TRUE,help="Attribute all excerpts; mostly for debugging")
    parser.add_argument('--maxPlayerTitleLength',type=int,default = 30,help="Maximum length of title tag for chip audio player.")
    parser.add_argument('--blockRobots',**Utils.STORE_TRUE,help="Use <meta name robots> to prevent crawling staging sites.")
    parser.add_argument('--redirectToJavascript',**Utils.STORE_TRUE,help="Redirect page to index.html/#page if Javascript is available.")
    parser.add_argument('--urlList',type=str,default='',help='Write a list of URLs to this file.')
    parser.add_argument('--keepOldHtmlFiles',**Utils.STORE_TRUE,help="Keep old html files from previous runs; otherwise delete them.")

gAllSections = {"tags","drilldown","events","teachers","search","allexcerpts"}
def ParseArguments():
    if gOptions.buildOnly == "":
        gOptions.buildOnly = set(gAllSections)
    elif gOptions.buildOnly.lower() == "none":
        gOptions.buildOnly = set()
    else:
        gOptions.buildOnly = set(section.strip().lower() for section in gOptions.buildOnly.split(','))
        if "drilldown" in gOptions.buildOnly:
            gOptions.buildOnly.add("tags")
        unknownSections = gOptions.buildOnly.difference(gAllSections)
        if unknownSections:
            Alert.warning(f"--buildOnly: Unrecognized section(s) {unknownSections} will be ignored.")
            gOptions.buildOnly = gOptions.buildOnly.difference(unknownSections)
    
    if gOptions.buildOnlyIndexes:
        gOptions.buildOnly -= {"drilldown","allexcerpts","events","search"}

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def YieldAllIf(iterator:Iterator,yieldAll:bool) -> Iterator:
    "Yield all of iterator if yieldAll, otherwise yield only the first element."
    if yieldAll:
        yield from iterator
    else:
        yield next(iter(iterator))

def main():
    if not os.path.exists(gOptions.prototypeDir):
        os.makedirs(gOptions.prototypeDir)
    
    # WriteIndentedTagDisplayList(Utils.PosixJoin(gOptions.prototypeDir,"TagDisplayList.txt"))

    if gOptions.buildOnly != gAllSections:
        if gOptions.buildOnly:
            Alert.warning(f"Building only section(s) --buildOnly {gOptions.buildOnly}. This should be used only for testing and debugging purposes.")
        else:
            Alert.warning(f"No sections built due to --buildOnly none. This should be used only for testing and debugging purposes.")

    basePage = Html.PageDesc()

    indexDir ="indexes"
    mainMenu = []
    technicalMenu = list(DocumentationMenu("technical"))
    technicalMenu[0] = technicalMenu[0]._replace(title="Technical")
    mainMenu.append(DocumentationMenu("about",
                                      specialFirstItem=Html.PageInfo("About","homepage.html","The Ajahn Pasanno Question and Story Archive"),
                                      extraItems=[technicalMenu]))
    mainMenu.append(DocumentationMenu("misc",makeMenu=False))

    mainMenu.append(YieldAllIf(SearchMenu("search"),"search" in gOptions.buildOnly))
    mainMenu.append(YieldAllIf(TagMenu(indexDir),"tags" in gOptions.buildOnly))
    mainMenu.append(YieldAllIf(EventsMenu(indexDir),"events" in gOptions.buildOnly))
    mainMenu.append(YieldAllIf(TeacherMenu("teachers"),"teachers" in gOptions.buildOnly))
    mainMenu.append(YieldAllIf(AllExcerpts(indexDir),"allexcerpts" in gOptions.buildOnly))

    mainMenu.append([Html.PageInfo("Back to Abhayagiri.org","https://www.abhayagiri.org/questions-and-stories")])
    
    with (open(gOptions.urlList if gOptions.urlList else os.devnull,"w") as urlListFile,
            FileRegister.HashWriter(gOptions.prototypeDir,"assets/HashCache.json",exactDates=True) as writer):
        for newPage in basePage.AddMenuAndYieldPages(mainMenu,**MAIN_MENU_STYLE):
            WritePage(newPage,writer)
            print(f"{gOptions.info.cannonicalURL}{newPage.info.file}",file=urlListFile)
        
        writer.WriteTextFile("sitemap.xml",XmlSitemap(writer))
        Alert.extra("html files:",writer.StatusSummary())
        if gOptions.buildOnly == gAllSections and writer.Count(FileRegister.Status.STALE):
            Alert.extra("stale files:",writer.FilesWithStatus(FileRegister.Status.STALE))
        if not gOptions.keepOldHtmlFiles and not gOptions.buildOnlyIndexes:
            DeleteUnwrittenHtmlFiles(writer)
    