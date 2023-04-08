"""A module to read csv files from ./csv and create the Database.json file used by subsequent operations"""

import os, re, csv, json, unicodedata
import Utils
from typing import List
from Prototype import QuestionDurationStr

gCamelCaseTranslation = {}
def CamelCase(input: str) -> str: 
    """Convert a string to camel case and remove all diacritics and special characters
    "Based on https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-96.php"""
    
    text = unicodedata.normalize('NFKD', input).encode('ascii', 'ignore').decode('ascii')
    text = text.replace("#"," Number") #NoCamelCase
    
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

            CamelCaseKeys(row,camelCase)
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

def ListifyKey(dictList,key,delimiter=';'):
    """Convert the values in a specific key to a list for all dictionaries in dictList.
    First, look for other keys with names like dictKey+'2', etc.
    Then split all these keys using the given delimiter, concatenate the results, and store it in dictKey.
    Remove any other keys found."""
    
    for d in dictList:
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
    
    for d in dictList:
        d[key] = int(d[key])

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
    
    CamelCaseKeys(outDict,camelCase)
    return outDict

def LoadSummary(database,summaryFileName):
    summaryList = CSVFileToDictList(summaryFileName,skipLines = 1,removeKeys = ["seconds","sortBy"],endOfSection = '<---->')
    
    for numericalKey in ["sessions","questions","answersListenedTo","tagsApplied","invalidTags"]:
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
    flags = {'.':"Virtual", '*':"Primary"}
    for item in rawTagList:
        for flag in flags:
            item[flags[flag]] = flag in item["flags"]
        
        digitFlag = re.search("[0-9]",item["flags"])
        if digitFlag:
            item["Item count"] = int(digitFlag[0])
        else:
            item["Item count"] = 0 if item["Virtual"] else 1

    # Next build the main tag dictionary
    tags = {}
    namePreference = ["abbreviation","fullTag","paliAbbreviation","pali"]
    paliPreference = ["paliAbbreviation","pali"]
    fullNamePreference = ["fullTag","pali"]
    
    # Remove any blank values from the list before looping over it
    rawTagList = [tag for tag in rawTagList if FirstValidValue(tag,namePreference)]
    
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
        tagDesc["Full Pāli"] = rawTag["pali"]
        for key in ["number","alternateTranslations","related","Virtual"]:
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
                    tags[lastTag.tag]["Subtags"] = []
                elif not tags[lastTag.tag]["Subtags"]: # But even if it's not primary, accumulate subtags if there are no prior subtags
                    lastTag.collectSubtags = True
                
                tagStack.append(lastTag)
 
        tagDesc["Subtags"] = []
        rawTag["indexNumber"] = ""
        if curTagLevel > 1:
            tagDesc["Supertags"] = [tagStack[-1].tag]
            if tagStack[-1].subtagIndex:
                if rawTag["Item count"]:
                    rawTag["indexNumber"] = str(tagStack[-1].subtagIndex)
                    tagStack[-1].Increment(rawTag["Item count"])
            if tagStack[-1].collectSubtags:
                tags[tagStack[-1].tag]["Subtags"].append(tagName)
                #print(tagStack[-1].tag,"<-",tagName,":",tags[tagStack[-1].tag]["Subtags"])
        else:
            tagDesc["Supertags"] = []

        lastTagLevel = curTagLevel
        lastTag = TagStackItem(tagName,rawTag["Primary"],bool(rawTag["number"])) # Count subtags if this tag is numerical
        
        # Subsumed tags don't have a tag entry
        if rawTag["subsumedUnder"]:
            subsumedTags[tagName] = rawTag["subsumedUnder"]
            continue
        
        # If this is a duplicate tag, insert only if the primary flag is true
        tagDesc["Copies"] = 1
        tagDesc["Primaries"] = 1 if rawTag["Primary"] else 0
        if tagName in tags:
            if rawTag["Primary"]:
                tagDesc["Copies"] += tags[tagName]["Copies"]
                tagDesc["Primaries"] += tags[tagName]["Primaries"]
                AppendUnique(tagDesc["Supertags"],tags[tagName]["Supertags"])
            else:
                tags[tagName]["Copies"] += tagDesc["Copies"]
                tags[tagName]["Primaries"] += tagDesc["Primaries"]
                AppendUnique(tags[tagName]["Supertags"],tagDesc["Supertags"])
                continue
        
        tagDesc["html file"] = Utils.slugify(tagName) + '.html'
        
        tagDesc["List index"] = rawTagIndex
        tags[tagName] = tagDesc
    
    database["tag"] = tags
    database["tagRaw"] = rawTagList
    database["tagSubsumed"] = subsumedTags

