"""Render raw documentation files in documentation/aboutSources to markdown files in documentation/about using pryatemp."""

from __future__ import annotations

import json, re, os
import Utils, Render
from typing import Tuple, Type, Callable
import pyratemp

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--documentationDir',type=str,default='documentation',help='Read and write documentation files here; Default: ./documenation')
    

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main() -> None:
    scanDirectories = [Utils.PosixJoin(gOptions.documentationDir,dir) for dir in ['about']]

    for destDir in scanDirectories:
        sourceDir = destDir + "Sources"
        for fileName in sorted(os.listdir(sourceDir)):
            sourcePath = Utils.PosixJoin(sourceDir,fileName)
            destPath = Utils.PosixJoin(destDir,fileName)

            if not os.path.isfile(sourcePath) or not fileName.endswith(".md"):
                continue

            with open(sourcePath,encoding='utf8') as file:
                fileText = file.read()
            
            def ApplyToText(transform: Callable[[str],Tuple[str,int]]) -> int:
                nonlocal fileText
                fileText,changeCount = transform(fileText)
                return changeCount
            
            Render.LinkSuttas(ApplyToText)
            Render.LinkKnownReferences(ApplyToText)
            Render.LinkSubpages(ApplyToText)

            with open(destPath,'w',encoding='utf-8') as file:
                print(fileText,file=file)
                



