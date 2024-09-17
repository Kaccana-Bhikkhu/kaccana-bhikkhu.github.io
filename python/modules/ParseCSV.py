"""A module to read csv files from ./csv and create the Database.json file used by subsequent operations"""

from __future__ import annotations

import os, sys, re, csv, json, unicodedata
import Database
import Filter
import Render
import SplitMp3,Mp3DirectCut
import Utils
from typing import List, Iterator, Tuple, Callable, Any, TextIO
from datetime import timedelta
import Prototype, Alert
from enum import Enum
from collections import Counter, defaultdict

class StrEnum(str,Enum):
    pass

class TagFlag(StrEnum):
    VIRTUAL = "."               # A virtual tag can't be applied to excerpts but can have subtags
    PRIMARY = "*"               # The primary instance of this tag in the hierarchical tag list
    PROPER_NOUN = "p"           # Alphabetize as a proper noun
    PROPER_NOUN_SUBTAGS = "P"   # Alphabetize all subtags as proper nouns
    SORT_SUBTAGS = "S"          # Sort this tag's subtags using the "sortBy"
    DISPLAY_GLOSS = "g"         # Display the first gloss in the tag name; e.g. Saṅgha (Monastic community)
    ENGLISH_ALSO = "E"          # Show in English tags as well as Pali or proper nouns
    CAPITALIZE = "C"            # Capitalize the Pali entry; e.g. Nibbāna
    HIDE = "h"                  # Hide this tag in alphabetical lists

class KeyTagFlag(StrEnum):
    HEADING = "h"               # This tag is subsumed under the Key Topic heading and shouldn't be displayed
    PEER_TAG = "-"              # Subtag of previous topic X. Shown as: X, Y, and Z
    SUBORDINATE_TAG = ","       # Subtag of previous topic X. Shown as: X (includes Y)
    HIDDEN_TAG = "."            # Subtag of previous topic X. Not displayed.

SUBTAG_FLAGS = set([KeyTagFlag.PEER_TAG,KeyTagFlag.SUBORDINATE_TAG,KeyTagFlag.HIDDEN_TAG])
class ExcerptFlag(StrEnum):
    INDENT = "-"
    ATTRIBUTE = "a"
    OVERLAP = "o"
    PLURAL = "s"
    UNQUOTE = "u"

gCamelCaseTranslation = {}
def CamelCase(input: str) -> str: 
    """Convert a string to camel case and remove all diacritics and special characters
    "Based on https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-96.php"""
    
    try:
        return gCamelCaseTranslation[input]
    except KeyError:
        pass
    text = unicodedata.normalize('NFKD', input).encode('ascii', 'ignore').decode('ascii')
    text = text.replace("#"," Number")
    
    text = re.sub(r"([a-zA-Z])([A-Z])(?![A-Z]*\b)",r"\1 \2",text) # Add spaces where the string is already camel case to avoid converting to lower case

    s = re.sub(r"[(_|)?+:\.\/-]", " ", text).title().replace(" ", "")
    if s:
        returnValue = ''.join([s[0].lower(), s[1:]])
    else:
        returnValue = ''

    gCamelCaseTranslation[input] = returnValue
    return returnValue

def CamelCaseKeys(d: dict,reallyChange = True):
    """Convert all keys in dict d to camel case strings"""

    for key in list(d.keys()):
        if reallyChange:
            d[CamelCase(key)] = d.pop(key)
        else:
            CamelCase(key) # Just log what the change would be in the camel case dictionary


def SniffCSVDialect(inFile,scanLength = 4096):
	inFile.seek(0)
	dialect = csv.Sniffer().sniff(inFile.read(scanLength))
	inFile.seek(0)
	return dialect

def BlankDict(inDict):
    "Returns True if all values are either an empty string or None"
    
    for key in inDict:
        value = inDict[key]
        if value is not None and value != '':
            return False
    
    return True

def FirstValidValue(inDict,keyList,inDefault = None):
    for key in keyList:
        if inDict[key]:
            return inDict[key]
    
    return inDefault

def BooleanValue(text: str) -> bool:
    """Returns true if the first three characters of text are 'Yes'.
    This is the standard way of encoding boolean values in the csv files from AP QS Archive main."""
    
    return text[:3] == 'Yes'

def AppendUnique(ioList,inToAppend):
    "Append values to a list unless they are already in it"
    for item in inToAppend:
        if not item in ioList:
            ioList.append(item)

def CSVToDictList(file: TextIO,skipLines = 0,removeKeys = [],endOfSection = None,convertBools = BooleanValue,camelCase = True):
    for _ in range(skipLines):
        file.readline()
    
    reader = csv.DictReader(file)
    output = []
    for row in reader:
        firstDictValue = row[next(iter(row))].strip()
        if firstDictValue == endOfSection:
            break
        elif not BlankDict(row):
            if not firstDictValue:
                Alert.warning("blank first field in",row)
        
            # Increase robustness by stripping values and keys
            for key in list(row):
                row[key] = row[key].strip()
                if key != key.strip():
                    row[key.strip()] = row.pop(key)
            
            if convertBools:
                for key in row:
                    if key[-1:] == '?':
                        row[key] = convertBools(row[key])
            
            if camelCase:
                CamelCaseKeys(row)
            output.append(row)
    
    removeKeys.append("")
    for key in removeKeys:
        for row in output:
            row.pop(key,None)
    
    return output

def SkipModificationLine(file: TextIO) -> None:
    """Skip the first line of the file if it is of the form "Modified:DATE"""
    if file.tell() == 0:
        if not file.readline().startswith("Modified:"):
            file.seek(0)
    
def CSVFileToDictList(fileName,*args,**kwArgs):
    """Read a CSV file and convert it to a list of dictionaries"""
    
    with open(fileName,encoding='utf8') as file:
        SkipModificationLine(file)
        return CSVToDictList(file,*args,**kwArgs)

def ListifyKey(dictList: list|dict,key: str,delimiter:str = ';') -> None:
    """Convert the values in a specific key to a list for all dictionaries in dictList.
    First, look for other keys with names like dictKey+'2', etc.
    Then split all these keys using the given delimiter, concatenate the results, and store it in dictKey.
    Remove any other keys found."""
    
    for d in Utils.Contents(dictList):
        if key not in d:
            d[key] = []
            continue

        keyList = [key]
        if key[-1] == '1': # Does the key name end in 1?
            baseKey = key[:-1].strip()
        else:
            baseKey = key
        
        keyIndex = 1
        foundKey = True
        while foundKey:
            keyIndex += 1
            foundKey = False
            for testKey in [baseKey + str(keyIndex),baseKey + ' ' + str(keyIndex)]:
                if testKey in d:
                    keyList.append(testKey)
                    foundKey = True
        
        items = []
        for sequentialKey in keyList:
            items += d[sequentialKey].split(delimiter)
        items = [s.strip() for s in items if s.strip()]
        d[baseKey] = items
                    
        if baseKey == key:
            delStart = 1
        else:
            delStart = 0
        for index in range(delStart,len(keyList)):
            del d[keyList[index]]

def ConvertToInteger(dictList,key,defaultValue = None,reportError:Alert.AlertClass|None = None):
    "Convert the values in key to ints"
    
    def Convert(s: str) -> int:
        try:
            return int(s)
        except ValueError as err:
            if reportError and s:
                reportError("Cannot convert",repr(s),"to an integer in",d)
            return defaultValue

    sequences = frozenset((list,tuple))
    for d in Utils.Contents(dictList):
        if type(d[key]) in sequences:
            d[key] = [Convert(item) for item in d[key]]
        else:
            d[key] = Convert(d[key])

def ListToDict(inList,key = None):
    """Convert a list of dicts to a dict of dicts using key. If key is None, use the first key
    Throw an exception if there are duplicate values."""
    
    if key is None:
        key = next(iter(inList[0]))
    
    outDict = {}
    for item in inList:
        newKey = item[key]
        if newKey in outDict:
            Alert.warning("ListToDict: Duplicate key:",newKey,". Will use the value of the old key:",outDict[newKey])
        else:
            outDict[newKey] = item
    
    return outDict

def DictFromPairs(inList,keyKey,valueKey,camelCase = True):
    "Convert a list of dicts to a dict by taking a single key/value pair from each dict."
    
    outDict = {}
    for item in inList:
        newKey = item[keyKey]
        if newKey in outDict:
            Alert.warning("DictFromPairs: Duplicate key:",newKey,". Will use the value of the old key:",outDict[newKey])
        else:
            outDict[newKey] = item[valueKey]
    
    if camelCase:
        CamelCaseKeys(outDict)
    return outDict

