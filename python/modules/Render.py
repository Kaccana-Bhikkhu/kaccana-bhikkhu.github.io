"""Render the text of each excerpt in the database with its annotations to html using the pryatemp templates in database["Kind"].
The only remaining work for Prototype.py to do is substitute the list of teachers for {attribtuion}, {attribtuion2}, and {attribtuion3} when needed."""

from __future__ import annotations

import json, re
import markdown
from markdown_newtab_remote import NewTabRemoteExtension
from typing import Tuple, Type, Callable
import pyratemp
from functools import lru_cache
import ParseCSV, Prototype, Utils, Alert, Link
import Html2 as Html

def FStringToPyratemp(fString: str) -> str:
    """Convert a template in our psuedo-f string notation to a pyratemp template"""
    prya = fString.replace("{","$!").replace("}","!$")
    
    return prya

def ApplyToBodyText(transform: Callable[...,Tuple[str,int]],passItemAsSecondArgument: bool = False) -> int:
    """Apply operation transform on each string considered body text in the database.
    If passItemAsSecondArgument is True, transform has the form transform(bodyText,item), otherwise transform(bodyText).
    transform returns a tuple (changedText,changeCount). Return the total number of changes made."""
    
    if not passItemAsSecondArgument:
        twoVariableTransform = lambda bodyStr,_: transform(bodyStr)
    else:
        twoVariableTransform = transform

    changeCount = 0
    for x in gDatabase["excerpts"]:
        x["body"],count = twoVariableTransform(x["body"],x)
        changeCount += count
        for a in x["annotations"]:
            a["body"],count = twoVariableTransform(a["body"],a)
            changeCount += count

    for e in gDatabase["event"].values():
        e["description"],count = twoVariableTransform(e["description"],e)
        changeCount += count

    for s in gDatabase["series"].values():
        s["description"],count = twoVariableTransform(s["description"],s)
        changeCount += count

    return changeCount
    

def ExtractAnnotation(form: str) -> Tuple[str,str]:
    """Split the form into body and attribution parts, which are separated by ||.
    Example: Story|| told by @!teachers!@||: @!text!@ ->
    body = Story||{attribution}||:: @!text!@
    attribution = told by @!teachers!@"""

    parts = form.split("++")
    if len(parts) > 1:
        parts.insert(2,"</b>")
        parts.insert(1,"<b>")
        form = ''.join(parts)

    parts = form.split("||")
    if len(parts) == 1:
        return form, ""

    attribution = parts[1]
    parts[1] = "{attribution}"
    return "".join(parts), attribution

def PrepareTemplates():
    ParseCSV.ListifyKey(gDatabase["kind"],"form1")
    ParseCSV.ConvertToInteger(gDatabase["kind"],"defaultForm")

    for kind in gDatabase["kind"].values():
        kind["form"] = [FStringToPyratemp(f) for f in kind["form"]]

        kind["body"] = []; kind["attribution"] = []
        for form in kind["form"]:
            
            body, attribution = ExtractAnnotation(form)
            kind["body"].append(body)
            kind["attribution"].append(attribution)

def AddImplicitAttributions() -> None:
    "If an excerpt or annotation of kind Reading doesn't have a Read by annotation, attribute it to the session or excerpt teachers"
    for session,x in Utils.PairWithSession(gDatabase["excerpts"]):
        if x["kind"] == "Reading":
            readBy = [a for a in x["annotations"] if a["kind"] == "Read by"]
            if not readBy:
                sessionTeachers = session["teachers"]
                newAnnotation = {"kind": "Read by", "flags": "","text": "","teachers": sessionTeachers,"indentLevel": 1}
                x["annotations"].insert(0,newAnnotation)
        for n,a in reversed(list(enumerate(x["annotations"]))): # Go backwards to allow multiple insertions
            if a["kind"] == "Reading":
                readBy = [subA for subA in Utils.SubAnnotations(x,a) if subA["kind"] == "Read by"]
                if not readBy:
                    if x["kind"] == "Reading":
                        readers = session["teachers"]
                    else:
                        readers = x["teachers"]
                    newAnnotation = {"kind": "Read by", "flags": "","text": "","teachers": readers,"indentLevel": a["indentLevel"] + 1}
                    x["annotations"].insert(n + 1,newAnnotation)