def CreateTagDisplayList(database):
    """Generate Tag_DisplayList from Tag_Raw and Tag keys in database
    Format: level, text of display line, tag to open when clicked""" 
    
    tagList = []
    for rawTag in database["tagRaw"]:
        listItem = {"level" : rawTag["level"],"indexNumber" : rawTag["indexNumber"]}
        
        if rawTag["Item count"] > 1:
            listItem["indexNumber"] = ','.join(str(n + int(rawTag["indexNumber"])) for n in range(rawTag["Item count"]))
        

        
        name = FirstValidValue(rawTag,["fullTag","pali"])
        tag = FirstValidValue(rawTag,["subsumedUnder","abbreviation","fullTag","paliAbbreviation","pali"])
        text = name
        
        try:
            questionCount = database["tag"][tag]["questionCount"]
        except KeyError:
            questionCount = 0
        subsumed = bool(rawTag["subsumedUnder"])
        
        if questionCount > 0 and not subsumed:
            text += " (" + str(questionCount) + ")"
        
        if rawTag["fullTag"] and rawTag["pali"]:
            text += " [" + rawTag["pali"] + "]"

        if subsumed:
            text += " see " + rawTag["subsumedUnder"]
            if questionCount > 0:
                text += " (" + str(questionCount) + ")"
        
        listItem["name"] = name
        listItem["pali"] = rawTag["pali"]
        listItem["questionCount"] = questionCount
        listItem["subsumed"] = subsumed
        listItem["text"] = text
            
        if rawTag["Virtual"]:
            listItem["tag"] = "" # Virtual tags don't have a display page
        else:
            listItem["tag"] = tag
        
        tagList.append(listItem)
    
    database["tagDisplayList"] = tagList
    
    # Cross-check tag indexes
    for tag in database["tag"]:
        if not database["tag"][tag]["Virtual"]:
            index = database["tag"][tag]["List index"]
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

def AddAnnotation(question: dict,annotation: dict):
    "Add an annotation to a question"
    
    if annotation["kindAnnotation"] == "Extra tags":
        question["tags"] += annotation["qTag"]
        question["tags"] += annotation["aTag"]
    
    if gOptions.ignoreAnnotations:
        return
    
    print("We don't yet support annotation",annotation["kindAnnotation"])
    
