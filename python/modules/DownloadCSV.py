"""Use Mp3DirectCut.exe to split the session audio files into individual excerpts based on start and end times from Database.json"""

from __future__ import annotations

import os, re
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import shutil
from typing import List
from ParseCSV import CSVToDictList, DictFromPairs
import Alert

def BuildSheetUrl(docId: str, sheetId: str):
    "From https://stackoverflow.com/excerpts/12842341/download-google-docs-public-spreadsheet-to-csv-with-python"
    
    return f'https://docs.google.com/spreadsheets/d/{docId}/export?format=csv&gid={sheetId}'

def DownloadFile(url:str,filename:str,retries:int = 2):
    
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url) as remoteFile:
                with open(filename,'wb') as localFile:
                    shutil.copyfileobj(remoteFile, localFile)
        except urllib.error.HTTPError:
            if attempt < retries:
                Alert.caution(f"HTTP error when attempting to download {filename}. Retrying.")
            else:
                Alert.error(f"HTTP error when attempting to download {filename}. Giving up after {retries + 1} attempts.")
        

def DownloadSheetCSV(docId: str, sheetId: str, filePath: str) -> None:
    "Download a Google Sheet with the given docId and sheetId to filePath"
    
    url = BuildSheetUrl(docId,sheetId)
    DownloadFile(url,filePath)

def DownloadSummarySheet() -> None:
    "Download the Summary sheet to the csv directory"
        
    if not os.path.exists(gOptions.csvDir):
        os.makedirs(gOptions.csvDir)
        
    DownloadSheetCSV(gOptions.spreadsheetId,gOptions.summarySheetID,gOptions.summaryFilePath)

def ReadSheetIds() -> dict:
    "Read Summary.csv and return a dict {sheetName : sheetId}"
    
    with open(os.path.join(gOptions.csvDir,'Summary.csv'),encoding='utf8') as file:
        CSVToDictList(file,skipLines = 1,endOfSection = '<---->',camelCase = False)
            # Skip the first half of the summary file
        
        sheetIds = CSVToDictList(file,camelCase = False,skipLines = 2)
    
    return DictFromPairs(sheetIds,'Sheet','gid',camelCase=False)

def DownloadSheets(sheetIds: dict) -> None:
    "Download the sheets specified by the sheetIds in the form {sheetName : sheetId}"
    
    with ThreadPoolExecutor() as pool:
        for sheetName,sheetId in sheetIds.items():
            pool.submit(DownloadSheetCSV,gOptions.spreadsheetId,sheetId,os.path.join(gOptions.csvDir,sheetName + '.csv'))

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--spreadsheet',type=str, help='URL of the QS Archive main Google Sheet')
    parser.add_argument('--summarySheetID',type=int,default = 0,help='GID of the "Summary" sheet in spreadsheet')
    parser.add_argument('--sheets',type=str,default='Default',help='Download this list of named sheets; Default: Tags and the sheets specified by --events')
    parser.add_argument('--csvDir',type=str,default='csv',help="Read/write csv files in this directory; Default: ./csv")

def ParseArguments(options) -> None:
    if not options.spreadsheet:
        Alert.error("A spreadsheet must be specified using --spreadsheet")
        return

    spreadsheetMatch = re.search(r'/d/([^/]*)/',options.spreadsheet)
    if not spreadsheetMatch:
        Alert.error("Cannot find a spreadsheet ID in --spreadsheet",repr(options.spreadsheet))
        return
    
    options.spreadsheetId = spreadsheetMatch.groups()[0]
    options.summaryFilePath = os.path.join(options.csvDir,'Summary.csv')

def Initialize() -> None:
    pass

gOptions = None

def main():
    """ Split the Q&A session mp3 files into individual excerpts.
    Read the beginning and end points from Database.json."""
    
    downloadSummary = False
    if gOptions.sheets != 'All' and gOptions.sheets != 'Default':
        gOptions.sheets = gOptions.sheets.split(',')
        if 'Summary' in gOptions.sheets:
            downloadSummary = True
            gOptions.sheets.remove('Summary')
        
    if os.path.isfile(gOptions.summaryFilePath) and gOptions.sheets != 'All' and not downloadSummary:
        oldSheetIds = ReadSheetIds()
        
        allEvents = [event for event in oldSheetIds if re.match(".*[0-9]{4}",event)]
        
        defaultSheets = ['Tag','Teacher','Reference'] # Sheets to download unless otherwise specified
        if gOptions.sheets == 'Default': # Default is to download event files and defaultSheets since other csv files rarely change
            if gOptions.events == 'All':
                gOptions.sheets = allEvents + defaultSheets
            else:
                gOptions.sheets = gOptions.events + defaultSheets
        
        # If there's a sheet we don't recognize, download Summary.csv to see if we can find it
        for sheet in gOptions.sheets:
            if sheet not in oldSheetIds:
                downloadSummary = True
    else:
        downloadSummary = True
        
    if downloadSummary:
        DownloadSummarySheet()
        sheetIds = ReadSheetIds()
        Alert.info("Downloaded Summary.csv")
    else:
        sheetIds = oldSheetIds
        Alert.info("Didn't download Summary.csv")
        
    
    sheetIds.pop('Summary',None) # No need to download summary again
    sheetIds = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName[0] != '_'}
        # Don't download special sheets begining with _
        
    if gOptions.sheets != 'All':
        for sheetName in gOptions.sheets:
            if sheetName not in sheetIds:
                Alert.warning('Warning: Sheet name',repr(sheetName),'does not appear in the Summary sheet and will not be downloaded.')
        
        sheetsToDownload = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName in gOptions.sheets}
        sheetsToDownload.update((sheetName,sheetId) for sheetName,sheetId in sheetIds.items() if sheetName.rstrip('x') in gOptions.sheets)
            # Download sheet WR2015x if WR2015 appears in gOptions.sheets
    else:
        sheetsToDownload = sheetIds
    
    DownloadSheets(sheetsToDownload)
    downloadedSheets = list(sheetsToDownload.keys())
    if downloadSummary:
        downloadedSheets = ['Summary'] + downloadedSheets
    Alert.info(f'Downloaded {len(downloadedSheets)} sheets: {", ".join(downloadedSheets)}')
