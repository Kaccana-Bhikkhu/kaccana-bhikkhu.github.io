"""A module to read csv files from ./csv and create the Database.json file used by subsequent operations"""

import os, re, csv, json, unicodedata
import Utils
from typing import List
from Prototype import ExcerptDurationStr

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
    This is the standard way of encoding boolean values in the csv files from AP QA Archive main."""
    
    return text[:3] == 'Yes'

def AppendUnique(ioList,inToAppend):
    "Append values to a list unless they are already in it"
    for item in inToAppend:
        if not item in ioList:
            ioList.append(item)

def ReorderKeys(inDict,firstKeys = [],lastKeys = []):
    "Return a dict with the same data, but reordered keys"
    
    outDict = {}
    for key in firstKeys:
        outDict[key] = inDict[key]
        
    for key in inDict:
        if key not in lastKeys:
            outDict[key] = inDict[key]
    
    for key in lastKeys:
        outDict[key] = inDict[key]
    
    return outDict

def CSVToDictList(file,skipLines = 0,removeKeys = [],endOfSection = None,convertBools = True,camelCase = True):
    for n in range(skipLines):
        file.readline()
                
    reader = csv.DictReader(file)
    output = []
    for row in reader:
        firstDictValue = row[next(iter(row))].strip()
        if firstDictValue == endOfSection:
            break
        elif not BlankDict(row):
            if not firstDictValue and gOptions.verbose > 0:
                print("WARNING: blank first field in",row)
        
            # Increase robustness by stripping values and keys
            for key in list(row):
                row[key] = row[key].strip()
                if key != key.strip():
                    row[key.strip()] = row.pop(key)
            
            if convertBools:
                for key in row:
                    if key[-1:] == '?':
                        row[key] = BooleanValue(row[key])
            
            if camelCase:
                CamelCaseKeys(row)
            output.append(row)
            

    
    removeKeys.append("")
    for key in removeKeys:
        for row in output:
            row.pop(key,None)
    
    return output
    
def CSVFileToDictList(fileName,*args,**kwArgs):
    """Read a CSV file and convert it to a list of dictionaries"""
    
    with open(fileName,encoding='utf8') as file:
        return CSVToDictList(file,*args,**kwArgs)

def ListifyKey(dictList: list|dict,key: str,delimiter:str = ';') -> None:
    """Convert the values in a specific key to a list for all dictionaries in dictList.
    First, look for other keys with names like dictKey+'2', etc.
    Then split all these keys using the given delimiter, concatenate the results, and store it in dictKey.
    Remove any other keys found."""
    
    for d in Utils.Contents(dictList):
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

def ConvertToInteger(dictList,key):
    "Convert the values in key to ints"
    
    for d in Utils.Contents(dictList):
        try:
            d[key] = int(d[key])
        except ValueError as err:
            if not d[key]:
                d[key] = None
            else:
                raise err

def ListToDict(inList,key = None):
    """Convert a list of dicts to a dict of dicts using key. If key is None, use the first key
    Throw an exception if there are duplicate values."""
    
    if key is None:
        key = next(iter(inList[0]))
    
    outDict = {}
    for item in inList:
        newKey = item[key]
        if newKey in outDict:
            raise KeyError("ListToDict: Duplicate key "+str(newKey))
        
        outDict[newKey] = item
    
    return outDict

def DictFromPairs(inList,keyKey,valueKey,camelCase = True):
    "Convert a list of dicts to a dict by taking a single key/value pair from each dict."
    
    outDict = {}
    for item in inList:
        newKey = item[keyKey]
        if newKey in outDict:
            raise KeyError("DictFromPairs: Duplicate key "+str(newKey))
        
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
    ListifyKey(rawTagList,"related")
    ConvertToInteger(rawTagList,"level")
    
    # Convert the flag codes to boolean values
    flags = {'.':"virtual", '*':"primary"}
    for item in rawTagList:
        for flag in flags:
            item[flags[flag]] = flag in item["flags"]
        
        digitFlag = re.search("[0-9]",item["flags"])
        if digitFlag:
            item["itemCount"] = int(digitFlag[0])
        else:
            item["itemCount"] = 0 if item["virtual"] else 1

    # Next build the main tag dictionary
    tags = {}
    namePreference = ["abbreviation","fullTag","paliAbbreviation","pali"]
    paliPreference = ["paliAbbreviation","pali"]
    fullNamePreference = ["fullTag","pali"]
    
    # Remove any blank values from the list before looping over it
    rawTagList = [tag for tag in rawTagList if FirstValidValue(tag,namePreference)]
    
    # Redact tags for teachers who haven't given consent - teacher names are never abbreviated, so use fullTag
    unallowedTags = [teacher["fullName"] for abbrev,teacher in database["teacher"].items() if not TeacherConsent(database["teacher"],[abbrev],"allowTag")]
    redactedTags = [tag["fullTag"] for tag in rawTagList if tag["fullTag"] in unallowedTags]
    rawTagList = [tag for tag in rawTagList if tag["fullTag"] not in unallowedTags]

    subsumedTags = {} # A dictionary of subsumed tags for future reference
    
    tagStack = [] # Supertag ancestry stack
    
    lastTagLevel = 1
    lastTag = TagStackItem("")
    rawTagIndex = -1
    for rawTag in rawTagList:
        rawTagIndex += 1
        tagName = FirstValidValue(rawTag,namePreference)
        tagPaliName = FirstValidValue(rawTag,paliPreference,"")
        
        tagDesc = {}
        tagDesc["tag"] = tagName
        tagDesc["pali"] = tagPaliName
        tagDesc["fullTag"] = FirstValidValue(rawTag,fullNamePreference)
        tagDesc["fullPali"] = rawTag["pali"]
        for key in ["number","alternateTranslations","related","virtual"]:
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
                elif not tags[lastTag.tag]["subtags"]: # But even if it's not primary, accumulate subtags if there are no prior subtags
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
                #print(tagStack[-1].tag,"<-",tagName,":",tags[tagStack[-1].tag]["subtags"])
        else:
            tagDesc["supertags"] = []

        lastTagLevel = curTagLevel
        lastTag = TagStackItem(tagName,rawTag["primary"],bool(rawTag["number"])) # Count subtags if this tag is numerical
        
        # Subsumed tags don't have a tag entry
        if rawTag["subsumedUnder"]:
            subsumedTags[tagName] = rawTag["subsumedUnder"]
            continue
        
        # If this is a duplicate tag, insert only if the primary flag is true
        tagDesc["copies"] = 1
        tagDesc["primaries"] = 1 if rawTag["primary"] else 0
        if tagName in tags:
            if rawTag["primary"]:
                tagDesc["copies"] += tags[tagName]["copies"]
                tagDesc["primaries"] += tags[tagName]["primaries"]
                AppendUnique(tagDesc["supertags"],tags[tagName]["supertags"])
            else:
                tags[tagName]["copies"] += tagDesc["copies"]
                tags[tagName]["primaries"] += tagDesc["primaries"]
                AppendUnique(tags[tagName]["supertags"],tagDesc["supertags"])
                continue
        
        tagDesc["htmlFile"] = Utils.slugify(tagName) + '.html'
        
        tagDesc["listIndex"] = rawTagIndex
        tags[tagName] = tagDesc
    
    database["tag"] = tags
    database["tagRaw"] = rawTagList
    database["tagSubsumed"] = subsumedTags
    database["tagRedacted"] = redactedTags

def CreateTagDisplayList(database):
    """Generate Tag_DisplayList from Tag_Raw and Tag keys in database
    Format: level, text of display line, tag to open when clicked""" 
    
    tagList = []
    for rawTag in database["tagRaw"]:
        listItem = {"level" : rawTag["level"],"indexNumber" : rawTag["indexNumber"]}
        
        if rawTag["itemCount"] > 1:
            listItem["indexNumber"] = ','.join(str(n + int(rawTag["indexNumber"])) for n in range(rawTag["itemCount"]))
        
        name = FirstValidValue(rawTag,["fullTag","pali"])
        tag = FirstValidValue(rawTag,["subsumedUnder","abbreviation","fullTag","paliAbbreviation","pali"])
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
            
        if rawTag["virtual"]:
            listItem["tag"] = "" # Virtual tags don't have a display page
        else:
            listItem["tag"] = tag
        
        tagList.append(listItem)
    
    database["tagDisplayList"] = tagList
    
    # Cross-check tag indexes
    for tag in database["tag"]:
        if not database["tag"][tag]["virtual"]:
            index = database["tag"][tag]["listIndex"]
            assert tag == tagList[index]["tag"],f"Tag {tag} has index {index} but TagList[{index}] = {tagList[index]['tag']}" 
      

def TeacherConsent(teacherDB: List[dict], teachers: List[str], policy: str) -> bool:
    "Scan teacherDB to see if all teachers in the list have consented to the given policy. Return False if not."
    
    if gOptions.ignoreTeacherConsent:
        return True
    
    consent = True
    for teacher in teachers:
        if not teacherDB[teacher][policy]:
            consent = False
        
    return consent

def AddAnnotation(database: dict, excerpt: dict,annotation: dict) -> None:
    """Add an annotation to a excerpt."""
    
    ### Need to fix so that Extra tags assigns tags to annotations
    if annotation["kind"] == "Extra tags":
        for prevAnnotation in reversed(excerpt["annotations"]): # look backwards and add these tags to the first annotation that supports them
            if "tags" in prevAnnotation:
                prevAnnotation["tags"] += annotation["qTag"]
                prevAnnotation["tags"] += annotation["aTag"] # annotations don't distinguish between q and a tags
                return
        
        excerpt["qTag"] += annotation["qTag"] # If no annotation takes the tags, give them to the excerpt
        excerpt["aTag"] += annotation["aTag"]
        return
    
    if gOptions.ignoreAnnotations:
        return
    
    if annotation["exclude"]:
        return
    
    if not annotation["kind"]:
        if gOptions.verbose >= -1:
            print("   Error: Annotations must specify a kind; defaulting to Comment. ",annotation["text"])
        annotation["kind"] = kind = "Comment"
    kind = database["kind"][annotation["kind"]]
    
    keysToRemove = ["sessionNumber","offTopic","aListen","exclude","qTag","aTag"]
    
    if kind["takesTeachers"]:
        if not annotation["teachers"]:
            defaultTeacher = kind["inheritTeacherFrom"]
            if defaultTeacher == "Anon": # Check if the default teacher is anonymous
                annotation["teachers"] = ["Anon"]
            elif defaultTeacher == "Excerpt":
                annotation["teachers"] = excerpt["teachers"]
            elif defaultTeacher == "Session":
                ourSession = Utils.FindSession(database["sessions"],excerpt["event"],excerpt["sessionNumber"])
                annotation["teachers"] = ourSession["teachers"]
        
        if not TeacherConsent(database["teacher"],annotation["teachers"],"indexExcerpts"):
            excerpt["exclude"] = True # If a teacher of one of the annotations hasn't given consent, we redact the excerpt itself
            return 
        
        teacherList = [teacher for teacher in annotation["teachers"] if TeacherConsent(database["teacher"],[teacher],"attribute")]
        if set(teacherList) == set(excerpt["teachers"]):
            teacherList = []
        
        annotation["teachers"] = teacherList
    else:
        keysToRemove.append("teachers")
    
    if kind["takesTags"]:
        annotation["tags"] = annotation["qTag"] + annotation["aTag"] # Annotations don't distiguish between q and a tags
    
    if not kind["takesTimes"]:
        keysToRemove += ["startTime","endTime"]
    
    for key in keysToRemove:
        annotation.pop(key,None)    # Remove keys that aren't relevant for annotations
    
    annotation["indentLevel"] = len(annotation["flags"].split("-"))
    
    excerpt["annotations"].append(annotation)
    
def LoadEventFile(database,eventName,directory):
    
    with open(os.path.join(directory,eventName + '.csv'),encoding='utf8') as file:
        rawEventDesc = CSVToDictList(file,endOfSection = '<---->')
        eventDesc = DictFromPairs(rawEventDesc,"key","value")
        
        for key in ["teachers","tags"]:
            eventDesc[key] = [s.strip() for s in eventDesc[key].split(';') if s.strip()]
        for key in ["sessions","excerpts","answersListenedTo","tagsApplied","invalidTags"]:
            eventDesc[key] = int(eventDesc[key])
        
        database["event"][eventName] = eventDesc
        
        sessions = CSVToDictList(file,removeKeys = ["seconds"],endOfSection = '<---->')
        
        for key in ["tags","teachers"]:
            ListifyKey(sessions,key)
        for key in ["sessionNumber","excerpts"]:
            ConvertToInteger(sessions,key)
            
        if not gOptions.ignoreExcludes:
            sessions = [s for s in sessions if not s["exclude"]] # Remove excluded sessions
            # Remove excluded sessions
            
        for s in sessions:
            s["event"] = eventName
            s = ReorderKeys(s,["event","sessionNumber"])
            if not gOptions.jsonNoClean:
                del s["exclude"]
            
            
        sessions = [s for s in sessions if TeacherConsent(database["teacher"],s["teachers"],"indexSessions")]
            # Remove sessions we didn't get consent for
        database["sessions"] += sessions
        
        rawExcerpts = CSVToDictList(file)
        
        for key in ["teachers","qTag1","aTag1"]:
            ListifyKey(rawExcerpts,key)
        ConvertToInteger(rawExcerpts,"sessionNumber")
        
        includedSessions = set(s["sessionNumber"] for s in sessions)
        rawExcerpts = [x for x in rawExcerpts if x["sessionNumber"] in includedSessions]
            # Remove excerpts and annotations in sessions we didn't get consent for
            
        fileNumber = 1
        lastSession = -1
        prevExcerpt = None
        excerpts = []
        redactedTagSet = set(database["tagRedacted"])
        for x in rawExcerpts:
            
            x["qTag"] = [tag for tag in x["qTag"] if tag not in redactedTagSet] # Redact non-consenting teacher tags for both annotations and excerpts
            x["aTag"] = [tag for tag in x["aTag"] if tag not in redactedTagSet]

            if not x["startTime"]: # If Start time is blank, this is an annotation to the previous excerpt
                AddAnnotation(database,prevExcerpt,x)
                continue
            else:
                x["annotations"] = []
            
            if not x["kind"]:
                x["kind"] = "Question"
            x["event"] = eventName
            
            ourSession = Utils.FindSession(sessions,eventName,x["sessionNumber"])
            
            if not x.pop("offTopic",False): # We don't need the off topic key after this, so throw it away with pop
                x["qTag"] = ourSession["tags"] + x["qTag"]

            if not x["teachers"]:
                defaultTeacher = database["kind"][x["kind"]]["inheritTeacherFrom"]
                if defaultTeacher == "Anon": # Check if the default teacher is anonymous
                    x["teachers"] = ["Anon"]
                else:
                    x["teachers"] = ourSession["teachers"]
            
            if x["sessionNumber"] != lastSession:
                fileNumber = 1
                lastSession = x["sessionNumber"]
            else:
                fileNumber += 1 # File number counts all excerpts listed for the event
            
            if (TeacherConsent(database["teacher"],x["teachers"],"indexExcerpts") or x["kind"] == "Reading") and (not x["exclude"] or gOptions.ignoreExcludes):
                x["exclude"] = False
            else:
                x["exclude"] = True
            
            x["teachers"] = [teacher for teacher in x["teachers"] if TeacherConsent(database["teacher"],[teacher],"attribute")]
            
            x["fileNumber"] = fileNumber
                
            excerpts.append(x)
            prevExcerpt = x
        
        for xIndex, x in enumerate(excerpts):
            
            # Combine all tags into a single list, but keep track of how many qTags there are
            x["tags"] = x["qTag"] + x["aTag"]
            x["qTagCount"] = len(x["qTag"])
            if not gOptions.jsonNoClean:
                del x["qTag"]
                del x["aTag"]
                del x["aListen"]

            startTime = x["startTime"]
            
            endTime = x["endTime"]
            if not endTime:
                try:
                    if excerpts[xIndex + 1]["sessionNumber"] == x["sessionNumber"]:
                        endTime = excerpts[xIndex + 1]["startTime"]
                except IndexError:
                    pass
            
            if not endTime:
                endTime = Utils.FindSession(sessions,eventName,x["sessionNumber"])["duration"]
                
            x["duration"] = Utils.TimeDeltaToStr(Utils.StrToTimeDelta(endTime) - Utils.StrToTimeDelta(startTime))
        
        removedExcerpts = [x for x in excerpts if x["exclude"]]
        excerpts = [x for x in excerpts if not x["exclude"]]
            # Remove excluded excerpts and those we didn't get consent for
        
        xNumber = 1
        lastSession = -1
        for x in excerpts:
            if x["sessionNumber"] != lastSession:
                if lastSession > x["sessionNumber"] and gOptions.verbose > 0:
                    print(f"Warning: Session number out of order after excerpt {xNumber} in session {lastSession} of {x['event']}")
                xNumber = 1
                lastSession = x["sessionNumber"]
            else:
                xNumber += 1
            
            x["excerptNumber"] = xNumber
        
        for index in range(len(excerpts)):
            excerpts[index] = ReorderKeys(excerpts[index],["event","sessionNumber","excerptNumber","fileNumber"])
        
        if not gOptions.jsonNoClean:
            for x in excerpts:
                del x["exclude"]
        
        for x in removedExcerpts: # Redact information about these excerpts
            for key in ["teachers","tags","text","qTag","aTag","aListen","excerptNumber","exclude","kind","duration"]:
                x.pop(key,None)
        
        sessionsWithExcerpts = set(x["sessionNumber"] for x in excerpts)
        sessions = [s for s in sessions if s["sessionNumber"] in sessionsWithExcerpts]
            # Remove sessions that have no excerpts in them
        
        database["excerpts"] += excerpts
        database["excerptsRedacted"] += removedExcerpts
        

def CountInstances(source: dict|list,sourceKey: str,countDicts: List[dict],countKey: str,zeroCount = False):
    """Loop through items in a collection of dicts and count the number of appearances a given str.
        source: A dict of dicts or a list of dicts containing the items to count.
        sourceKey: The key whose values we should count.
        countDicts: A dict of dicts that we use to count the items. Each item should be a key in this dict.
        countKey: The key we add to countDict[item] with the running tally of each item.
        zeroCount: add countKey even when there are no items counted? """
        
    if zeroCount:
        for key in countDicts:
            if countKey not in countDicts[key]:
                countDicts[key][countKey] = 0

    for d in Utils.Contents(source):
        valuesToCount = d[sourceKey]
        if type(valuesToCount) != list:
            valuesToCount = [valuesToCount]
        
        for item in valuesToCount:
            try:
                countDicts[item][countKey] = countDicts[item].get(countKey,0) + 1
            except KeyError:
                print(f"CountInstances: Can't match key {item} from {d} in list of {sourceKey}")

def CountAndVerify(database):
    
    tagDB = database["tag"]
    CountInstances(database["event"],"tags",tagDB,"eventCount")
    CountInstances(database["sessions"],"tags",tagDB,"sessionCount")
    
    for x in database["excerpts"]:
        tagSet = Utils.AllTags(x)
        for tag in tagSet:
            tagDB[tag]["excerptCount"] = tagDB[tag].get("excerptCount",0) + 1
        
    if gOptions.detailedCount:
        for key in ["venue","series","format","medium"]:
            CountInstances(database["event"],key,database[key],"Event count")
        
        CountInstances(database["event"],"teachers",database["teacher"],"Event count")
        CountInstances(database["sessions"],"teachers",database["teacher"],"Session count")
        CountInstances(database["excerpts"],"teachers",database["teacher"],"excerptCount")
    
    # Are tags flagged Primary as needed?
    if gOptions.verbose >= 1:
        for tag in database["tag"]:
            tagDesc = database["tag"][tag]
            if tagDesc["primaries"] > 1:
                print(f"Warning: {tagDesc['primaries']} instances of tag {tagDesc['tag']} are flagged as primary.")
            if gOptions.verbose >= 2 and tagDesc["copies"] > 1 and tagDesc["primaries"] == 0 and not tagDesc["virtual"]:
                print(f"Notice: None of {tagDesc['copies']} instances of tag {tagDesc['tag']} are designated as primary.")

def VerifyListCounts(database):
    # Check that the number of items in each numbered tag list matches the supertag item count
    for index, tagInfo in enumerate(database["tagDisplayList"]):
        tag = tagInfo["tag"]
        if not tag or tagInfo["subsumed"] or not database["tag"][tag]["number"]:
            continue   # Skip virtual, subsumed and unnumbered tags
        
        subtagLevel = tagInfo["level"] + 1 # Count tags one level deeper than us
        lookaheadIndex = index + 1
        listCount = 0
        # Loop through all subtags of this tag
        while lookaheadIndex < len(database["tagDisplayList"]) and database["tagDisplayList"][lookaheadIndex]["level"] >= subtagLevel:
            if database["tagDisplayList"][lookaheadIndex]["level"] == subtagLevel and database["tagDisplayList"][lookaheadIndex]["indexNumber"]:
                listCount = int(database["tagDisplayList"][lookaheadIndex]["indexNumber"].split(',')[-1])
                    # Convert the last item in this comma-separated list to an integer
            lookaheadIndex += 1
        
        if listCount != int(database["tag"][tag]["number"]):
            print(f'Notice: Mismatched list count in line {index} of tag list. {tag} indicates {database["tag"][tag]["number"]} items, but we count {listCount}')
    
    # Check for duplicate excerpt tags
    for x in database["excerpts"]:
        if len(set(x["tags"])) != len(x["tags"]) and gOptions.verbose > 1:
            print(f"Duplicate tags in {x['event']} S{x['sessionNumber']} Q{x['excerptNumber']} {x['tags']}")
    

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--ignoreTeacherConsent',action='store_true',help="Ignore teacher consent flags - debugging only")
    parser.add_argument('--ignoreExcludes',action='store_true',help="Ignore exclude session and excerpt flags - debugging only")
    parser.add_argument('--parseOnlySpecifiedEvents',action='store_true',help="Load only events specified by --events into the database")
    parser.add_argument('--detailedCount',action='store_true',help="Count all possible items; otherwise just count tags")
    parser.add_argument('--jsonNoClean',action='store_true',help="Keep intermediate data in json file for debugging")
    parser.add_argument('--ignoreAnnotations',action='store_true',help="Don't process annotations")

gOptions = None

def main(clOptions,database):
    """ Parse a directory full of csv files into the dictionary database and write it to a .json file.
    Each .csv sheet gets one entry in the database.
    Tags.csv and event files indicated by four digits e.g. TG2015.csv are parsed separately."""
    
    global gOptions
    gOptions = clOptions
    #gOptions.ignoreAnnotations = True # For the time being (Winter Retreat 2023), ignore annotations to avoid too much coding
    
    LoadSummary(database,os.path.join(gOptions.csvDir,"Summary.csv"))
   
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
        
        database[CamelCase(baseName)] = ListToDict(CSVFileToDictList(fullPath))
    
    LoadTagsFile(database,os.path.join(gOptions.csvDir,"Tag.csv"))
    
    database["event"] = {}
    database["sessions"] = []
    database["excerpts"] = []
    database["excerptsRedacted"] = []
    for event in database["summary"]:
        if not clOptions.parseOnlySpecifiedEvents or clOptions.events == "All" or event in clOptions.events:
            LoadEventFile(database,event,gOptions.csvDir)

    CountAndVerify(database)
    CreateTagDisplayList(database)
    if gOptions.verbose > 0:
        VerifyListCounts(database)
    
    database["keyCaseTranslation"] = gCamelCaseTranslation
    if not gOptions.jsonNoClean:
        del database["tagRaw"]

    if gOptions.verbose >= 2:
        print("Final database contents:")
        for item in database:
            print(item + ": "+str(len(database[item])))
    
    with open(gOptions.spreadsheetDatabase, 'w', encoding='utf-8') as file:
        json.dump(database, file, ensure_ascii=False, indent=2)
    
    if gOptions.verbose > 0:
        print("   " + ExcerptDurationStr(database["excerpts"]))