def LoadEventFile(database,eventName,directory):
    
    with open(os.path.join(directory,eventName + '.csv'),encoding='utf8') as file:
        rawEventDesc = CSVToDictList(file,endOfSection = '<---->')
        eventDesc = DictFromPairs(rawEventDesc,"key","value")
        
        for key in ["teachers","tags"]:
            eventDesc[key] = [s.strip() for s in eventDesc[key].split(';') if s.strip()]
        for key in ["sessions","questions","answersListenedTo","tagsApplied","invalidTags"]:
            eventDesc[key] = int(eventDesc[key])
        
        database["event"][eventName] = eventDesc
        
        
        sessions = CSVToDictList(file,removeKeys = ["seconds"],endOfSection = '<---->')
        
        for key in ["tags","teachers"]:
            ListifyKey(sessions,key)
        for key in ["sessionNumber","questions"]:
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

        
        rawQuestions = CSVToDictList(file)
        
        for key in ["teachers","qTag1","aTag1"]:
            ListifyKey(rawQuestions,key)
        ConvertToInteger(rawQuestions,"sessionNumber")
        
        includedSessions = set(s["sessionNumber"] for s in sessions)
        rawQuestions = [q for q in rawQuestions if q["sessionNumber"] in includedSessions]
            # Remove questions and annotations in sessions we didn't get consent for
            
        qNumber = 1 # Question number counts only questions allowed by teacher consent policies
        fileNumber = 1 
        lastSession = 0
        prevQuestion = None
        questions = []
        for q in rawQuestions:
            if not q["startTime"]: # If Start time is blank, this is an annotation to the previous question
                AddAnnotation(prevQuestion,q)
                continue
            else:
                q["kind"] = q.pop("kindAnnotation","") # Otherwise Kind / Annotation specifies the kind of question ("" = Question, "Story", or "Discussion")
            
            q["event"] = eventName
            
            ourSession = Utils.FindSession(sessions,eventName,q["sessionNumber"])
            
            q["tags"] = q["qTag"] + q["aTag"] # Combine question and session tags unless the question is off-topic
            if not q.pop("offTopic",False): # We don't need the off topic key after this, so throw it away with pop
                q["tags"] += ourSession["tags"]

            if not q["teachers"]:
                q["teachers"] = ourSession["teachers"]
            
            if q["sessionNumber"] != lastSession:
                if lastSession > q["sessionNumber"] and gOptions.verbose > 0:
                    print(f"Warning: Session number out of order after question {qNumber} in session {lastSession} of {q['event']}")
                qNumber = 0
                fileNumber = 1
                lastSession = q["sessionNumber"]
            else:
                fileNumber += 1 # File number counts all questions listed for the event
            
            if TeacherConsent(database["teacher"],q["teachers"],"indexQuestions") and (not q["exclude"] or gOptions.ignoreExcludes):                   
                qNumber += 1 # Question number counts only questions allowed by teacher consent and exclusion policies
                q["exclude"] = False
            else:
                q["exclude"] = True # Convert this value to boolean
            
            q["questionNumber"] = qNumber
            q["fileNumber"] = fileNumber
            
            if not gOptions.jsonNoClean:
                del q["qTag"]
                del q["aTag"]
                del q["aListen"]
                
            questions.append(q)
            prevQuestion = q
        
        for qIndex, q in enumerate(questions):
            startTime = q["startTime"]
            
            endTime = q["endTime"]
            if not endTime:
                try:
                    if questions[qIndex + 1]["sessionNumber"] == q["sessionNumber"]:
                        endTime = questions[qIndex + 1]["startTime"]
                except IndexError:
                    pass
            
            if not endTime:
                endTime = Utils.FindSession(sessions,eventName,q["sessionNumber"])["duration"]
                
            q["duration"] = Utils.TimeDeltaToStr(Utils.StrToTimeDelta(endTime) - Utils.StrToTimeDelta(startTime))
        
        for index in range(len(questions)):
            questions[index] = ReorderKeys(questions[index],["event","sessionNumber","questionNumber","fileNumber"])
        
        removedQuestions = [q for q in questions if q["exclude"]]
        questions = [q for q in questions if not q["exclude"]]
            # Remove excluded questions and those we didn't get consent for
        
        if not gOptions.jsonNoClean:
            for q in questions:
                del q["exclude"]
        
        for q in removedQuestions: # Redact information about these questions
            for key in ["teachers","tags","questionText","qTag","aTag","aListen","questionNumber","exclude","kind","duration"]:
                q.pop(key,None)
        
        sessionsWithQuestions = set(q["sessionNumber"] for q in questions)
        sessions = [s for s in sessions if s["sessionNumber"] in sessionsWithQuestions]
            # Remove sessions that have no questions in them
        
        database["sessions"] += sessions
        database["questions"] += questions
        database["questionsRedacted"] += removedQuestions
        

def CountInstances(source,sourceKey,countDicts,countKey,zeroCount = False):
    """Loop through items in a collection of dicts and count the number of appearances a given str.
        source: A dict of dicts or a list of dicts containing the items to count.
        sourceKey: The key whose values we should count. This can be either a str or a list of strs.
        countDict: A dict of dicts that we use to count the items. Each item should be a key in this dict.
        countKey: The key we add to countDict[item] with the running tally of each item."""
    
    if zeroCount:
        for key in countDicts:
            if countKey not in countDicts[key]:
                countDicts[key][countKey] = 0
    
    if type(source) == list:
        iterator = range(len(source))
    elif type(source) == dict:
        iterator = source.keys()
    else:
        raise TypeError("CountInstances: source must be a list or a dict.")
    
    for index in iterator:
        d = source[index]
        valuesToCount = d[sourceKey]
        if type(valuesToCount) != list:
            valuesToCount = [valuesToCount]
        
        for item in valuesToCount:
            try:
                if countKey not in countDicts[item]:
                    countDicts[item][countKey] = 0
                countDicts[item][countKey] += 1
            except KeyError:
                print(f"CountInstances: Can't match key {item} from {d} in list of {sourceKey}")
            
    