def LoadSummary(database,summaryFileName):
    summaryList = CSVFileToDictList(summaryFileName,skipLines = 1,removeKeys = ["seconds","sortBy"],endOfSection = '<---->')
    
    for numericalKey in ["sessions","excerpts","answersListenedTo","tagsApplied","invalidTags"]:
        ConvertToInteger(summaryList,numericalKey)
    
    database["summary"] = ListToDict(summaryList,"eventCode")

class TagStackItem:
    """Information about a supertag
        tag - str - name of the supertag at this level
        collectSubtags - bool - do we add subtags to this tag?
        subtagIndex - int - index of the next subtag to add to this supertag."""
        
    def __init__(self,tag,collectSubtags = False,indexSubtags = False):
        self.tag = tag
        self.collectSubtags = collectSubtags
        if indexSubtags:
            self.subtagIndex = 1
        else:
            self.subtagIndex = None
    
    def Increment(self,count = 1):
        if self.subtagIndex:
            self.subtagIndex += count
    

def LoadTagsFile(database,tagFileName):
    "Load Tag_Raw from a file and parse it to create the Tag dictionary"

    # First load the raw tags from the csv file
    rawTagList = CSVFileToDictList(tagFileName,skipLines = 1,removeKeys = ["indentedTags","paliTerm","tagMenu","Tag count","paliTagMenu"])
        
    ListifyKey(rawTagList,"alternateTranslations")
    ListifyKey(rawTagList,"glosses")
    ListifyKey(rawTagList,"related")
    ConvertToInteger(rawTagList,"level",reportError=Alert.error)
    
    for item in rawTagList:     
        digitFlag = re.search("[0-9]",item["flags"])
        if digitFlag:
            item["itemCount"] = int(digitFlag[0])
        else:
            item["itemCount"] = 0 if TagFlag.VIRTUAL in item["flags"] else 1

    # Next build the main tag dictionary
    tags = {}
    namePreference = ["abbreviation","fullTag","paliAbbreviation","pali"]
    paliPreference = ["paliAbbreviation","pali"]
    fullNamePreference = ["fullTag","pali"]
    referencedTag = ["subsumedUnder","abbreviation","fullTag","paliAbbreviation","pali"]
    
    # Remove any blank values from the list before looping over it
    rawTagList = [tag for tag in rawTagList if FirstValidValue(tag,namePreference)]
    
    # Redact tags for teachers who haven't given consent - teacher names are never abbreviated, so use fullTag
    unallowedTags = [teacher["fullName"] for abbrev,teacher in database["teacher"].items() if not TeacherConsent(database["teacher"],[abbrev],"allowTag")]
    redactedTags = [tag["fullTag"] for tag in rawTagList if tag["fullTag"] in unallowedTags]
    rawTagList = [tag for tag in rawTagList if tag["fullTag"] not in unallowedTags]

    subsumedTags = {} # A dictionary of subsumed tags for future reference
    virtualHeadings = set() # Tags used only as list headers

    tagStack = [] # Supertag ancestry stack
    
    lastTagLevel = 1
    lastTag = TagStackItem("")
    for rawTagIndex,rawTag in enumerate(rawTagList):
        
        tagName = FirstValidValue(rawTag,namePreference)
        tagPaliName = FirstValidValue(rawTag,paliPreference,"")

        rawTag["tag"] = FirstValidValue(rawTag,referencedTag)

        tagDesc = {}
        tagDesc["tag"] = tagName
        tagDesc["pali"] = tagPaliName
        tagDesc["fullTag"] = FirstValidValue(rawTag,fullNamePreference)
        tagDesc["fullPali"] = rawTag["pali"]
        for key in ["number","alternateTranslations","glosses","related","flags"]:
            tagDesc[key] = rawTag[key]
                
        # Assign subtags and supertags based on the tag level. Interpret tag level like indented code sections.
        curTagLevel = rawTag["level"]        
        while (curTagLevel < lastTagLevel):
            tagStack.pop()
            lastTagLevel -= 1
        
        if curTagLevel > lastTagLevel:
            assert curTagLevel == lastTagLevel + 1, f"Level of tag {tagName} increased by more than one."
            if curTagLevel > 1:
                if lastTag.collectSubtags: # If the previous tag was flagged as primary, remove subtags from previous instances and accumulate new subtags
                    tags[lastTag.tag]["subtags"] = []
                elif lastTag.tag not in subsumedTags and not tags[lastTag.tag]["subtags"]: # But even if it's not primary, accumulate subtags if there are no prior subtags
                    lastTag.collectSubtags = True
                
                tagStack.append(lastTag)
 
        tagDesc["subtags"] = []
        rawTag["indexNumber"] = ""
        if curTagLevel > 1:
            tagDesc["supertags"] = [tagStack[-1].tag]
            if tagStack[-1].subtagIndex:
                if rawTag["itemCount"]:
                    rawTag["indexNumber"] = str(tagStack[-1].subtagIndex)
                    tagStack[-1].Increment(rawTag["itemCount"])
            if tagStack[-1].collectSubtags:
                tags[tagStack[-1].tag]["subtags"].append(tagName)
        else:
            tagDesc["supertags"] = []

        lastTagLevel = curTagLevel
        lastTag = TagStackItem(tagName,TagFlag.PRIMARY in rawTag["flags"] and not rawTag["subsumedUnder"],
                               bool(rawTag["number"])) # Count subtags if this tag is numerical
        
        # Subsumed tags don't have a tag entry
        if rawTag["subsumedUnder"]:
            if TagFlag.PRIMARY in tagDesc["flags"] or tagName not in subsumedTags:
                tagDesc["subsumedUnder"] = rawTag["subsumedUnder"]
                subsumedTags[tagName] = tagDesc
            continue
        
        # If this is a duplicate tag, insert only if the primary flag is true
        tagDesc["copies"] = 1
        tagDesc["primaries"] = 1 if TagFlag.PRIMARY in rawTag["flags"] else 0
        if tagName in tags:
            if TagFlag.PRIMARY in rawTag["flags"]:
                tagDesc["copies"] += tags[tagName]["copies"]
                tagDesc["primaries"] += tags[tagName]["primaries"]
                AppendUnique(tagDesc["supertags"],tags[tagName]["supertags"])
            else:
                tags[tagName]["copies"] += tagDesc["copies"]
                tags[tagName]["primaries"] += tagDesc["primaries"]
                AppendUnique(tags[tagName]["supertags"],tagDesc["supertags"])
                continue
        
        if TagFlag.VIRTUAL in rawTag["flags"] and (rawTagIndex + 1 >= len(rawTagList) or rawTagList[rawTagIndex + 1]["level"] <= rawTag["level"]):
            virtualHeadings.add(tagName)
            tagDesc["htmlFile"] = "" # Virtual tags with no subtags don't have a page
        else:
            tagDesc["htmlFile"] = Utils.slugify(tagName) + '.html'
        
        tags[tagName] = tagDesc
    
    for tag in tags.values():
        tag["subtags"] = [t for t in tag["subtags"] if t not in virtualHeadings]
            # Remove virtual headings from subtag lists

    database["tag"] = tags
    database["tagRaw"] = rawTagList
    database["tagSubsumed"] = subsumedTags
    database["tagRedacted"] = redactedTags

kNumberNames = ["zero","one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve"]