@lru_cache(maxsize = None)
def CompileTemplate(template: str) -> Type[pyratemp.Template]:
    return pyratemp.Template(template)

def AppendAnnotationToExcerpt(a: dict, x: dict) -> None:
    "Append annotation a to the end of excerpt x."

    if a["indentLevel"] == 1: # Append the annotation to the end of the excerpt.
        if "{attribution}" in a["body"]:
            attrNum = 2
            attrKey = "attribution" + str(attrNum)
            while attrKey in x: # Find the first available key of this form
                attrNum += 1
                attrKey = "attribution" + str(attrNum)
            
            a["body"] = a["body"].replace("{attribution}","{" + attrKey + "}")
            x[attrKey] = a["attribution"]
            x["teachers" + str(attrNum)] = a["teachers"]

        x["body"] += " " + a["body"]
    else: # Append the annotation to its enclosing excerpt
        body = a["body"].replace("{attribution}",a["attribution"])
        Utils.ParentAnnotation(x,a)["body"] += " " + body

    a["body"] = ""
    del a["attribution"]
        

def RenderItem(item: dict,container: dict|None = None) -> None:
    """Render an excerpt or annotation by adding "body" and "attribution" keys.
    If item is an attribution, container is the excerpt containing it."""
    
    kind = gDatabase["kind"][item["kind"]]

    formNumberStr = re.search("[0-9]+",item["flags"])
    if formNumberStr:
        formNumber = int(formNumberStr[0]) - 1
        if formNumber >= 0:
            if formNumber >= len(kind["body"]) or kind["body"][formNumber] == "unimplemented":
                formNumber = kind["defaultForm"] - 1
                Alert.warning(f"   {kind['kind']} does not implement form {formNumberStr[0]}. Reverting to default form number {formNumber + 1}.")
    else:
        formNumber = kind["defaultForm"] - 1

    if formNumber >= 0:
        bodyTemplateStr = kind["body"][formNumber]
        attributionTemplateStr = kind["attribution"][formNumber]
    else:
        bodyTemplateStr,attributionTemplateStr = ExtractAnnotation(item["text"])
    
    if ParseCSV.ExcerptFlag.UNQUOTE in item["flags"]: # This flag indicates no quotes
        bodyTemplateStr = re.sub('[“”]','',bodyTemplateStr) # Templates should use only double smart quotes

    bodyTemplate = CompileTemplate(bodyTemplateStr)
    attributionTemplate = CompileTemplate(attributionTemplateStr)

    plural = "s" if (ParseCSV.ExcerptFlag.PLURAL in item["flags"]) else "" # Is the excerpt heading plural?

    teachers = item.get("teachers",())
    if container:
        if item["kind"] == "Read by":
            grandparent = Utils.ParentAnnotation(container,Utils.ParentAnnotation(container,item))
                # The parent of this Read by annotation is a reading, which has the authors as teachers
                # Thus the grandparent indicates the default reader(s)
            if grandparent:
                defaultTeachers = grandparent["teachers"]
            else:
                defaultTeachers = Utils.FindSession(gDatabase["sessions"],container["event"],container["sessionNumber"])["teachers"]
        else:
            parent = Utils.ParentAnnotation(container,item)
            defaultTeachers = parent.get("teachers",())
        if set(defaultTeachers) == set(teachers) and ParseCSV.ExcerptFlag.ATTRIBUTE not in item["flags"] and not gOptions.attributeAll:
            teachers = () # Don't attribute an annotation which has the same teachers as it's excerpt
    teacherStr = Prototype.ListLinkedTeachers(teachers = teachers,lastJoinStr = ' and ')

    text = item["text"]
    prefix = ""
    suffix = ""
    parts = text.split("|")
    if len(parts) > 1:
        if len(parts) == 2:
            text, suffix = parts
        else:
            prefix, text, suffix = parts[0:3]
            if len(parts) > 3:
                Alert.warning("'|' occurs more than two times in '",item["text"],"'. Latter sections will be truncated.")

    colon = "" if not text or re.match(r"\s*[a-z]",text) else ":"
    renderDict = {"text": text, "s": plural, "colon": colon, "prefix": prefix, "suffix": suffix, "teachers": teacherStr}

    item["body"] = bodyTemplate(**renderDict)

    if teachers:

        # Does the text before the attribution end in a full stop?
        fullStop = "." if re.search(r"[.?!][^a-zA-Z]*\{attribution\}",item["body"]) else ""
        renderDict["fullStop"] = fullStop
        
        attributionStr = attributionTemplate(**renderDict)

        # If the template itself doesn't specify how to handle fullStop, capitalize the first letter of the attribution string
        if fullStop and "fullStop" not in attributionTemplateStr:
            attributionStr = re.sub("[a-zA-Z]",lambda match: match.group(0).upper(),attributionStr,count = 1)
    else:
        item["body"] = item["body"].replace("{attribution}","")
        attributionStr = ""
    
    if container and not kind["appendToExcerpt"]: # Is this an annotation listed below the excerpt?
        item["body"] = item["body"].replace("{attribution}",attributionStr)
    else:
        item["attribution"] = attributionStr
    
    # If the first tag of an indirect quote specifies a teacher, link the last occurence of the teacher in the body
    if item["kind"] == "Indirect quote" and item["tags"]:
        quotedTeacher = Utils.TeacherLookup(item["tags"][0])
        if quotedTeacher:
            parts = re.split(Utils.RegexMatchAny([gDatabase["teacher"][quotedTeacher]["fullName"]]),item["body"])
            if len(parts) > 1:
                parts[-2] = Prototype.LinkTeachersInText(parts[-2])
                item["body"] = "".join(parts)

