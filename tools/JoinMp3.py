"""Simple script to test join mp3 files"""

import os,sys

sys.path.append('python') # Look for modules in the ./python in the same directory as QAarchive.py

import Mp3DirectCut

Mp3DirectCut.SetExecutable(os.path.join('tools','Mp3DirectCut'))

fileList = next(os.walk('tools/mp3Join'), (None, None, []))[2]
fileList = [os.path.join('tools','mp3Join',file) for file in fileList if file[-4:] == '.mp3']

print('Joining:',fileList)

Mp3DirectCut.Join(fileList,'tools/result.mp3')