def RemoveUnusedTags(database: dict) -> None:
    """Remove unused tags from the raw tag list before building the tag display list."""

    def TagCount(tag: dict) -> bool:
        return tag.get("excerptCount",0) + tag.get("sessionCount",0) + tag.get("sessionCount",0)

    def NamedNumberTag(tag: dict) -> bool:
        "Does this tag explicitly mention a numbered list?"
        if tag["number"] and int(tag["number"]) < len(kNumberNames):
            return kNumberNames[int(tag["number"])] in tag["fullTag"]
        else:
            return False

    usedTags = set(tag["tag"] for tag in database["tag"].values() if TagCount(tag))
    usedTags.update(t["subsumedUnder"] for t in gDatabase["tagSubsumed"].values())

    Alert.extra(len(usedTags),"unique tags applied.")
    
    prevTagCount = 0
    round = 0
    while prevTagCount < len(usedTags):
        round += 1
        prevTagCount = len(usedTags)

        for parent,children in WalkTags(database["tagRaw"]):
            anyTagUsed = numberedTagUsed = False
            for childTag in children:
                if childTag["tag"] in usedTags:
                    anyTagUsed = True
                    if childTag["indexNumber"]:
                        numberedTagUsed = True

            if anyTagUsed: # Mark the parent tag as used if any of the children are in use
                usedTags.add(parent["tag"])

            # Mark all numbered tags as used if any other numbered tag is in use or we expect to see a numbered list i.e. "Four Noble Truths"
            if (parent["tag"] in usedTags and NamedNumberTag(parent)) or numberedTagUsed: # Mark all numbered tags as used if
                seenNumberedTagYet = False
                for childTag in children:
                    if childTag["indexNumber"] or not seenNumberedTagYet: # Tags before the numbered list are essential headings
                        usedTags.add(childTag["tag"])
                    if childTag["indexNumber"]:
                        seenNumberedTagYet = True

    """remainingTags = set(usedTags)
    with open("prototype/UsedTags.txt",mode="w",encoding='utf-8') as file:
        for rawTag in database["tagRaw"]:
            tag = rawTag["tag"]
            name = FirstValidValue(rawTag,["fullTag","pali"])

            indent = "     " * (rawTag["level"] - 1)

            if tag in usedTags:
                remainingTags.discard(tag)
                name = name.upper()

            display = indent + (f"{rawTag['indexNumber']}. " if rawTag["indexNumber"] else "") + name + f" ({TagCount(database['tag'][tag])})"

            print(display,file=file)"""
    
    database["tagRaw"] = [tag for tag in database["tagRaw"] if tag["tag"] in usedTags]
    database["tagRemoved"] = [tagName for tagName,tag in database["tag"].items() if tagName not in usedTags]
    database["tag"] = {tagName:tag for tagName,tag in database["tag"].items() if tagName in usedTags}

    for tag in database["tag"].values():
        tag["subtags"] = [t for t in tag["subtags"] if t in usedTags]
        tag["related"] = [t for t in tag["related"] if t in usedTags]

def IndexTags(database: dict) -> None:
    """Add listIndex tag to raw tags after we have removed unused tags."""
    tagsSoFar = set()
    for n,tag in enumerate(database["tagDisplayList"]):
        tagName = tag["tag"]
        if not tagName:
            tagName = tag["virtualTag"]
        if tag["subsumed"]:
            continue
        if tagName in tagsSoFar and TagFlag.PRIMARY not in tag["flags"]:
            continue

        tagsSoFar.add(tagName)
        
        database["tag"][tagName]["listIndex"] = n

    tagList = database["tagDisplayList"]
    # Cross-check tag indexes
    for tag in database["tag"]:
        if TagFlag.VIRTUAL not in database["tag"][tag]["flags"]:
            index = database["tag"][tag]["listIndex"]
            assert tag == tagList[index]["tag"],f"Tag {tag} has index {index} but TagList[{index}] = {tagList[index]['tag']}"

    """for tag in database["tag"].values():
        if tag["listIndex"] != tag["newListIndex"]:
            print(f"Mismatched numbers: {tag['tag']}: {tag['listIndex']=}, {tag['newListIndex']=}")"""

def SortTags(database: dict) -> None:
    """Sort subtags of tags with flag 'S' according to sort by dates in Name sheet."""

    datelessTags = []
    for parentIndex,childIndexes in WalkTags(database["tagDisplayList"],returnIndices=True):
        parent = database["tagDisplayList"][parentIndex]
        if TagFlag.SORT_SUBTAGS not in parent["flags"]:
            continue
        
        childIndexes = range(childIndexes[0],childIndexes[-1] + 1)
            # WalkTags omits subtags, so include all tags between the first and the last; 
        children = [database["tagDisplayList"][i] for i in childIndexes]

        def SortByDate(tagInfo:dict) -> float:
            fullTag = database["tag"][tagInfo["tag"]]["fullTag"]
            sortBy = database["name"].get(fullTag,{"sortBy":""})["sortBy"]
            if sortBy:
                try:
                    return float(sortBy)
                except ValueError:
                    pass
            datelessTags.append(fullTag)
            return 9999.0

        baseIndent = children[0]["level"]
        lastDate = None
        tagDates = {}
        for child in children:
            if child["level"] == baseIndent: # Any subtags sort by the date of their parent.
                    # Since the sort is stable, this keeps subtags with their parents.
                lastDate = SortByDate(child)
            tagDates[child["tag"]] = lastDate

        children.sort(key=lambda tag: tagDates[tag["tag"]])
        for index,child in zip(childIndexes,children):
            database["tagDisplayList"][index] = child
    if datelessTags:
        Alert.caution("Cannot find a date for",len(datelessTags),"tag(s) in the Name sheet. These tags will go last.")
        Alert.extra("Dateless tags:",datelessTags)

def CountSubtagExcerpts(database):
    """Add the subtagCount and subtagExcerptCount fields to each item in tagDisplayList which counts the number
    of excerpts which are tagged by this tag or any of its subtags."""

    tagList = database["tagDisplayList"]
    excerpts = database["excerpts"]
    subtags = [None] * len(tagList)
    savedSearches = [None] * len(tagList)
    for parentIndex,childIndexes in WalkTags(tagList,returnIndices=True):
        theseTags = set()
        thisSearch = set()
        for index in childIndexes + [parentIndex]:
            if subtags[index] is None:
                tag = tagList[index]["tag"]
                if tag:
                    subtags[index] = {tag}
                    savedSearches[index] = {id(x) for x in Filter.Tag(tag)(excerpts)}
                    #print(f"{index} {tag}: {len(savedSearches[index])} excerpts singly")
                else:
                    subtags[index] = set()
                    savedSearches[index] = set()
            
            theseTags.update(subtags[index])
            thisSearch.update(savedSearches[index])
        
        subtags[parentIndex] = theseTags
        savedSearches[parentIndex] = thisSearch
        #print(f"{parentIndex} {tagList[parentIndex]["tag"]}: {len(savedSearches[index])} excerpts singly")
        tagList[parentIndex]["subtagCount"] = len(theseTags) - 1
        tagList[parentIndex]["subtagExcerptCount"] = len(thisSearch)

def CollectTopicHeadings(database:dict[str]) -> None:
    """Create keyTopic dictionary from keyTag dictionary."""

    topicHeading = {}
    currentHeading = {}
    topicsToRemove = set()
    mainTopic = None
    for topic in database["keyTopic"].values():
        if topic["heading"]:
            currentHeading = {
                "code": topic["headingCode"],
                "heading": topic["heading"],
                "shortNote": topic["shortNote"],
                "longNote": topic["longNote"],
                "listFile": "list-" + topic["headingCode"] + ".html",
                "topics": []
            }
            topicHeading[topic["headingCode"]] = currentHeading
        
        if topic["flags"] in SUBTAG_FLAGS:
            topicsToRemove.add(topic["topic"])
            mainTopic["subtags"][topic["topic"]] = topic["flags"]
        else:
            mainTopic = topic
            topic["subtags"] = {}
            topic["headingCode"] = currentHeading["code"]
            topic["heading"] = currentHeading["heading"]
            database["tag"][topic["topic"]]["topicHeading"] = currentHeading["code"]
            if not topic["displayAs"]:
                topic["displayAs"] = topic["topic"]
            topic.pop("shortNote",None)
            topic.pop("longNote",None)
            
            currentHeading["topics"].append(topic["topic"])
    
    for topic in topicsToRemove:
        del database["keyTopic"][topic]
    
    for topic in database["keyTopic"].values():
        if topic["subtags"]: # Topics with subtopics link to separate pages in the topics directory
            topic["htmlPath"] = f"topics/{Utils.slugify(topic['topic'])}.html"
        else: # Tags without subtopics link to pages in the tags directory
            topic["htmlPath"] = f"tags/{database['tag'][topic['topic']]['htmlFile']}"

    database["topicHeading"] = topicHeading

