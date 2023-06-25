"""Render the text of each excerpt in the database with its annotations to html using the pryatemp templates in database["Kind"].
The only remaining work for Prototype.py to do is substitute the list of teachers for {attribtuion}, {attribtuion2}, and {attribtuion3} when needed."""

from __future__ import annotations

import json, re
import markdown
from markdown_newtab import NewTabExtension
from typing import Tuple, Type, Callable, List, Dict
import pyratemp
from functools import lru_cache
import ParseCSV, Prototype, Utils, Alert

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
    "If an excerpt of kind Reading doesn't have a Read by annotation, attribute it to the session teachers"
    for x in gDatabase["excerpts"]:
        if x["kind"] == "Reading":
            readBy = [a for a in x["annotations"] if a["kind"] == "Read by"]
            if not readBy:
                sessionTeachers = Utils.FindSession(gDatabase["sessions"],x["event"],x["sessionNumber"])["teachers"]
                newAnnotation = {"kind": "Read by", "flags": "","text": "","teachers": sessionTeachers,"indentLevel": 1}
                x["annotations"].insert(0,newAnnotation)
                

@lru_cache(maxsize = None)
def CompileTemplate(template: str) -> Type[pyratemp.Template]:
    return pyratemp.Template(template)

def AppendAnnotationToExcerpt(a: dict, x: dict) -> None:
    "Append annotation a to the end of excerpt x."

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
                Alert.warning.Show(f"   {kind['kind']} does not implement form {formNumberStr[0]}. Reverting to default form number {formNumber + 1}.")
    else:
        formNumber = kind["defaultForm"] - 1

    if formNumber >= 0:
        bodyTemplateStr = kind["body"][formNumber]
        attributionTemplateStr = kind["attribution"][formNumber]
    else:
        bodyTemplateStr,attributionTemplateStr = ExtractAnnotation(item["text"])
    
    if "u" in item["flags"]: # This flag indicates no quotes
        bodyTemplateStr = re.sub('[“”]','',bodyTemplateStr) # Templates should use only double smart quotes

    bodyTemplate = CompileTemplate(bodyTemplateStr)
    attributionTemplate = CompileTemplate(attributionTemplateStr)

    plural = "s" if ("s" in item["flags"]) else "" # Is the excerpt heading plural?

    teachers = item.get("teachers",())
    if container and set(container["teachers"]) == set(teachers) and "a" not in item["flags"] and not gOptions.attributeAll:
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
                Alert.warning.Show("'|' occurs more than two times in '",item["text"],"'. Latter sections will be truncated.")

    colon = "" if not text or re.match(r"\s*[a-z]",text) else ":"
    renderDict = {"text": text, "s": plural, "colon": colon, "prefix": prefix, "suffix": suffix, "teachers": teacherStr}

    item["body"] = bodyTemplate(**renderDict)

    if teachers:

        # Does the text before the attribution end in a full stop?
        fullStop = "." if re.search(r"[.?!][^a-zA-Z]*\{attribution\}",item["body"]) else ""
        renderDict["fullStop"] = fullStop
        
        attributionStr = attributionTemplate(**renderDict)

        # If the template itself doesn't specify how to handle fullStop, capitalize the first letter of the attribution string
        if fullStop and "{fullStop}" not in attributionTemplateStr:
            attributionStr = re.sub("[a-zA-Z]",lambda match: match.group(0).upper(),attributionStr,count = 1)
    else:
        item["body"] = item["body"].replace("{attribution}","")
        attributionStr = ""
    
    if container and not kind["appendToExcerpt"]: # Is this an annotation listed below the excerpt?
        item["body"] = item["body"].replace("{attribution}",attributionStr)
    else:
        item["attribution"] = attributionStr

def RenderExcerpts() -> None:
    """Use the templates in gDatabase["kind"] to add "body" and "attribution" keys to each except and its annotations"""

    kinds = gDatabase["kind"]
    for x in gDatabase["excerpts"]:
        RenderItem(x)
        for a in x["annotations"]:
            RenderItem(a,x)
            if kinds[a["kind"]]["appendToExcerpt"]:
                AppendAnnotationToExcerpt(a,x)


