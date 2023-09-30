"""List properties of all mp3 files in a given directory."""

from __future__ import annotations

import os,sys,argparse
from mutagen.mp3 import MP3

parser = argparse.ArgumentParser(description="List the properties of mp3 files in a given directory.")
parser.add_argument('directory',type=str,help="Directory to list mp3 files")

options = parser.parse_args(sys.argv[1:])

for fileName in sorted(os.listdir(options.directory)):
    path = os.path.join(options.directory,fileName)
    if fileName.endswith(".mp3"):
        file = MP3(os.path.join(options.directory,fileName))
        print('\t'.join((fileName,str(file.info.length))))