def CreateTagDisplayList(database):
    """Generate Tag_DisplayList from Tag_Raw and Tag keys in database
    Format: level, text of display line, tag to open when clicked""" 
    
    tagList = []
    for rawTag in database["tagRaw"]:
        listItem = {}
        for key in ["level","indexNumber","flags"]:
            listItem[key] = rawTag[key]
        
        itemCount = rawTag["itemCount"]
        if itemCount > 1:
            indexNumber = int(rawTag["indexNumber"])
            separator = '-' if itemCount > 1 else ','
            listItem["indexNumber"] = separator.join((str(indexNumber),str(indexNumber + itemCount - 1)))
        
        name = FirstValidValue(rawTag,["fullTag","pali"])
        tag = rawTag["tag"]
        text = name
        
        try:
            excerptCount = database["tag"][tag]["excerptCount"]
        except KeyError:
            excerptCount = 0
        subsumed = bool(rawTag["subsumedUnder"])
        
        if excerptCount > 0 and not subsumed:
            text += " (" + str(excerptCount) + ")"
        
        if rawTag["fullTag"] and rawTag["pali"]:
            text += " [" + rawTag["pali"] + "]"

        if subsumed:
            text += " see " + rawTag["subsumedUnder"]
            if excerptCount > 0:
                text += " (" + str(excerptCount) + ")"
        
        listItem["name"] = name
        listItem["pali"] = rawTag["pali"]
        listItem["excerptCount"] = excerptCount
        listItem["subsumed"] = subsumed
        listItem["text"] = text
            
        if TagFlag.VIRTUAL in rawTag["flags"]:
            listItem["tag"] = "" # Virtual tags don't have a display page
            listItem["virtualTag"] = tag
        else:
            listItem["tag"] = tag
        
        tagList.append(listItem)
    
    database["tagDisplayList"] = tagList
    
    if not gOptions.jsonNoClean:
        del gDatabase["tagRaw"]

def WalkTags(tagDisplayList: list,returnIndices:bool = False,yieldRootTags = False) -> Iterator[Tuple[dict,List[dict]]]:
    """Return (tag,subtags) tuples for all tags that have subtags. Walk the list depth-first."""
    tagStack = []
    for n,tag in enumerate(tagDisplayList):
        tagLevel = tag["level"]
        while len(tagStack) > tagLevel: # If the tag level drops, then yield the accumulated tags and their parent 
            children = tagStack.pop()
            parent = tagStack[-1][-1] # The last item of the next-highest level is the parent tag
            yield parent,children
        
        if tagLevel > len(tagStack):
            assert tagLevel == len(tagStack) + 1, f"Level of tag {tag['tagName']} increased by more than one."
            tagStack.append([])
        
        if returnIndices:
            tagStack[-1].append(n)
        else:
            tagStack[-1].append(tag)
    
    while len(tagStack) > 1: # Yield sibling tags still in the list
        children = tagStack.pop()
        parent = tagStack[-1][-1] # The last item of the next-highest level is the parent tag
        yield parent,children
    
    if tagStack and yieldRootTags:
        yield None,tagStack[0]
        

def TeacherConsent(teacherDB: List[dict], teachers: List[str], policy: str, singleConsentOK = False) -> bool:
    """Scan teacherDB to see if all teachers in the list have consented to the given policy. Return False if not.
    If singleConsentOK then only one teacher must consent to return True."""
    
    if gOptions.ignoreTeacherConsent:
        return True
    
    consent = True
    for teacher in teachers:
        if teacherDB[teacher][policy]:
            if singleConsentOK:
                return True
        else:
            consent = False
        
    return consent

def PrepareReferences(reference) -> None:
    """Prepare database["reference"] for use."""

    ListifyKey(reference,"author1")
    ConvertToInteger(reference,"pdfPageOffset")

    # Convert ref["abbreviation"] to lowercase for dictionary matching
    # ref["title"] still has the correct case
    for ref in list(reference.keys()):
        reference[ref.lower()] = reference.pop(ref)


def PrepareTeachers(teacherDB) -> None:
    """Prepare database["teacher"] for use."""
    for t in teacherDB.values():
        if not t.get("attributionName",""):
            t["attributionName"] = t["fullName"]
        if TeacherConsent(teacherDB,[t["teacher"]],"teacherPage") and t.get("excerptCount",0):
            t["htmlFile"] = Utils.slugify(t["attributionName"]) + ".html"
        else:
            t["htmlFile"] = ""

itemAllowedFields = {"startTime": "takesTimes", "endTime": "takesTimes", "teachers": "takesTeachers", "aTag": "takesTags", "qTag": "takesTags"}

def CheckItemContents(item: dict,prevExcerpt: dict|None,kind: dict) -> bool:
    """Print alerts if there are unexpectedly blank or filled fields in item based on its kind."""

    isExcerpt = bool(item["startTime"]) and kind["canBeExcerpt"]
        # excerpts specify a start time
    
    if not isExcerpt and not kind["canBeAnnotation"]:
        Alert.warning(item,"to",prevExcerpt,f": Kind {repr(item['kind'])} is not allowed for annotations.")
    
    for key,permission in itemAllowedFields.items():
        if item[key] and not kind[permission]:
            message = f"has ['{key}'] = {repr(item[key])}, but kind {repr(item['kind'])} does not allow this."
            if isExcerpt or not prevExcerpt:
                Alert.caution(item,message)
            else:
                Alert.caution(item,"to",prevExcerpt,message)

def FinalizeExcerptTags(x: dict) -> None:
    """Combine qTags and aTags into a single list, but keep track of how many qTags there are."""
    x["tags"] = x["qTag"] + x["aTag"]
    x["qTagCount"] = len(x["qTag"])
    if len(x["fTagOrder"]) != len(x["fTags"]):
        Alert.caution(x,f"has {len(x['fTags'])} fTag but specifies {len(x['fTagOrder'])} fTagOrder numbers.")
    if not gOptions.jsonNoClean:
        del x["qTag"]
        del x["aTag"]
        x.pop("aListen",None)
        if not x["fTags"]:
            x.pop("fTagOrder")

def AddExcerptTags(excerpt: dict,annotation: dict) -> None:
    "Combine qTag, aTag, fTag, and fTagOrder keys from an Extra Tags annotation with an existing excerpt."

    for key in ("qTag","aTag","fTags","fTagOrder"):
        excerpt[key] = excerpt.get(key,[]) + annotation.get(key,[])

def AddAnnotation(database: dict, excerpt: dict,annotation: dict) -> None:
    """Add an annotation to a excerpt."""
    
    if annotation["sessionNumber"] != excerpt["sessionNumber"]:
        Alert.warning("Annotation",annotation,"to",excerpt,f"has a different session number ({annotation['sessionNumber']}) than its excerpt ({excerpt['sessionNumber']})")
    global gRemovedAnnotations
    if annotation["exclude"]:
        excludeAlert(annotation,"to",excerpt,"- exclude flag Yes.")
        gRemovedAnnotations += 1
        return
    if database["kind"][annotation["kind"]].get("exclude",False):
        excludeAlert(annotation,"to",excerpt,"- kind",repr(annotation["kind"]),"exclude flag Yes.")
        gRemovedAnnotations += 1
        return
    
    CheckItemContents(annotation,excerpt,database["kind"][annotation["kind"]])
    if annotation["kind"] == "Extra tags":
        for prevAnnotation in reversed(excerpt["annotations"]): # look backwards and add these tags to the first annotation that supports them
            if "tags" in prevAnnotation:
                prevAnnotation["tags"] += annotation["qTag"]
                prevAnnotation["tags"] += annotation["aTag"] # annotations don't distinguish between q and a tags
                return
        
        AddExcerptTags(excerpt,annotation) # If no annotation takes the tags, give them to the excerpt
        return
    
    kind = database["kind"][annotation["kind"]]
    
    keysToRemove = ["sessionNumber","offTopic","aListen","exclude","qTag","aTag"]
    
    if kind["takesTeachers"]:
        if not annotation["teachers"]:
            defaultTeacher = kind["inheritTeachersFrom"]
            if defaultTeacher == "Anon": # Check if the default teacher is anonymous
                annotation["teachers"] = ["Anon"]
            elif defaultTeacher == "Excerpt":
                annotation["teachers"] = excerpt["teachers"]
            elif defaultTeacher == "Session" or (defaultTeacher == "Session unless text" and not annotation["text"]):
                ourSession = Database.FindSession(database["sessions"],excerpt["event"],excerpt["sessionNumber"])
                annotation["teachers"] = ourSession["teachers"]
        
        if not (TeacherConsent(database["teacher"],annotation["teachers"],"indexExcerpts") or database["kind"][annotation["kind"]]["ignoreConsent"]):
            # If a teacher of one of the annotations hasn't given consent, we redact the excerpt itself
            if annotation["teachers"] == excerpt["teachers"] and database["kind"][excerpt["kind"]]["ignoreConsent"]:
                pass # Unless the annotation has the same teachers as the excerpt and the excerpt kind ignores consent; e.g. "Reading"
            else:
                excerpt["exclude"] = True
                excludeAlert(excerpt,"due to teachers",annotation["teachers"],"of",annotation)
                return
        
        teacherList = [teacher for teacher in annotation["teachers"] if TeacherConsent(database["teacher"],[teacher],"attribute") or database["kind"][annotation["kind"]]["ignoreConsent"]]
        for teacher in set(annotation["teachers"]) - set(teacherList):
            gUnattributedTeachers[teacher] += 1

        if annotation["kind"] == "Reading":
            AppendUnique(teacherList,ReferenceAuthors(annotation["text"]))

        annotation["teachers"] = teacherList
    else:
        keysToRemove.append("teachers")
    
    if kind["takesTags"]:
        annotation["tags"] = annotation["qTag"] + annotation["aTag"] # Annotations don't distiguish between q and a tags
    
    if kind["canBeExcerpt"] or not kind["takesTimes"]:
        keysToRemove += ["startTime","endTime"]
    
    for key in keysToRemove:
        annotation.pop(key,None)    # Remove keys that aren't relevant for annotations
    
    annotation["indentLevel"] = len(annotation["flags"].split(ExcerptFlag.INDENT))
    if len(excerpt["annotations"]):
        prevAnnotationLevel = excerpt["annotations"][-1]["indentLevel"]
    else:
        prevAnnotationLevel = 0
    if annotation["indentLevel"] - 1 > prevAnnotationLevel:
        Alert.warning("Annotation",annotation,"to",excerpt,": Cannot increase indentation level by more than one.")
    
    excerpt["annotations"].append(annotation)

