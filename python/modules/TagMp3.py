"""Apply tags to mp3 excerpt files based on the information in RenderedDatabase.json.
We leave the session file tags untouched."""

from __future__ import annotations

import json, re, os
import Utils, Alert
from typing import Tuple, Type, Callable

import mutagen
import mutagen.id3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3

def register_comment(desc='') -> None:
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

removeFromBody = "|".join([r"\{attribution[^}]*}",r"<[^>]*>"])
def CleanupBody(body:str) -> str:
    "Remove extraneous bit from the body text in order to make a nice comment tag."

    return re.sub(removeFromBody,"",body)

def ExcerptTags(excerpt: dict) -> dict:
    """Given an excerpt, return a dictionary of the id3 tags it should have."""
    event = gDatabase["event"][excerpt["event"]]
    session = Utils.FindSession(gDatabase["sessions"],excerpt["event"],excerpt["sessionNumber"])

    sessionStr = f", Session {excerpt['sessionNumber']}" if excerpt['sessionNumber'] else ""
    returnValue = {
        "title": f"{event['title']}{sessionStr}, Excerpt {excerpt['excerptNumber']}",
        "artist": [gDatabase["teacher"][t]["fullName"] for t in event["teachers"]],
        "album": event["title"] + sessionStr,
        "tracknumber": str(excerpt["excerptNumber"]),
        "date": str(Utils.ParseDate(session["date"]).year),
        "comment": CleanupBody(excerpt["body"]),
        "genre": "Questions and answers",
        "copyright": "© 2023 Abhayagiri Monastery; not for distribution outside the APQS Archive",
        "organization": "The Ajahn Pasanno Question and Story Achive",
        "website": "https://abhayagiri.org/questions/",
    }

    for key in returnValue:
        if type(returnValue[key]) == str:
            returnValue[key] = [returnValue[key]]
        else:
            returnValue[key] = ["/".join(returnValue[key])]
    
    return returnValue

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    parser.add_argument('--forceMp3Tag',action='store_true',help="Always rewrite mp3 tags")

gOptions = None
gDatabase = None # These globals are overwritten by QSArchive.py, but we define them to keep PyLint happy
register_comment()

def main() -> None:
    if gOptions.excerptMp3 == 'remote':
        Alert.info("All excerpt mp3 links go to remote servers. No mp3 files will be tagged.")
        return # No need to run TagMp3 if all excerpt files are remote
    
    changeCount = sameCount = 0
    for x in gDatabase["excerpts"]:
        if gOptions.events != "All" and x["event"] not in gOptions.events:
            continue # Only tag mp3 files for the specifed events
        if not x["fileNumber"]:
            continue # Ignore session excerpts
        
        tags = ExcerptTags(x)

        path = Utils.Mp3Link(x,directoryDepth=0)
        try:
            fileTags = EasyID3(path)
        except mutagen.id3.ID3NoHeaderError:
            fileTags = mutagen.File(path,easy=True)
            fileTags.add_tags()
            Alert.extra("Added tags to",path)

        if tags != dict(fileTags) or gOptions.forceMp3Tag:
            fileTags.delete()
            for t in tags:
                fileTags[t] = tags[t]
            fileTags.save(v1=2,v2_version=3)
            changeCount += 1
            Alert.extra("Updated tags in",path)
        else:
            sameCount += 1
        lastFileTags = fileTags
    
    Alert.info("Updated tags in",changeCount,"mp3 files;",sameCount,"files unchaged.")

