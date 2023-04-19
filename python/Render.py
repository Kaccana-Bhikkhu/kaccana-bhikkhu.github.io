"""Render the text of each excerpt in the database with its annotations to html using the pryatemp templates in database["Kind"].
The only remaining work for Prototype.py to do is substitute the list of teachers for {attribtuion}, {attribtuion2}, and {attribtuion3} when needed."""

import json, re
import markdown
from markdown_newtab import NewTabExtension
from typing import Tuple, Type, Callable
from collections import defaultdict
import pyratemp
from functools import cache
import itertools
import ParseCSV, Prototype, Utils

def PrepareReferences() -> None:
    """Prepare gDatabase["reference"] for use."""
    reference = gDatabase["reference"]

    ParseCSV.ListifyKey(reference,"author1")
    ParseCSV.ConvertToInteger(reference,"pdfPageOffset")
    
    # Convert ref["abbreviation"] to lowercase for dictionary matching
    # ref["title"] still has the correct case
    for ref in list(reference.keys()): 
        reference[ref.lower()] = reference.pop(ref)

def FStringToPyratemp(fString: str) -> str:
    """Convert a template in our psuedo-f string notation to a pyratemp template"""
    prya = fString.replace("{","@!").replace("}","!@")
    
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

    return changeCount
    

def ExtractAnnotation(form: str) -> Tuple[str,str]:
    """Split the form into body and attribution parts, which are separated by ||.
    Example: Story|| told by @!teachers!@||: @!text!@ ->
    body = Story||{attribution}||:: @!text!@
    attribution = told by @!teachers!@"""

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
            parts = form.split("++")
            if len(parts) > 1:
                parts.insert(2,"</b>")
                parts.insert(1,"<b>")
                form = ''.join(parts)
            
            body, attribution = ExtractAnnotation(form)
            kind["body"].append(body)
            kind["attribution"].append(attribution)

def AddImplicitAttributions() -> None:
    "If an excerpt of kind Reading doesn't have a Read by annotation, attribute it to the session teachers"
    for x in gDatabase["excerpts"]:
        if x["kind"] == "Reading":
            readBy = [a for a in x["annotations"] if a["kind"] == "Read by"]
            if not readBy:
                print("We're going to add something soon.")

@cache
def CompileTemplate(template: str) -> Type[pyratemp.Template]:
    return pyratemp.Template(template)

def AppendAnnotationToExcerpt(a: dict, x: dict) -> None:
    "Append annotation a to the end of excerpt x."
    #print(f"{a=},{x=}")

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

def RenderItem(item: dict) -> None:
    """Render an excerpt or annotation by adding "body" and "attribution" keys."""
    
    kind = gDatabase["kind"][item["kind"]]

    formNumber = kind["defaultForm"] - 1

    if formNumber >= 0:
        bodyTemplateStr = kind["body"][formNumber]
    else:
        bodyTemplateStr = item["text"]
    bodyTemplate = CompileTemplate(bodyTemplateStr)
    attributionTemplateStr = kind["attribution"][formNumber]
    attributionTemplate = CompileTemplate(attributionTemplateStr)

    plural = "s" if ("s" in item["flags"]) else "" # Is the excerpt heading plural?

    teacherList = [gDatabase["teacher"][t]["fullName"] for t in item.get("teachers",())]
    teacherStr = Prototype.ItemList(items = teacherList,lastJoinStr = ' and ')

    text = item["text"]
    prefix = ""
    suffix = ""
    parts = text.split("|")
    if len(parts) > 1:
        if len(parts) == 2:
            text, suffix = parts
        else:
            prefix, text, suffix = parts[0:3]
            if len(parts) > 3 and gOptions.verbose >= -1:
                print("   Warning: '|' occurs more than two times in '",item["text"],"'. Latter sections will be truncated.")

    colon = "" if re.match(r"\s*[a-z]",text) else ":"
    renderDict = {"text": text, "s": plural, "colon": colon, "prefix": prefix, "suffix": suffix, "teachers": teacherStr}

    item["body"] = bodyTemplate(**renderDict)

    if teacherList:

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
    
    if "indentLevel" in item and not kind["appendToExcerpt"]: # Is this an annotation listed below the excerpt?
        item["body"] = item["body"].replace("{attribution}",attributionStr)
    else:
        item["attribution"] = attributionStr

def RenderExcerpts() -> None:
    """Use the templates in gDatabase["kind"] to add "body" and "attribution" keys to each except and its annotations"""

    kinds = gDatabase["kind"]
    for x in gDatabase["excerpts"]:
        RenderItem(x)
        for a in x["annotations"]:
            RenderItem(a)
            if kinds[a["kind"]]["appendToExcerpt"]:
                AppendAnnotationToExcerpt(a,x)