gAuthorRegexList = None
def ReferenceAuthors(textToScan: str) -> list[str]:
    global gAuthorRegexList
    if not gAuthorRegexList:
        gAuthorRegexList = Render.ReferenceMatchRegExs(gDatabase["reference"])
    authors = []
    for regex in gAuthorRegexList:
        matches = re.findall(regex,textToScan,flags = re.IGNORECASE)
        for match in matches:
            AppendUnique(authors,gDatabase["reference"][match[0].lower()]["author"])

    return authors

def FilterAndExplain(items: list,filter: Callable[[Any],bool],printer: Alert.AlertClass,message: str) -> list:
    """Return [i for in items if filter(i)].
    Print a message for each excluded item using printer and message."""
    filteredItems = []
    excludedItems = []
    for i in items:
        if filter(i):
            filteredItems.append(i)
        else:
            excludedItems.append(i)

    for i in excludedItems:
        printer(i,message)
    return filteredItems

def CreateClips(excerpts: list[dict], sessions: list[dict], database: dict) -> None:
    """For excerpts in a given event, convert startTime and endTime keys into the clips key.
    Add audio sources from sessions (and eventually audio annotations) to database["audioSource"]
    Eventually this function will scan for Alt. Audio and Append Audio annotations for extended functionality."""

    # First eliminate excerpts with fatal parsing errors.
    deletedExcerptIDs = set() # Ids of excerpts with fatal parsing errors
    for x in excerpts:
        try:
            if x["startTime"] != "Session":
                startTime = Mp3DirectCut.ToTimeDelta(x["startTime"])
                if startTime is None:
                    deletedExcerptIDs.add(id(x))
            endTime = Mp3DirectCut.ToTimeDelta(x["endTime"])
        except Mp3DirectCut.ParseError:
            deletedExcerptIDs.add(id(x))

    for index in reversed(range(len(excerpts))):
        if id(excerpts[index]) in deletedExcerptIDs:
            Alert.error("Misformed time string in",excerpts[index],". Will delete this excerpt.")
            del excerpts[index]
    
    def AddAudioSource(filename:str, duration:str, event: str, url: str) -> None:
        """Add an audio source to database["audioSource"]."""
        noDiacritics = Utils.RemoveDiacritics(filename)
        if filename != noDiacritics:
            Alert.error("Audio filename",repr(filename),"contains diacritics, which are not allowed.")
            filename = noDiacritics

        if filename in database["audioSource"]:
            existingSource = database["audioSource"][filename]
            if existingSource["duration"] != duration or existingSource["url"] != url:
                Alert.error(f"Audio file {filename} in event {event}: Duration ({duration}) or url ({url}) do not match parameters given previously.")
        else:
            source = {"filename": filename, "duration":duration, "event":event, "url":url}
            database["audioSource"][filename] = source

    def ExcerptDuration(excerpt: dict,sessionDuration:timedelta) -> str:
        "Return the duration of excerpt as a string."
        try:
            clip = excerpt["clips"][0].ToClipTD()
            duration = clip.Duration(sessionDuration)
        except Mp3DirectCut.TimeError as error:
            Alert.error(excerpt,"generates time error:",error.args[0])
            return "0:00"
        return Utils.TimeDeltaToStr(duration)


    # Then scan through the excerpts and add key "clips"
    for session,sessionExcerpts in Database.GroupBySession(excerpts,sessions):
        prevExcerpt = None
        if session["filename"]:
            AddAudioSource(session["filename"],session["duration"],session["event"],session["remoteMp3Url"])
            try:
                sessionDuration = Mp3DirectCut.ToTimeDelta(session["duration"])
            except ValueError:
                Alert.error(session,"has invalid duration:",repr(session["duration"]))
                sessionDuration = None
        else:
            sessionDuration = None
        del session["remoteMp3Url"]

        for x in sessionExcerpts:
            # Calculate the duration of each excerpt and handle overlapping excerpts
            startTime = x["startTime"]
            endTime = x["endTime"]
            if startTime == "Session":
                    # The session excerpt has the length of the session and has no clips key
                session = Database.FindSession(sessions,x["event"],x["sessionNumber"])
                x["duration"] = session["duration"]
                if not x["duration"]:
                    Alert.error("Deleting session excerpt",x,"since the session has no duration.")
                    deletedExcerptIDs.add(id(x))
                continue
            
            if prevExcerpt and "clips" in prevExcerpt:
                if not prevExcerpt["clips"][0].end:
                        # If the previous excerpt didn't specify an end time, use the start time of this excerpt
                    prevExcerpt["clips"][0] = prevExcerpt["clips"][0]._replace(end=startTime)
            
                prevExcerpt["duration"] = ExcerptDuration(prevExcerpt,sessionDuration)
                
                if prevExcerpt["clips"][0].ToClipTD().end > Mp3DirectCut.ToTimeDelta(startTime):
                    # startTime = prevExcerpt["clips"][0].end # This code eliminates clip overlaps
                    # x["startTime"] = prevExcerpt["endTime"]
                    if ExcerptFlag.OVERLAP not in x["flags"]:
                        Alert.warning(f"excerpt",x,"unexpectedly overlaps with the previous excerpt. This should be either changed or flagged with 'o'.")

            x["clips"] = [SplitMp3.Clip("$",startTime,endTime)]
            prevExcerpt = x
        
        if prevExcerpt:
            prevExcerpt["duration"] = ExcerptDuration(prevExcerpt,sessionDuration)

gUnattributedTeachers = Counter()
"Counts the number of times we hide a teacher's name when their attribute permission is false."