def RenderExcerpts() -> None:
    """Use the templates in gDatabase["kind"] to add "body" and "attribution" keys to each except and its annotations"""

    kinds = gDatabase["kind"]
    for x in gDatabase["excerpts"]:
        RenderItem(x)
        for a in x["annotations"]:
            RenderItem(a,x)
            if kinds[a["kind"]]["appendToExcerpt"]:
                AppendAnnotationToExcerpt(a,x)


def LinkSuttas(ApplyToFunction:Callable = ApplyToBodyText):
    """Add links to sutta.readingfaithfully.org to the excerpts
    ApplyToFunction allows us to apply these same operations to other collections of text (e.g. documentation)"""

    def RawRefToReadingFaithfully(matchObject: re.Match) -> str:
        firstPart = matchObject[0].split("-")[0]

        if firstPart.startswith("Kd"): # For Kd, link to SuttaCentral directly
            chapter = matchObject[2]

            if matchObject[3]:
                if matchObject[4]:
                    subheading = f"#{matchObject[3]}.{matchObject[4]}.1"
                else:
                    subheading = f"#{matchObject[3]}.1.1"
            else:
                subheading = ""
            link = f"https://suttacentral.net/pli-tv-kd{chapter}/en/brahmali?layout=plain&reference=main&notes=asterisk&highlight=false&script=latin{subheading}"
        else: # All other links go to readingfaithfully.org
            dashed = re.sub(r'\s','-',firstPart)
            link = f"https://sutta.readingfaithfully.org/?q={dashed}"

        return link

    def RefToReadingFaithfully(matchObject: re.Match) -> str:
        return f'[{matchObject[0]}]({RawRefToReadingFaithfully(matchObject)})'

    def SuttasWithinMarkdownLink(bodyStr: str) -> Tuple[str,int]:
        return re.subn(markdownLinkToSutta,RawRefToReadingFaithfully,bodyStr,flags = re.IGNORECASE)
    
    def LinkItem(bodyStr: str) -> Tuple[str,int]:
        return re.subn(suttaMatch,RefToReadingFaithfully,bodyStr,flags = re.IGNORECASE)
    
    with open(Utils.PosixJoin(gOptions.prototypeDir,'assets/citationHelper/Suttas.json'), 'r', encoding='utf-8') as file: 
        suttas = json.load(file)
    suttaAbbreviations = [s[0] for s in suttas]

    suttaMatch = r"\b" + Utils.RegexMatchAny(suttaAbbreviations)+ r"\s+([0-9]+)[.:]?([0-9]+)?[.:]?([0-9]+)?[-]?[0-9]*"
    
    markdownLinkToSutta = r"(?<=\]\()" + suttaMatch + r"(?=\))"
    markdownLinksMatched = ApplyToFunction(SuttasWithinMarkdownLink)
        # Use lookbehind and lookahead assertions to first match suttas links within markdown format, e.g. [Sati](MN 10)

    suttasMatched = ApplyToFunction(LinkItem)
        # Then match all remaining sutta links

    Alert.extra(f"{suttasMatched + markdownLinksMatched} links generated to suttas, {markdownLinksMatched} within markdown links")