def LinkSuttas():
    """Add links to sutta.readingfaithfully.org"""

    def RefToReadingFaithfully(matchObject: re.Match) -> str:
        firstPart = matchObject[0].split("-")[0]
        dashed = re.sub(r'\s','-',firstPart)
        #print(matchObject,dashed)
        return f'[{matchObject[0]}](https://sutta.readingfaithfully.org/?q={dashed})'

    def LinkItem(bodyStr: str) -> Tuple[str,int]:
        return re.subn(suttaMatch,RefToReadingFaithfully,bodyStr,flags = re.IGNORECASE)
    
    with open('tools/citationHelper/Suttas.json', 'r', encoding='utf-8') as file: 
        suttas = json.load(file)
    suttaAbbreviations = [s[0] for s in suttas]

    suttaMatch = r"\b" + Utils.RegexMatchAny(suttaAbbreviations)+ r"\s*([0-9]+)[.:]?([0-9]+)?[-]?[0-9]*"

    suttasMatched = ApplyToBodyText(LinkItem)

    if gOptions.verbose > 1:
        print(f"   {suttasMatched} links generated to suttas")


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
        #print(matchObject[0],matchObject[1],matchObject[2])
        
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            if gOptions.verbosity > 0:
                print(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = reference['remoteUrl']
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + reference['pdfPageOffset']}"

        nonlocal foundReferences # use this to pass the abbreviation of the matched book back to ReferenceForm2
        foundReferences.append(reference)
        return f"[{reference['title']}]({url}) {reference['attribution']}"

    def ReferenceForm2(bodyStr,item: dict) -> Tuple[str,int]:
        """Search for references of the form: [title]() or [title](page N)"""
        nonlocal foundReferences
        foundReferences = []
        returnStr = re.sub(refForm2,ReferenceForm2Substitution,bodyStr,flags = re.IGNORECASE)

        if foundReferences:
            if item["kind"] == "Reading": # If this is a reading, add the authors to the teacher list
                #print(foundReferences)
                for ref in foundReferences:
                    Utils.AppendUnique(item["teachers"],ref["author"])
            #print("Ref form 2:",item["body"],item.get("teachers",[]))
        
        return returnStr,len(foundReferences)
    
    def ReferenceForm3Substitution(matchObject: re.Match) -> str:
        #print(repr(matchObject[0]),repr(matchObject[1]),repr(matchObject[2]))
        
        try:
            reference = gDatabase["reference"][matchObject[1].lower()]
        except KeyError:
            if gOptions.verbosity > 0:
                print(f"Cannot find abbreviated title {matchObject[1]} in the list of references.")
            return matchObject[1]
        
        url = reference['remoteUrl']
        page = ParsePageNumber(matchObject[2])
        if page:
           url +=  f"#page={page + reference['pdfPageOffset']}"

        nonlocal foundReferences # use this to pass the abbreviation of the matched book back to ReferenceForm2
        foundReferences.append(reference)
        return f"{reference['title']} {reference['attribution']} [{matchObject[2]}]({url})"

    def ReferenceForm3(bodyStr,item: dict) -> Tuple[str,int]:
        """Search for references of the form: title page N"""
        nonlocal foundReferences
        foundReferences = []
        returnStr = re.sub(refForm3,ReferenceForm3Substitution,bodyStr,flags = re.IGNORECASE)

        if foundReferences:
            if item["kind"] == "Reading": # If this is a reading, add the authors to the teacher list
                #print(foundReferences)
                for ref in foundReferences:
                    Utils.AppendUnique(item["teachers"],ref["author"])
            #print("Ref form 3:",item["body"],item.get("teachers",[]))
        
        return returnStr,len(foundReferences)

    escapedTitles = [re.escape(abbrev) for abbrev in gDatabase["reference"]]
    pageReference = r'(?:pages?|pp?\.)\s+[0-9]+(?:\-[0-9]+)?' 

    refForm2 = r'\[' + Utils.RegexMatchAny(escapedTitles) + r'\]\((' + pageReference + ')?\)'
    #print(refForm2)
    refForm3 = Utils.RegexMatchAny(escapedTitles) + r'\s+(' + pageReference + ')'
    #print(refForm3)

    foundReferences = []

    referenceCount = ApplyToBodyText(ReferenceForm2,passItemAsSecondArgument=True)
    referenceCount = ApplyToBodyText(ReferenceForm3,passItemAsSecondArgument=True)
    
    if gOptions.verbose > 1:
        print(f"   {referenceCount} links generated to references")

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
    3. title page N - Link to specific page for titles in Reference sheet which shows the page number
    4. SS N.N - Link to Sutta/vinaya SS section N.N at sutta.readingfaithfully.org"""

    LinkSuttas()
    LinkKnownReferences()

    markdownChanges = ApplyToBodyText(MarkdownFormat)
    if gOptions.verbose > 1:
        print(f"   {markdownChanges} items changed by markdown")
    

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--renderedDatabase',type=str,default='prototype/RenderedDatabase.json',help='Database after rendering each excerpt; Default: prototype/RenderedDatabase.json')

gOptions = None
gDatabase = None
def main(clOptions,database) -> None:
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    gDatabase = database

    PrepareReferences()
    PrepareTemplates()

    AddImplicitAttributions()

    RenderExcerpts()

    LinkReferences()

    with open(gOptions.renderedDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase, file, ensure_ascii=False, indent=2)