def LoadEventFile(database,eventName,directory):
    
    with open(os.path.join(directory,eventName + '.csv'),encoding='utf8') as file:
        SkipModificationLine(file)
        rawEventDesc = CSVToDictList(file,endOfSection = '<---->')
        sessions = CSVToDictList(file,removeKeys = ["seconds"],endOfSection = '<---->')
        try: # First look for a separate excerpt sheet ending in x.csv
            with open(os.path.join(directory,eventName + 'x.csv'),encoding='utf8') as excerptFile:
                SkipModificationLine(excerptFile)
                rawExcerpts = CSVToDictList(excerptFile,endOfSection = '<---->')
        except FileNotFoundError:
            rawExcerpts = CSVToDictList(file,endOfSection = '<---->')

    def RemoveUnknownTeachers(teacherList: list[str],item: dict) -> None:
        """Remove teachers that aren't present in the teacher database.
        Report an error mentioning item if this is the case."""

        unknownTeachers = [t for t in teacherList if t not in database["teacher"]]
        if unknownTeachers:
            Alert.warning("Teacher(s)",repr(unknownTeachers),"in",item,"do not appear in the Teacher sheet.")
            for t in unknownTeachers:
                teacherList.remove(t)

    eventDesc = DictFromPairs(rawEventDesc,"key","value")
    eventDesc["code"] = eventName

    for key in ["teachers","tags"]:
        eventDesc[key] = [s.strip() for s in eventDesc[key].split(';') if s.strip()]
    for key in ["sessions","excerpts","answersListenedTo","tagsApplied","invalidTags","duration"]:
        eventDesc.pop(key,None) # The spreadsheet often miscounts these items, so remove them.

    RemoveUnknownTeachers(eventDesc["teachers"],eventDesc)
    
    
    for key in ["tags","teachers"]:
        ListifyKey(sessions,key)
    for key in ["sessionNumber","excerpts"]:
        ConvertToInteger(sessions,key)

    for s in sessions:
        s["event"] = eventName
        Utils.ReorderKeys(s,["event","sessionNumber"])
        RemoveUnknownTeachers(s["teachers"],s)
        s["teachers"] = [teacher for teacher in s["teachers"] if TeacherConsent(database["teacher"],[teacher],"attribute")]

    if not gOptions.ignoreExcludes:
        sessions = FilterAndExplain(sessions,lambda s: not s["exclude"],excludeAlert,"- exclude flag Yes.")
        # Remove excluded sessions
        
    for s in sessions:
        if not gOptions.jsonNoClean:
            del s["exclude"]
    
    sessions = FilterAndExplain(sessions,lambda s: TeacherConsent(database["teacher"],s["teachers"],"indexSessions",singleConsentOK=True),excludeAlert,"due to teacher consent.")
        # Remove sessions if none of the session teachers have given consent
    database["sessions"] += sessions

    for x in rawExcerpts:
        x["fTagOrder"] = re.sub(r"\?+",lambda m: str(len(m[0]) + 1000),x["fTagOrder"])
    for key in ["teachers","qTag1","aTag1","fTags","fTagOrder"]:
        ListifyKey(rawExcerpts,key)
    ConvertToInteger(rawExcerpts,"sessionNumber")
    ConvertToInteger(rawExcerpts,"fTagOrder")
    
    includedSessions = set(s["sessionNumber"] for s in sessions)
    rawExcerpts = [x for x in rawExcerpts if x["sessionNumber"] in includedSessions]
        # Remove excerpts and annotations in sessions we didn't get consent for
        
    fileNumber = 1
    lastSession = -1
    prevExcerpt = None
    excerpts = []
    blankExcerpts = 0
    redactedTagSet = set(database["tagRedacted"])
    for x in rawExcerpts:
        if all(not value for key,value in x.items() if key != "sessionNumber"): # Skip lines which have a session number and nothing else
            blankExcerpts += 1
            continue

        x["flags"] = x.get("flags","")
        x["kind"] = x.get("kind","")

        x["qTag"] = [tag for tag in x["qTag"] if tag not in redactedTagSet] # Redact non-consenting teacher tags for both annotations and excerpts
        x["aTag"] = [tag for tag in x["aTag"] if tag not in redactedTagSet]
        x["fTags"] = [tag for tag in x["fTags"] if tag not in redactedTagSet]

        if not x["kind"]:
            x["kind"] = "Question"

        if not x["startTime"] or not database["kind"][x["kind"]]["canBeExcerpt"]:
                # If Start time is blank and it's not an audio annotation, this is an annotation to the previous excerpt
            if prevExcerpt is not None:
                AddAnnotation(database,prevExcerpt,x)
            else:
                Alert.error(f"Error: The first item in {eventName} session {x['sessionNumber']} must specify at start time.")
            continue

        x["annotations"] = []    
        x["event"] = eventName
        
        ourSession = Database.FindSession(sessions,eventName,x["sessionNumber"])
        
        if not x.pop("offTopic",False): # We don't need the off topic key after this, so throw it away with pop
            Utils.ExtendUnique(x["qTag"],ourSession["tags"])

        RemoveUnknownTeachers(x["teachers"],x)

        if not x["teachers"]:
            defaultTeacher = database["kind"][x["kind"]]["inheritTeachersFrom"]
            if defaultTeacher == "Anon": # Check if the default teacher is anonymous
                x["teachers"] = ["Anon"]
            elif defaultTeacher != "None":
                x["teachers"] = list(ourSession["teachers"]) # Make a copy to prevent subtle errors
        
        if x["kind"] == "Reading":
            AppendUnique(x["teachers"],ReferenceAuthors(x["text"]))
        
        if x["sessionNumber"] != lastSession:
            if lastSession > x["sessionNumber"]:
                Alert.error(f"Session number out of order after excerpt number {fileNumber} in session {lastSession} of",eventDesc," Will discard this excerpt.")
                continue
            lastSession = x["sessionNumber"]
            if x["startTime"] == "Session":
                fileNumber = 0
            else:
                fileNumber = 1
        else:
            fileNumber += 1 # File number counts all excerpts listed for the event
            if x["startTime"] == "Session":
                Alert.warning("Session excerpt",x,"must occur as the first excerpt in the session. Excluding this excerpt.")
                x["exclude"] = True
        x["fileNumber"] = fileNumber

        excludeReason = []
        if x["exclude"] and not gOptions.ignoreExcludes:
            excludeReason = [x," - marked for exclusion in spreadsheet"]
        elif database["kind"][x["kind"]].get("exclude",False):
            excludeReason = [x,"is of kind",x["kind"],"which is excluded in the spreadsheet"]
        elif not (TeacherConsent(database["teacher"],x["teachers"],"indexExcerpts") or database["kind"][x["kind"]]["ignoreConsent"]):
            x["exclude"] = True
            excludeReason = [x,"due to excerpt teachers",x["teachers"]]

        CheckItemContents(x,None,database["kind"][x["kind"]])

        if excludeReason:
            excludeAlert(*excludeReason)

        attributedTeachers = [teacher for teacher in x["teachers"] if TeacherConsent(database["teacher"],[teacher],"attribute") or database["kind"][x["kind"]]["ignoreConsent"]]
        for teacher in set(x["teachers"]) - set(attributedTeachers):
            if not x["exclude"]:
                gUnattributedTeachers[teacher] += 1
        x["teachers"] = attributedTeachers
        
        excerpts.append(x)
        prevExcerpt = x

    if blankExcerpts:
        Alert.notice(blankExcerpts,"blank excerpts in",eventDesc)

    for x in excerpts:
        FinalizeExcerptTags(x)

    CreateClips(excerpts,sessions,database)
    
    originalCount = len(excerpts)
    excerpts = [x for x in excerpts if not x["exclude"]]
        # Remove excluded excerpts, those we didn't get consent for, and excerpts which are too corrupted to interpret
    global gRemovedExcerpts
    gRemovedExcerpts += originalCount - len(excerpts)
    sessionsWithExcerpts = set(x["sessionNumber"] for x in excerpts)
    for unusedSession in includedSessions - sessionsWithExcerpts:
        del gDatabase["sessions"][Utils.SessionIndex(gDatabase["sessions"],eventName,unusedSession)]
        # Remove sessions with no excerpts

    if sessionsWithExcerpts:
        database["event"][eventName] = eventDesc
    else:
        Alert.caution(eventDesc,"has no non-excluded session. Removing this event from the database.")

    xNumber = 1
    lastSession = -1
    for x in excerpts:
        if x["sessionNumber"] != lastSession:
            if "clips" in x: # Does the session begin with a regular (non-session) excerpt?
                xNumber = 1
            else:
                xNumber = 0
            lastSession = x["sessionNumber"]
        else:
            xNumber += 1
        
        x["excerptNumber"] = xNumber
    
    for index in range(len(excerpts)):
        Utils.ReorderKeys(excerpts[index],["event","sessionNumber","excerptNumber","fileNumber"])
    
    if not gOptions.jsonNoClean:
        for x in excerpts:
            del x["exclude"]
            del x["startTime"]
            del x["endTime"]

    database["excerpts"] += excerpts

    eventDesc["sessions"] = len(sessions)
    eventDesc["excerpts"] = sum(1 for x in excerpts if x["fileNumber"]) # Count only non-session excerpts   