def ReferenceMatchRegExs(referenceDB: dict[dict]) -> tuple[str]:
    escapedTitles = [re.escape(abbrev) for abbrev in referenceDB]
    titleRegex = Utils.RegexMatchAny(escapedTitles)
    pageReference = r'(?:pages?|pp?\.)\s+[0-9]+(?:\-[0-9]+)?' 

    refForm2 = r'\[' + titleRegex + r'\]\((' + pageReference + ')?\)'
    refForm3 = r'\]\(' + titleRegex + r'(\s+' + pageReference + ')?\)'

    refForm4 = titleRegex + r'\s+(' + pageReference + ')'

    return refForm2, refForm3, refForm4

def LinkKnownReferences(ApplyToFunction:Callable = ApplyToBodyText) -> None:
    """Search for references of the form [abbreviation]() OR abbreviation page|p. N, add author and link information.
    If the excerpt is a reading, make the author the teacher.
    ApplyToFunction allows us to apply these same operations to other collections of text (e.g. documentation)"""

    def ParsePageNumber(text: str) -> int|None:
        "Extract the page number from a text string"
        if not text:
            return None
        pageNumber = re.search(r"[0-9]+",text)
        if pageNumber:
            return int(pageNumber[0])
        else:
            return None

    def PdfPageOffset(reference: dict,giveWarning = True) -> int:
        if not reference["filename"].lower().endswith(".pdf"):
            Alert.warning(reference,"links to",reference["filename"],"not a pdf file.")
        pageOffset = reference['pdfPageOffset']
        if pageOffset is None:
            pageOffset = 0
            if giveWarning:
                Alert.warning(reference,"does not specify pdfPageOffset.")
        return pageOffset

    def ReferenceForm2Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = Link.URL(reference,directoryDepth=2)
        if url:
            page = ParsePageNumber(matchObject[2])
            if page:
                url +=  f"#page={page + PdfPageOffset(reference,giveWarning=False)}"

            returnValue = f"[{reference['title']}]({url})"
        else:
            returnValue = f"{reference['title']}"

        if reference['attribution']:
            returnValue += " " + Prototype.LinkTeachersInText(reference['attribution'])
        
        if not url and reference["remoteUrl"]:
            returnValue += " " + reference["remoteUrl"]
                # If there's no link, "remoteUrl" key indicates a suffix, typically "(commercial)"

        return returnValue

    def ReferenceForm2(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: [title]() or [title](page N)"""
        return re.subn(refForm2,ReferenceForm2Substitution,bodyStr,flags = re.IGNORECASE)
    
    def ReferenceForm3Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = Link.URL(reference,directoryDepth=2)
        
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + PdfPageOffset(reference,giveWarning=False)}"""

        return f"]({url})"

    def ReferenceForm3(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: [xxxxx](title) or [xxxxx](title page N)"""
        return re.subn(refForm3,ReferenceForm3Substitution,bodyStr,flags = re.IGNORECASE)

    def ReferenceForm4Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = Link.URL(reference,directoryDepth=2)
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + PdfPageOffset(reference)}"

        items = [reference['title'],f", [{matchObject[2]}]({url})"]
        if reference["attribution"]:
            items.insert(1," " + Prototype.LinkTeachersInText(reference['attribution']))
        return "".join(items)

    def ReferenceForm4(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: title page N"""
        return re.subn(refForm4,ReferenceForm4Substitution,bodyStr,flags = re.IGNORECASE)
        
    refForm2, refForm3, refForm4 = ReferenceMatchRegExs(gDatabase["reference"])

    referenceCount = ApplyToFunction(ReferenceForm2)
    referenceCount += ApplyToFunction(ReferenceForm3)
    referenceCount += ApplyToFunction(ReferenceForm4)
    
    Alert.extra(f"{referenceCount} links generated to references")

def LinkSubpages(ApplyToFunction:Callable = ApplyToBodyText,pathToPrototype:str = "../",pathToHome:str = "../../") -> None:
    """Link references to subpages of the form [subpage](pageType:pageName) as described in LinkReferences().
    pathToPrototype is the path from the directory where the files are written to the prototype directory.
    pathToBaseForNonPages is the path to root directory from this file for links that don't go to html pages.
    It is necessary to distinguish between the two since frame.js modifies paths to local html files"""

    tagTypes = {"tag","drilldown"}
    excerptTypes = {"event","excerpt","session"}
    pageTypes = Utils.RegexMatchAny(tagTypes.union(excerptTypes,{"teacher","about","image","photo","player"}))
    linkRegex = r"\[([^][]*)\]\(" + pageTypes + r":([^()#]*)#?([^()#]*)\)"

    def SubpageSubstitution(matchObject: re.Match) -> str:
        text,pageType,link,hashTag = matchObject.groups()
        pageType = pageType.lower()

        linkTo = ""
        linkToPage = True
        wrapper = Html.Wrapper()
        if pageType in tagTypes:
            if link:
                tag = link
            else:
                tag = text
    
            realTag = Utils.TagLookup(tag)            
            if pageType == "tag":
                if realTag:
                    linkTo = f"tags/{gDatabase['tag'][realTag]['htmlFile']}"
                else:
                    Alert.warning("Cannot link to tag",tag,"in link",matchObject[0])
                if not link:
                    wrapper = Html.Wrapper("[","]")
            else:
                if tag.lower() == "root":
                    linkTo = f"drilldown/{Prototype.DrilldownPageFile(-1)}"
                elif realTag:
                    linkTo = f"drilldown/{Prototype.DrilldownPageFile(realTag,jumpToEntry=True)}"
                else:
                    Alert.warning("Cannot link to tag",tag,"in link",matchObject[0])
        elif pageType in excerptTypes:
            event,session,fileNumber = Utils.ParseItemCode(link)
            if event in gDatabase["event"]:
                if session or fileNumber:
                    bookmark = "#" + Utils.ItemCode(event=event,session=session,fileNumber=fileNumber)
                else:
                    bookmark = ""
                linkTo = f"events/{event}.html{bookmark}"
            else:
                Alert.warning("Cannot link to event",event,"in link",matchObject[0])
        elif pageType == "player":
            event,session,fileNumber = Utils.ParseItemCode(link)
            if fileNumber is not None:
                x = Utils.FindExcerpt(event,session,fileNumber)
                if x:
                    linkTo = Prototype.Mp3ExcerptLink(x)
                else:
                    Alert.warning("Cannot find excerpt corresponding to code",link,"in link",matchObject[0])
                    return text

            if not linkTo:
                linkTo = Prototype.AudioIcon(link,title=text)
            return f"<!--HTML{linkTo}-->"
        elif pageType == "teacher":
            if link:
                teacher = link
            else:
                teacher = text
            
            teacherCode = Utils.TeacherLookup(teacher)
            if teacherCode:
                htmlPage = gDatabase['teacher'][teacherCode]['htmlFile']
                if htmlPage:
                    linkTo = f"teachers/{htmlPage}"
                else:
                    Alert.caution("Teacher",teacherCode,"in link",matchObject[0],"is not searchable and has no html file.")
            else:
                Alert.warning("Cannot link to teacher",teacher,"in link",matchObject[0])
        elif pageType == "about":
            aboutPage = Utils.AboutPageLookup(link)
            if aboutPage:
                linkTo = f"{aboutPage}"
            else:
                Alert.warning("Cannot link about page",link,"in link",matchObject[0])
        elif pageType == "image":
            linkToPage = True
            linkTo = f"images/{link}"
        elif pageType == "photo":
            linkToPage = False
            imagePath = Utils.PosixJoin(pathToPrototype,"images/photos",link)
            if not hashTag:
                hashTag = "cover"
            text = f'<!--HTML <img src="{imagePath}" alt="{text}" id="{hashTag}" title="{text}" align="bottom" width="200" border="0"/> -->'

        if linkTo:
            path = Utils.PosixJoin(pathToPrototype if linkToPage else pathToHome,linkTo)
            return wrapper(f"[{text}]({path}{'#' + hashTag if hashTag else ''})")
        else:
            return text
        
    def ReplaceSubpageLinks(bodyStr) -> tuple[str,int]:
        return re.subn(linkRegex,SubpageSubstitution,bodyStr,flags = re.IGNORECASE)
    
    linkCount = ApplyToFunction(ReplaceSubpageLinks)
    Alert.extra(f"{linkCount} links generated to subpages")

def MarkdownFormat(text: str) -> Tuple[str,int]:
    """Format a single-line string using markdown, and eliminate the <p> tags.
    The second item of the tuple is 1 if the item has changed and zero otherwise"""

    md = re.sub("(^<P>|</P>$)", "", markdown.markdown(text,extensions = [NewTabRemoteExtension()]), flags=re.IGNORECASE)
    if md != text:
        return md, 1
    else:
        return text,0


def LinkReferences() -> None:
    """Add hyperlinks to references contained in the excerpts and annotations.
    Allowable formats are:
    1. [reference](link) - Markdown format for arbitrary hyperlinks
    2. [title]() or [title](page N) - Titles in Reference sheet; if page N or p. N appears between the parenthesis, link to this page in the pdf, but don't display in the html
    3. [xxxxx](title) or [xxxxx](title page N) - Apply hyperlink from title to arbitrary text xxxxx
    4. title page N - Link to specific page for titles in Reference sheet which shows the page number
    5. SS N.N - Link to Sutta/vinaya SS section N.N at sutta.readingfaithfully.org
    6. [reference](SS N.N) - Markdown hyperlink pointing to sutta..
    7. [subpage](pageType:pageName) - Link to a subpage within the QS Archive. Options for pageType are:
        tag - Link to the named tag page - Link to tag subpage and enclose the entire reference in brackets if pageName is ommited
        drilldown - Link to the primary tag given by pageName
        event,session,excerpt - Link to an event page, optionally to a specific session or excerpt. 
            pageName is of the form Event20XX_SYY_FZZ produced by Utils.ItemCode()
        player - Insert an audio player; pageName is either an item code as above or a hyperlink to an audio file.
            In the latter case, subpage specifies the title of the audio.
        teacher - Link to a teacher page; pageName is the teacher code, e.g. AP
        about - Link to about page pageName
        image - Link to images in prototypeDir/images
        photo - Link to photos in prototypeDir/images/photos"""

    LinkSubpages()
    LinkKnownReferences()
    LinkSuttas()

    markdownChanges = ApplyToBodyText(MarkdownFormat)
    Alert.extra(f"{markdownChanges} items changed by markdown")
    

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--renderedDatabase',type=str,default='prototype/RenderedDatabase.json',help='Database after rendering each excerpt; Default: prototype/RenderedDatabase.json')

def ParseArguments() -> None:
    pass

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:

    PrepareTemplates()

    AddImplicitAttributions()

    RenderExcerpts()

    LinkReferences()

    for key in ["tagRedacted","excerptsRedacted","tagRemoved","summary","keyCaseTranslation"]:
        del gDatabase[key]

    #Alert.extra("Rendered database contents:",indent = 0)
    #Utils.SummarizeDict(gDatabase,Alert.extra)

    with open(gOptions.renderedDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase, file, ensure_ascii=False, indent=2)
