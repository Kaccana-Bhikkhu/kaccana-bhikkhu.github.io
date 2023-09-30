"""Render raw documentation files in documentation/aboutSources to markdown files in documentation/about using pryatemp."""

from __future__ import annotations

import json, re, os
import Utils, Render, Alert, Html
from typing import Tuple, Type, Callable
import pyratemp, markdown
from markdown_newtab_remote import NewTabRemoteExtension

def RenderDocumentationFiles(aboutDir: str,destDir:str = "",pathToPrototype:str = "../",pathToBase = "../../",html:bool = True) -> list[Html.PageDesc]:
    """Read and render the documentation files. Return a list of PageDesc objects.
    aboutDir: the name of the directory to read from; files are read from aboutDir + "Sources".
    destDir: the destination directory; set to aboutDir if not given.
    pathToPrototype: path from the where the documentation will be written to the prototype directory.
    pathToBase: the path to the base directory
    html: Render the file into html? - Leave in .md format if false.
    """

    aboutDir = Utils.PosixJoin(gOptions.documentationDir,aboutDir)
    if not destDir:
        destDir = aboutDir
    sourceDir = aboutDir + "Sources"
    
    fileContents = {}
    for fileName in sorted(os.listdir(sourceDir)):
        sourcePath = Utils.PosixJoin(sourceDir,fileName)

        if not os.path.isfile(sourcePath) or not fileName.endswith(".md"):
            continue

        with open(sourcePath,encoding='utf8') as file:
            fileContents[fileName] = file.read()
            
    def ApplyToText(transform: Callable[[str],Tuple[str,int]]) -> int:
        changeCount = 0
        for fileName in fileContents.keys():
            fileContents[fileName],changes = transform(fileContents[fileName])
            changeCount += changes
        
        return changeCount
            
    Render.LinkSubpages(ApplyToText,pathToPrototype,pathToBase)
    Render.LinkKnownReferences(ApplyToText)
    Render.LinkSuttas(ApplyToText)

    if html:
        htmlFiles = {}
        for fileName in fileContents:
            html = markdown.markdown(fileContents[fileName],extensions = ["sane_lists","footnotes",NewTabRemoteExtension()])
        
            html = re.sub(r"<!--HTML(.*?)-->",r"\1",html) # Remove comments around HTML code
            htmlFiles[Utils.ReplaceExtension(fileName,".html")] = html
        fileContents = htmlFiles

    titleInPage = "The Ajahn Pasanno Question and Story Archive"
    renderedPages = []
    for fileName,fileText in fileContents.items():
        titleMatch = re.search(r"<!--TITLE:(.*?)-->",fileText)
        if titleMatch:
            title = titleMatch[1]
        else:
            m = re.match(r"[0-9]*_?([^.]*)",fileName)
            title = m[1].replace("-"," ")

        page = Html.PageDesc(Html.PageInfo(title,Utils.PosixJoin(destDir,fileName),titleInPage))
        page.AppendContent(fileText)
        renderedPages.append(page)

    return renderedPages


def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--documentationDir',type=str,default='documentation',help='Read and write documentation files here; Default: ./documenation')
    

def ParseArguments() -> None:
    pass

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy


def main() -> None:
    for directory in ['about','misc']:
        os.makedirs(Utils.PosixJoin(gOptions.documentationDir,directory),exist_ok=True)
        for page in RenderDocumentationFiles(directory,pathToPrototype=Utils.PosixJoin("../../",gOptions.prototypeDir),pathToBase="../../",html=False):
            with open(page.info.file,'w',encoding='utf-8') as file:
                print(str(page),file=file)