def CountInstances(source: dict|list,sourceKey: str,countDicts: List[dict],countKey: str,zeroCount = False) -> int:
    """Loop through items in a collection of dicts and count the number of appearances a given str.
        source: A dict of dicts or a list of dicts containing the items to count.
        sourceKey: The key whose values we should count.
        countDicts: A dict of dicts that we use to count the items. Each item should be a key in this dict.
        countKey: The key we add to countDict[item] with the running tally of each item.
        zeroCount: add countKey even when there are no items counted?
        return the total number of items counted"""
        
    if zeroCount:
        for key in countDicts:
            if countKey not in countDicts[key]:
                countDicts[key][countKey] = 0

    totalCount = 0
    for d in Utils.Contents(source):
        valuesToCount = d[sourceKey]
        if type(valuesToCount) != list:
            valuesToCount = [valuesToCount]
        
        removeItems = []
        for item in valuesToCount:
            try:
                countDicts[item][countKey] = countDicts[item].get(countKey,0) + 1
                totalCount += 1
            except KeyError:
                Alert.warning(f"CountInstances: Can't match key {item} from {d} in list of {sourceKey}. Will remove {item}.")
                removeItems.append(item)

        if type(d[sourceKey]) == list:
            for item in removeItems:
                valuesToCount.remove(item)
    
    return totalCount

def CountAndVerify(database):
    
    tagDB = database["tag"]
    tagCount = CountInstances(database["event"],"tags",tagDB,"eventCount")
    tagCount += CountInstances(database["sessions"],"tags",tagDB,"sessionCount")
    
    fTagCount = 0
    for x in database["excerpts"]:
        tagSet = Filter.AllTags(x)
        tagsToRemove = []
        for topic in tagSet:
            try:
                tagDB[topic]["excerptCount"] = tagDB[topic].get("excerptCount",0) + 1
                tagCount += 1
            except KeyError:
                Alert.warning(f"CountAndVerify: Tag",repr(topic),"is not defined. Will remove this tag.")
                tagsToRemove.append(topic)
        
        if tagsToRemove:
            for item in Filter.AllItems(x):
                item["tags"] = [t for t in item["tags"] if t not in tagsToRemove]
        
        for topic in x["fTags"]:
            if topic not in tagSet:
                Alert.caution(x,"specifies fTag",topic,"but this does not appear as a regular tag.")
            tagDB[topic]["fTagCount"] = tagDB[topic].get("fTagCount",0) + 1
            fTagCount += 1
    
    Alert.info(tagCount,"total tags applied.",fTagCount,"featured tags applied.")
    
    CountInstances(database["event"],"teachers",database["teacher"],"eventCount")
    CountInstances(database["sessions"],"teachers",database["teacher"],"sessionCount")
    CountInstances(database["excerpts"],"teachers",database["teacher"],"excerptCount")

    for teacher in database["teacher"].values():
        teacher["excerptCount"] = len(Filter.Teacher(teacher["teacher"])(database["excerpts"]))
        # Modify excerptCount so that it includes indirect quotes from teachers as well as attributed teachers
    
    for heading in database["topicHeading"].values():
        topicExcerpts = set()
        for topic in heading["topics"]:
            allTags = set([topic] + list(database["keyTopic"][topic]["subtags"].keys()))
            tagExcerpts = set(id(x) for x in Filter.FTag(allTags)(database["excerpts"]))
            database["keyTopic"][topic]["excerptCount"] = len(tagExcerpts)
            topicExcerpts.update(tagExcerpts)
        
        heading["excerptCount"] = len(topicExcerpts)

    if gOptions.detailedCount:
        for key in ["venue","series","format","medium"]:
            CountInstances(database["event"],key,database[key],"eventCount")
    
    # Are tags flagged Primary as needed?
    for topic in database["tag"]:
        tagDesc = database["tag"][topic]
        if tagDesc["primaries"] > 1:
            Alert.caution(f"{tagDesc['primaries']} instances of tag {tagDesc['tag']} are flagged as primary.")
        if tagDesc["copies"] > 1 and tagDesc["primaries"] == 0 and TagFlag.VIRTUAL not in tagDesc["flags"]:
            Alert.notice(f"Notice: None of {tagDesc['copies']} instances of tag {tagDesc['tag']} are designated as primary.")

def VerifyListCounts(database):
    # Check that the number of items in each numbered tag list matches the supertag item count
    tagList = database["tagDisplayList"]
    for tagIndex,subtagIndices in WalkTags(tagList,returnIndices=True):
        tag = tagList[tagIndex]["tag"]
        if not tag:
            continue
        tagSubitemCount = database["tag"][tag]["number"]
        if tagList[tagIndex]["subsumed"] or not tagSubitemCount:
            continue   # Skip virtual, subsumed and unnumbered tags
        
        finalIndex = 0
        for subtag in subtagIndices:
            finalIndexStr = tagList[subtag]["indexNumber"]
            if finalIndexStr:
                finalIndex = re.split(r"[-,]",finalIndexStr)[-1]

        if tagSubitemCount != finalIndex: # Note that this compares two strings
            Alert.warning(f'Notice: Mismatched list count in line {tagIndex} of tag list. {tag} indicates {tagSubitemCount} items, but we count {finalIndex}')

    # Check for duplicate excerpt tags
    for x in database["excerpts"]:
        if len(set(x["tags"])) != len(x["tags"]):
            Alert.caution(f"Duplicate tags in {x['event']} S{x['sessionNumber']} Q{x['excerptNumber']} {x['tags']}")

