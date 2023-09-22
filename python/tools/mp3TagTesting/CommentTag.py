"""Sandbox to figure out how to use comments in mutagen"""

from __future__ import annotations

import os
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, COMM
import unicodedata

def RemoveDiacritics(string: str) -> str:
    "Remove diacritics from string."
    return unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')

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
            encoding=0, lang='\x00\x00\x00', desc=desc, text=[RemoveDiacritics(t) for t in value]))
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

tagDict = {}
directory = './'
#directory = 'python/tools/mp3Tag'
for fileName in sorted(os.listdir(directory)):
    if fileName.endswith('.mp3'):
        tags = ReadID3(os.path.join(directory,fileName))
        print(fileName + ':')
        PrintID3(tags)
        tagDict[fileName[:-4]] = tags

register_comment()
easy = EasyID3(os.path.join(directory,"Easy.mp3"))
print("Inital easy contents:",easy)

"""
hard = ID3("Mutagen.mp3")
print("Inital ID3 contents:",hard)
hard['comment'] = 'Comment added by mutagen.easyid3'
print("After adding comment:",hard)
hard.save()"""
