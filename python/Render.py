"""Render the text of each excerpt in the database with its annotations to html using the pryatemp templates in database["Kind"].
The only remaining work for Prototype.py to do is substitute the list of teachers for {attribtuion}, {attribtuion2}, and {attribtuion3} when needed."""

import json
import ParseCSV
from typing import Tuple

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
        return form,  ""

    attribution = parts[1]
    parts[1] = "{attribution}"
    return "".join(parts), attribution

def PrepareTemplates():
    ParseCSV.ListifyKey(gDatabase["kind"],"form1")

    for kind in gDatabase["kind"].values():
        kind["forms"] = [FStringToPyratemp(f) for f in kind["form"]]
        del kind["form"]

        kind["body"] = []; kind["attribution"] = []
        for form in kind["forms"]:
            body, attribution = ExtractAnnotation(form)
            kind["body"].append(body)
            kind["attribution"].append(attribution)

def RenderExcerpts():
    """Add a 'rendered' key to each excerpt by applying the specified template to its contents.
    Prototype.py then uses this key to generate the html file."""
    pass

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--renderedDatabase',type=str,default='prototype/RenderedDatabase.json',help='Database after rendering each excerpt; Default: prototype/RenderedDatabase.json')

gOptions = None
gDatabase = None
def main(clOptions,database):
    global gOptions
    gOptions = clOptions
    
    global gDatabase
    gDatabase = database

    PrepareTemplates()

    RenderExcerpts()

    with open(gOptions.renderedDatabase, 'w', encoding='utf-8') as file:
        json.dump(gDatabase["kind"], file, ensure_ascii=False, indent=2)
