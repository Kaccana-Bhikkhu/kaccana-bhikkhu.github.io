"""Render the text of each excerpt in the database with its annotations to html using the pryatemp templates in database["Kind"].
The only remaining work for Prototype.py to do is substitute the list of teachers for {attribtuion}, {attribtuion2}, and {attribtuion3} when needed."""

import json, re
import ParseCSV, Prototype, Utils
from typing import Tuple, Type
from collections import defaultdict
import pyratemp
from functools import cache

def PrepareReferences() -> None:
    """Prepare gDatabase["reference"] for use."""
    reference = gDatabase["reference"]

    ParseCSV.ListifyKey(reference,"author1")
    ParseCSV.ConvertToInteger(reference,"pdfPageOffset")

def FStringToPyratemp(fString: str) -> str:
    """Convert a template in our psuedo-f string notation to a pyratemp template"""
    prya = fString.replace("{","@!").replace("}","!@")
    
    return prya

def ExtractAnnotation(form: str) -> Tuple[str,str]:
    """Split the form into body and attribution parts, which are separated by ||.
    Example: Story|| told by @!teacher!@||: @!text!@ ->
    body = Story||{attribution}||:: @!text!@
    attribution = told by @!teacher!@"""

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

@cache
def CompileTemplate(template: str) -> Type[pyratemp.Template]:
    return pyratemp.Template(template)

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
    renderDict = {"text": text, "s": plural, "colon": colon, "prefix": prefix, "suffix": suffix, "teacher": teacherStr}

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
    
    if "indentLevel" in item: # Is this an annotation?
        item["body"] = item["body"].replace("{attribution}",attributionStr)
    else:
        item["attribution"] = attributionStr

def RenderExcerpts() -> None:
    """Use the templates in gDatabase["kind"] to add "body" and "attribution" keys to each except and its annotations"""

    for x in gDatabase["excerpts"]:
        RenderItem(x)
        for a in x["annotations"]:
            RenderItem(a)

def LinkSuttas():
    """Add links to sutta.readingfaithfully.org"""

    def RefToReadingFaithfully(matchObject: re.Match):
        firstPart = matchObject[0].split("-")[0]
        dashed = re.sub(r'\s','-',firstPart)
        #print(matchObject,dashed)
        return f'<a href = "https://sutta.readingfaithfully.org/?q={dashed}">{matchObject[0]}</a>'

    def LinkItem(item: dict):
        item["body"],count = re.subn(suttaMatch,RefToReadingFaithfully,item["body"],flags = re.IGNORECASE)

        #if count:
        #    print(item["body"])

        nonlocal suttasMatched
        suttasMatched += count
    
    suttasMatched = 0
    with open('tools/citationHelper/Suttas.json', 'r', encoding='utf-8') as file: 
        suttas = json.load(file)
    suttaAbbreviations = [s[0] for s in suttas]

    suttaMatch = r"\b" + Utils.RegexMatchAny(suttaAbbreviations)+ r"\s*([0-9]+)[.:]?([0-9]+)?[-]?[0-9]*"
    #print(suttaMatch)

    for x in gDatabase["excerpts"]:
        LinkItem(x)
        for a in x["annotations"]:
            LinkItem(a)

    if gOptions.verbose > 1:
        print(f"{suttasMatched} links generated to suttas")

def LinkReferences() -> None:
    """Add hyperlinks to references contained in the excerpts and annotations.
    Allowable formats are:
    1. [reference](link) - Markdown format for arbitrary hyperlinks
    2. [title]() - Titles in Reference sheet: 
    3. title page N - Link to specific pages for titles in Reference sheet 
    4. SS N.N - Link to Sutta/vinaya SS section N.N at sutta.readingfaithfully.org"""

    LinkSuttas()

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

    RenderExcerpts()

    LinkReferences()

    with open(gOptions.renderedDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase, file, ensure_ascii=False, indent=2)