def LinkSuttas():
    """Add links to sutta.readingfaithfully.org"""

    def RefToReadingFaithfully(matchObject: re.Match) -> str:
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

        return f'[{matchObject[0]}]({link})'

    def LinkItem(bodyStr: str) -> Tuple[str,int]:
        return re.subn(suttaMatch,RefToReadingFaithfully,bodyStr,flags = re.IGNORECASE)
    
    with open('tools/citationHelper/Suttas.json', 'r', encoding='utf-8') as file: 
        suttas = json.load(file)
    suttaAbbreviations = [s[0] for s in suttas]

    suttaMatch = r"\b" + Utils.RegexMatchAny(suttaAbbreviations)+ r"\s*([0-9]+)[.:]?([0-9]+)?[.:]?([0-9]+)?[-]?[0-9]*"

    suttasMatched = ApplyToBodyText(LinkItem)

    Alert.extra.Show(f"{suttasMatched} links generated to suttas")

def ReferenceMatchRegExs(referenceDB: dict[dict]) -> tuple[str]:
    escapedTitles = [re.escape(abbrev) for abbrev in referenceDB]
    titleRegex = Utils.RegexMatchAny(escapedTitles)
    pageReference = r'(?:pages?|pp?\.)\s+[0-9]+(?:\-[0-9]+)?' 

    refForm2 = r'\[' + titleRegex + r'\]\((' + pageReference + ')?\)'
    refForm3 = r'\]\(' + titleRegex + r'(\s+' + pageReference + ')?\)'

    refForm4 = titleRegex + r'\s+(' + pageReference + ')'

    return refForm2, refForm3, refForm4

def LinkKnownReferences() -> None:
    """Search for references of the form [abbreviation]() OR abbreviation page|p. N, add author and link information.
    If the excerpt is a reading, make the author the teacher."""

    def ParsePageNumber(text: str) -> int|None:
        "Extract the page number from a text string"
        if not text:
            return None
        pageNumber = re.search(r"[0-9]+",text)
        if pageNumber:
            return int(pageNumber[0])
        else:
            return None

    def ReferenceForm2Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning.Show(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = reference['remoteUrl']
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + reference['pdfPageOffset']}"

        return f"[{reference['title']}]({url}) {Prototype.LinkTeachersInText(reference['attribution'])}"

    def ReferenceForm2(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: [title]() or [title](page N)"""
        return re.subn(refForm2,ReferenceForm2Substitution,bodyStr,flags = re.IGNORECASE)
    
    def ReferenceForm3Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning.Show(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = reference['remoteUrl']
        
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + reference['pdfPageOffset']}"""

        return f"]({url})"

    def ReferenceForm3(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: [xxxxx](title) or [xxxxx](title page N)"""
        return re.subn(refForm3,ReferenceForm3Substitution,bodyStr,flags = re.IGNORECASE)

    def ReferenceForm4Substitution(matchObject: re.Match) -> str:
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            Alert.warning.Show(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = reference['remoteUrl']
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + reference['pdfPageOffset']}"

        return f"{reference['title']} {Prototype.LinkTeachersInText(reference['attribution'])} [{matchObject[2]}]({url})"

    def ReferenceForm4(bodyStr: str) -> tuple[str,int]:
        """Search for references of the form: title page N"""
        return re.subn(refForm4,ReferenceForm4Substitution,bodyStr,flags = re.IGNORECASE)
        
    refForm2, refForm3, refForm4 = ReferenceMatchRegExs(gDatabase["reference"])

    referenceCount = ApplyToBodyText(ReferenceForm2)
    referenceCount += ApplyToBodyText(ReferenceForm3)
    referenceCount += ApplyToBodyText(ReferenceForm4)
    
    Alert.extra.Show(f"{referenceCount} links generated to references")

def MarkdownFormat(text: str) -> Tuple[str,int]:
    """Format a single-line string using markdown, and eliminate the <p> tags.
    The second item of the tuple is 1 if the item has changed and zero otherwise"""

    md = re.sub("(^<P>|</P>$)", "", markdown.markdown(text,extensions = [NewTabExtension()]), flags=re.IGNORECASE)
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
    5. SS N.N - Link to Sutta/vinaya SS section N.N at sutta.readingfaithfully.org"""

    LinkSuttas()
    LinkKnownReferences()

    markdownChanges = ApplyToBodyText(MarkdownFormat)
    Alert.extra.Show(f"{markdownChanges} items changed by markdown")
    

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--renderedDatabase',type=str,default='prototype/RenderedDatabase.json',help='Database after rendering each excerpt; Default: prototype/RenderedDatabase.json')

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main() -> None:

    PrepareTemplates()

    AddImplicitAttributions()

    RenderExcerpts()

    LinkReferences()

    with open(gOptions.renderedDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase, file, ensure_ascii=False, indent=2)
