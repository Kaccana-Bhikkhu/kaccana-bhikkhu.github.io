"""Use Mp3DirectCut.exe to split the session audio files into individual questions based on start and end times from Database.json"""

import os, re
import urllib.request
import shutil
from typing import List
from ParseCSV import CSVToDictList, DictFromPairs

def BuildSheetUrl(docId: str, sheetId: str):
    "From https://stackoverflow.com/questions/12842341/download-google-docs-public-spreadsheet-to-csv-with-python"
    
    return f'https://docs.google.com/spreadsheets/d/{docId}/export?format=csv&gid={sheetId}'

def DownloadFile(url,filename,checkSize = True):
    if os.path.exists(filename):
        if checkSize:
            localSize = os.path.getsize(filename)
        else:
            return 0
    else:
        localSize = 0
        
    with urllib.request.urlopen(url) as remoteFile:
        info = remoteFile.info()
        if "Content-Length" in info:
            remoteSize = int(remoteFile.info()["Content-Length"])
            if localSize == remoteSize:
                return 0
        
        with open(filename,'wb') as localFile:
            shutil.copyfileobj(remoteFile, localFile)
            
        if localSize > 0:
            return 2
        else:
            return 1

def DownloadSheetCSV(docId: str, sheetId: str, filePath: str) -> None:
    "Download a Google Sheet with the given docId and sheetId to filePath"
    
    url = BuildSheetUrl(docId,sheetId)
    DownloadFile(url,filePath)

def DownloadSummarySheet() -> None:
    "Download the Summary sheet to the csv directory"
        
    if not os.path.exists(gOptions.csvDir):
        os.makedirs(gOptions.csvDir)
    
    summarySheetId = re.search(r'gid=([0-9]*)',gOptions.spreadsheet).groups()[0]
    
    DownloadSheetCSV(gOptions.spreadsheetId,summarySheetId,gOptions.summaryFilePath)

def ReadSheetIds() -> dict:
    "Read Summary.csv and return a dict {sheetName : sheetId}"
    
    with open(os.path.join(gOptions.csvDir,'Summary.csv'),encoding='utf8') as file:
        CSVToDictList(file,skipLines = 1,endOfSection = '<---->')
            # Skip the first half of the summary file
        
        sheetIds = CSVToDictList(file,skipLines = 2)
    
    return DictFromPairs(sheetIds,'Sheet','gid')

def DownloadSheets(sheetIds: dict) -> None:
    "Download the sheets specified by the sheetIds in the form {sheetName : sheetId}"
    
    for sheetName,sheetId in sheetIds.items():
        DownloadSheetCSV(gOptions.spreadsheetId,sheetId,os.path.join(gOptions.csvDir,sheetName + '.csv'))

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--spreadsheet',type=str,default='https://docs.google.com/spreadsheets/d/1PNFs3BaaXep-bdeWgahgV9c-i7sqd_QHr3kwRHLvjrg/edit#gid=2007732801', help='URL of the QA Archive Main sheet Summary')
    parser.add_argument('--sheets',type=str,default='Default',help='Download this list of named sheets; Default: Tags and the sheets specified by --events')
    parser.add_argument('--csvDir',type=str,default='csv',help="Read/write csv files in this directory; Default: ./csv")
    
gOptions = None

def main(clOptions,_):
    """ Split the Q&A session mp3 files into individual questions.
    Read the beginning and end points from Database.json."""
    
    global gOptions
    gOptions = clOptions
    
    gOptions.spreadsheetId = re.search(r'/d/([^/]*)/',gOptions.spreadsheet).groups()[0]
    gOptions.summaryFilePath = os.path.join(gOptions.csvDir,'Summary.csv')
    
    if gOptions.sheets != 'All' and gOptions.sheets != 'Default':
        gOptions.sheets = gOptions.sheets.split(',')
        
    downloadSummary = True
    if os.path.isfile(gOptions.summaryFilePath) and gOptions.sheets != 'All':
        oldSheetIds = ReadSheetIds()
        
        allEvents = [event for event in oldSheetIds if re.match(".*[0-9]{4}",event)]
        
        if gOptions.sheets == 'Default': # Default is to download event files and Tag.csv since the other csv files rarely change
            if gOptions.events == 'All':
                gOptions.sheets = allEvents + ['Tag']
            else:
                gOptions.sheets = gOptions.events + ['Tag']
        
        downloadSummary = False
        for sheet in gOptions.sheets:
            if sheet not in oldSheetIds:
                downloadSummary = True
        
    if downloadSummary:
        DownloadSummarySheet()
        sheetIds = ReadSheetIds()
        if gOptions.verbose > 1:
            print("Downloaded Summary.csv")
    else:
        sheetIds = oldSheetIds
        if gOptions.verbose > 1:
            print("Didn't download Summary.csv")
        
    
    sheetIds.pop('Summary',None) # No need to download summary again
    sheetIds = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName[0] != '_'}
        # Don't download special sheets begining with _
        
    if gOptions.sheets != 'All':
        for sheetName in gOptions.sheets:
            if sheetName not in sheetIds:
                if gOptions.verbose >= 0:
                    print('Warning: Sheet name',repr(sheetName),'does not appear in the Summary sheet and will not be downloaded.')
        
        sheetIds = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName in gOptions.sheets}
    
    DownloadSheets(sheetIds)
    if gOptions.verbose > 0:
        print(f'   Downloaded {len(sheetIds)} sheets: {", ".join(sheetIds.keys())}')
    