def AuditNames() -> None:
    """Write assets/NameAudit.csv summarizing the information in the Tag, Teacher, and Name sheets.
    This can be used to check consistency and see which teachers still need ordination dates."""

    teacherFields = ["attributionName","group","lineage","indexExcerpts","indexSessions","searchable","teacherPage","attribute","allowTag"]
    allFields = ["name","sortBy","nameEntry","tagEntry","teacherEntry","dateText","dateKnown","tag","supertag"] + teacherFields

    def NameData() -> dict:
        "Return a dictionary with keys for the name audit."
        d = dict.fromkeys(allFields,"")
        d["sortBy"] = 0.0
        d["nameEntry"] = d["tagEntry"] = d["teacherEntry"] = False
        d["dateKnown"] = "unknown"
        return d
    
    names = defaultdict(NameData)

    # Copy data from tags
    for supertag,subtags in WalkTags(gDatabase["tagDisplayList"]):
        if TagFlag.SORT_SUBTAGS in supertag["flags"] or supertag["tag"] == "Thai Forest Tradition":
            for tag in subtags:
                if not tag["tag"] or gDatabase["tag"][tag["tag"]]["subtags"]: # Names don't have subtags
                    continue
                n = names[gDatabase["tag"][tag["tag"]]["fullTag"]]
                n["tagEntry"] = True
                n["tag"] = gDatabase["tag"][tag["tag"]]["tag"]
                n["supertag"] = supertag["tag"]

   # Copy data from teachers
    for teacher in gDatabase["teacher"].values():
        names[teacher["fullName"]]["teacherEntry"] = True
        for field in teacherFields:
            names[teacher["fullName"]][field] = teacher[field]
    
    # Copy data from names sheet
    dateHierarchy = ["exactDate","knownMonth","knownYear","estimatedYear"]
    for name in gDatabase["name"].values():
        n = names[name["fullName"]]
        n["nameEntry"] = True
        if name["sortBy"]:
            n["sortBy"] = float(name["sortBy"])
        for dateField in dateHierarchy:
            if name[dateField]:
                n["dateText"] = name[dateField]
                n["dateKnown"] = dateField
                break

    for name,n in names.items():
        n["name"] = name

    # Check names for potential problems
    lineageExpectedSupertag = {"Thai disciples of Ajahn Chah":"Ajahn Chah lineage",
                        "Western disciples of Ajahn Chah":"Ajahn Chah lineage",
                        "Other Thai Forest":"Other Thai Forest teachers",
                        "Other Thai":"Other Thai monastics",
                        "Other Theravāda":"Other Theravāda monastics",
                        "Vajrayāna":"Mahāyāna monastics"}
    groupExpectedSupertag = {"Lay teachers":"Lay teachers"}
    namesByDate = defaultdict(list)
    for n in names.values():
        if n["tag"] and n["attributionName"] and n["tag"] != n["attributionName"]:
            Alert.notice(f"Short names don't match: tag: {repr(n['tag'])}; attributionName: {repr(n['attributionName'])}.")
        if n["supertag"] and n["lineage"] and lineageExpectedSupertag.get(n["lineage"],n["supertag"]) != n["supertag"]:
            Alert.caution(f"{n['name']} mismatch: lineage: {n['lineage']}, supertag: {n['supertag']}")
        if n["supertag"] and n["group"] and groupExpectedSupertag.get(n["group"],n["supertag"]) != n["supertag"]:
            Alert.caution(f"{n['name']} mismatch: group: {n['group']}, supertag: {n['supertag']}")
        namesByDate[n["sortBy"]].append(n)
    
    for date,namesWithDate in namesByDate.items():
        if len(namesWithDate) < 2 or not date:
            continue
        alertItems = [[n["name"] for n in namesWithDate],f"all have date {date}."]
        duplicateSupertags = Utils.Duplicates(n["supertag"] for n in namesWithDate if n["supertag"])
        for s in duplicateSupertags:
            alertItems.append(f"This will cause arbitrary sort order under supertag {s}.")
        duplicateGroups = Utils.Duplicates(n["group"] for n in namesWithDate if n["group"])
        for g in duplicateGroups:
            alertItems.append(f"This will cause arbitrary sort order in teacher group {g}.")

        if len(alertItems) > 2:
            Alert.caution(*alertItems)

    # Configure sort order
    supertags = set(n["supertag"] for n in names.values())
    supertagIndices = {}
    for tag in supertags:
        for n,tagEntry in enumerate(gDatabase["tagDisplayList"]):
            if tagEntry["tag"] == tag:
                supertagIndices[tag] = n
                break

    def SortKey(name) -> tuple:
        supertag = name["supertag"] or lineageExpectedSupertag.get(name["lineage"],None) or groupExpectedSupertag.get(name["group"],None)
        if supertag:
            if name["sortBy"]:
                return supertagIndices[supertag], name["sortBy"]
            else:
                return supertagIndices[supertag], 9999.0
        else:
            return 9999, name["sortBy"]

    nameList = sorted(names.values(),key=SortKey)
    for name in nameList:
        name["sortBy"] = SortKey(name)

    with open(Utils.PosixJoin(gOptions.prototypeDir,"assets/NameAudit.csv"), 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(allFields)
        for n in nameList:
            writer.writerow(n.values())

    Alert.info("Wrote",len(nameList),"names to assets/NameAudit.csv.")

def DumpCSV(directory:str):
    "Write a summary of gDatabase to csv files in directory."

    os.makedirs(directory,exist_ok=True)

    columns = ["event","sessionNumber","excerptNumber","indentLevel","kind","flags","teachers","text","tags","duration"]
    with open(Utils.PosixJoin(directory,"excerpts.csv"), 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        for x in gDatabase["excerpts"]:
            for i in Filter.AllSingularItems(x):
                duplicate = dict(i)
                duplicate["teachers"] = ";".join(gDatabase["teacher"][t]["attributionName"] for t in i.get("teachers",[]))
                duplicate["tags"] = ";".join(i.get("tags",[]))
                writer.writerow(duplicate.get(field,"") for field in columns)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--ignoreTeacherConsent',**Utils.STORE_TRUE,help="Ignore teacher consent flags - debugging only")
    parser.add_argument('--pendingMeansYes',**Utils.STORE_TRUE,help="Treat teacher consent pending as yes - debugging only")
    parser.add_argument('--ignoreExcludes',**Utils.STORE_TRUE,help="Ignore exclude session and excerpt flags - debugging only")
    parser.add_argument('--parseOnlySpecifiedEvents',**Utils.STORE_TRUE,help="Load only events specified by --events into the database")
    parser.add_argument('--detailedCount',**Utils.STORE_TRUE,help="Count all possible items; otherwise just count tags")
    parser.add_argument('--keepUnusedTags',**Utils.STORE_TRUE,help="Don't remove unused tags")
    parser.add_argument('--jsonNoClean',**Utils.STORE_TRUE,help="Keep intermediate data in json file for debugging")
    parser.add_argument('--explainExcludes',**Utils.STORE_TRUE,help="Print a message for each excluded/redacted excerpt")
    parser.add_argument('--auditNames',**Utils.STORE_TRUE,help="Write assets/NameAudit.csv file to check name sorting.")
    parser.add_argument('--dumpCSV',type=str,default='',help='Dump csv output files to this directory.')

def ParseArguments() -> None:
    pass

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy
gRemovedExcerpts = 0 # Count the total number of removed excerpts
gRemovedAnnotations = 0

# AlertClass for explanations of excluded excerpts. Don't show by default.
excludeAlert = Alert.AlertClass("Exclude","Exclude",printAtVerbosity=999,logging = False,lineSpacing = 1)

def main():
    """ Parse a directory full of csv files into the dictionary database and write it to a .json file.
    Each .csv sheet gets one entry in the database.
    Tags.csv and event files indicated by four digits e.g. TG2015.csv are parsed separately."""

    global gDatabase
    LoadSummary(gDatabase,os.path.join(gOptions.csvDir,"Summary.csv"))
   
    specialFiles = {'Summary','Tag','EventTemplate'}
    for fileName in os.listdir(gOptions.csvDir):
        fullPath = os.path.join(gOptions.csvDir,fileName)
        if not os.path.isfile(fullPath):
            continue
        
        baseName,extension = os.path.splitext(fileName)
        if extension.lower() != '.csv':
            continue
        
        if baseName in specialFiles or baseName[0] == '_':
            continue
        
        if re.match(".*[0-9]{4}",baseName): # Event files contain a four-digit year and are loaded after all other files
            continue
        
        def PendingBoolean(s:str):
            return s.startswith("Yes") or s.startswith("Pending")

        extraArgs = {}
        if baseName == "Teacher" and gOptions.pendingMeansYes:
            extraArgs["convertBools"] = PendingBoolean

        gDatabase[CamelCase(baseName)] = ListToDict(CSVFileToDictList(fullPath,**extraArgs))
    
    LoadTagsFile(gDatabase,os.path.join(gOptions.csvDir,"Tag.csv"))
    PrepareReferences(gDatabase["reference"])

    if gOptions.explainExcludes:
        excludeAlert.printAtVerbosity = -999

    if gOptions.events != "All":
        unknownEvents = set(gOptions.events) - set(gDatabase["summary"])
        if unknownEvents:
            Alert.warning("Events",unknownEvents,"are not listed in the Summary sheet and will not be parsed.")

    gDatabase["event"] = {}
    gDatabase["sessions"] = []
    gDatabase["audioSource"] = {}
    gDatabase["excerpts"] = []
    for event in gDatabase["summary"]:
        if not gOptions.parseOnlySpecifiedEvents or gOptions.events == "All" or event in gOptions.events:
            LoadEventFile(gDatabase,event,gOptions.csvDir)
    excludeAlert(f": {gRemovedExcerpts} excerpts and {gRemovedAnnotations} annotations in all.")
    gDatabase["sessions"] = FilterAndExplain(gDatabase["sessions"],lambda s: s["excerpts"],excludeAlert,"since it has no excerpts.")
        # Remove sessions that have no excerpts in them
    gUnattributedTeachers.pop("Anon",None)
    if gUnattributedTeachers:
        excludeAlert(f": Did not attribute excerpts to the following teachers:",dict(gUnattributedTeachers))
    if gDatabase["tagRedacted"]:
        excludeAlert(f": Redacted these tags due to teacher consent:",gDatabase["tagRedacted"])

    if not len(gDatabase["event"]):
        Alert.error("No excerpts have been parsed. Aborting.")
        sys.exit(1)

    CollectTopicHeadings(gDatabase)
    CountAndVerify(gDatabase)
    if not gOptions.keepUnusedTags:
        RemoveUnusedTags(gDatabase)
    else:
        gDatabase["tagRemoved"] = []

    PrepareTeachers(gDatabase["teacher"])

    CreateTagDisplayList(gDatabase)
    SortTags(gDatabase)
    IndexTags(gDatabase)
    if gOptions.verbose > 0:
        VerifyListCounts(gDatabase)
    CountSubtagExcerpts(gDatabase)

    if gOptions.auditNames:
        AuditNames()

    gDatabase["keyCaseTranslation"] = {key:gCamelCaseTranslation[key] for key in sorted(gCamelCaseTranslation)}

    Utils.ReorderKeys(gDatabase,["excerpts","event","sessions","audioSource","kind","category","teacher","tag","series","venue","format","medium","reference","tagDisplayList"])

    Alert.extra("Spreadsheet database contents:",indent = 0)
    Utils.SummarizeDict(gDatabase,Alert.extra)

    with open(gOptions.spreadsheetDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase, file, ensure_ascii=False, indent=2)
    
    if gOptions.dumpCSV:
        DumpCSV(gOptions.dumpCSV)

    Alert.info(Prototype.ExcerptDurationStr(gDatabase["excerpts"],countSessionExcerpts=True,sessionExcerptDuration=False),indent = 0)