def CountAndVerify(database):
    
    CountInstances(database["event"],"tags",database["tag"],"Event count",gOptions.zeroCount)
    CountInstances(database["sessions"],"tags",database["tag"],"Session count",gOptions.zeroCount)
    CountInstances(database["questions"],"tags",database["tag"],"questionCount",gOptions.zeroCount)
    
    if gOptions.detailedCount:
        for key in ["venue","series","format","medium"]:
            CountInstances(database["event"],key,database[key],"Event count",gOptions.zeroCount)
        
        CountInstances(database["event"],"teachers",database["teacher"],"Event count",gOptions.zeroCount)
        CountInstances(database["sessions"],"teachers",database["teacher"],"Session count",gOptions.zeroCount)
        CountInstances(database["questions"],"teachers",database["teacher"],"questionCount",gOptions.zeroCount)
    
    # Are tags flagged Primary as needed?
    if gOptions.verbose >= 1:
        for tag in database["tag"]:
            tagDesc = database["tag"][tag]
            if tagDesc["Primaries"] > 1:
                print(f"Warning: {tagDesc['Primaries']} instances of tag {tagDesc['tag']} are flagged as primary.")
            if gOptions.verbose >= 2 and tagDesc["Copies"] > 1 and tagDesc["Primaries"] == 0 and not tagDesc["Virtual"]:
                print(f"Notice: None of {tagDesc['Copies']} instances of tag {tagDesc['tag']} are designated as primary.")

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
    
    # Check for duplicate question tags
    for q in database["questions"]:
        if len(set(q["tags"])) != len(q["tags"]) and gOptions.verbose > 1:
            print(f"Duplicate tags in {q['event']} S{q['sessionNumber']} Q{q['questionNumber']} {q['tags']}")
    

def AddArguments(parser):
    "Add command-line arguments used by this module"
    
    parser.add_argument('--ignoreTeacherConsent',action='store_true',help="Ignore teacher consent flags - debugging only")
    parser.add_argument('--ignoreExcludes',action='store_true',help="Ignore exclude session and question flags - debugging only")
    parser.add_argument('--zeroCount',action='store_true',help="Write count=0 keys to json file; otherwise write only non-zero keys")
    parser.add_argument('--detailedCount',action='store_true',help="Count all possible items; otherwise just count tags")
    parser.add_argument('--jsonNoClean',action='store_true',help="Keep intermediate data in json file for debugging")
    parser.add_argument('--ignoreAnnotations',action='store_true',help="Don't process story and reference annotations")

gOptions = None

def main(clOptions,database):
    """ Parse a directory full of csv files into the dictionary database and write it to a .json file.
    Each .csv sheet gets one entry in the database.
    Tags.csv and event files indicated by four digits e.g. TG2015.csv are parsed separately."""
    
    global gOptions
    gOptions = clOptions
    gOptions.ignoreAnnotations = True # For the time being (Winter Retreat 2023), ignore annotations to avoid too much coding
    
    LoadSummary(database,os.path.join(gOptions.csvDir,"Summary.csv"))
   
    specialFiles = {'Summary','Tag','EventTemplate'} #NoCamelCase
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
    database["questions"] = []
    database["questionsRedacted"] = []
    for event in database["summary"]:
        LoadEventFile(database,event,gOptions.csvDir)
    
    CountAndVerify(database)
    CreateTagDisplayList(database)
    if gOptions.verbose > 0:
        VerifyListCounts(database)
        
    # database = ReorderKeys(database,["tagDisplayList","tag","tagRaw"])
    if not gOptions.jsonNoClean:
        del database["tagRaw"]

    if gOptions.verbose >= 2:
        print("Final database contents:")
        for item in database:
            print(item + ": "+str(len(database[item])))
    
    with open(gOptions.spreadsheetDatabase, 'w', encoding='utf-8') as file:
        json.dump(database, file, ensure_ascii=False, indent=2)
    
    if gOptions.verbose > 0:
        print("   " + QuestionDurationStr(database["questions"]))

    CamelCaseKeys(database,False)
    for stuff in database.values():
        try:
            firstItem = stuff[0]
        except KeyError:
            firstItem = next(iter(stuff))
        
        try:
            CamelCaseKeys(firstItem,False)
        except AttributeError:
            pass

    CamelCase("QTag") #NoCamelCase
    CamelCase("ATag") #NoCamelCase
    CamelCase("Tag_Raw") #NoCamelCase
    print(len(gCamelCaseTranslation),gCamelCaseTranslation)
    with open('tools/massRename/CamelCaseTranslation.json', 'w', encoding='utf-8') as file:
        json.dump(gCamelCaseTranslation,file,ensure_ascii=False, indent='\t')