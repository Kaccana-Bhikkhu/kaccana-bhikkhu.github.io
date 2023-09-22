"""Apply tags to mp3 excerpt files based on the information in RenderedDatabase.json.
We leave the session file tags untouched."""

from __future__ import annotations

import json, re, os
import Utils, Render, Alert, Html
from typing import Tuple, Type, Callable
import pyratemp, markdown

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, COMM

def register_comment(desc=''):
    """Register the comment tag using both UTF-16 and latin encodings.
    Tag choices based on Audacity mp3 encoder.
    Code based on https://www.extrema.is/blog/2021/08/04/comment-and-url-tags-with-mutagen."""
    frameid = ':'.join(('COMM', desc, '\x00\x00\x00'))
    frameidUTF16 = ':'.join(('COMM', desc, 'XXX'))

    def getter(id3, _key):
        frame = id3.get(frameidUTF16)
        if frame is not None:
            return list(frame)
        else:
            frame = id3.get(frame)
            if frame is not None:
                return list(frame)
            else:
                return None

    def setter(id3, _key, value):
        id3.add(mutagen.id3.COMM(
            encoding=0, lang='\x00\x00\x00', desc=desc, text=[Utils.RemoveDiacritics(t) for t in value]))
        id3.add(mutagen.id3.COMM(
            encoding=1, lang='XXX', desc=desc, text=value))

    def deleter(id3, _key):
        if frameid in id3:
            del id3[frameid]
        if frameidUTF16 in id3:
            del id3[frameidUTF16]

    def lister(id3, _key) -> list:
        if frameidUTF16 in id3 or frameid in id3:
            return ["comment"]
        else:
            return []

    EasyID3.RegisterKey('comment', getter, setter, deleter, lister)

def ReadID3(file: str) -> ID3:
    tags = ID3(file)
    return tags

def PrintID3(tags: ID3) -> None:
    print(tags)
    print('   ----')
    print(tags.pprint())
    print()

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    pass
    # parser.add_argument('--documentationDir',type=str,default='documentation',help='Read and write documentation files here; Default: ./documenation')
    

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy

def main() -> None:
    print("here")