"""Use Mp3DirectCut.exe to split the session audio files into individual excerpts based on start and end times from Database.json"""

from __future__ import annotations

import os, re, csv, time
import urllib.request, urllib.error
from typing import List
from ParseCSV import CSVToDictList, DictFromPairs
import Alert, Utils
from FileRegister import HashWriter

def BuildSheetUrl(docId: str, sheetId: str):
    "From https://stackoverflow.com/excerpts/12842341/download-google-docs-public-spreadsheet-to-csv-with-python"
    
    return f'https://docs.google.com/spreadsheets/d/{docId}/export?format=csv&gid={sheetId}'

def DownloadSmallFile(filename:str,url:str,retries:int = 2):
    "Load the remote and on-disk copies of filename, compare, and write to disk only when needed."
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url) as remoteFile:
                remoteData = remoteFile.read()
            if os.path.isfile(filename):
                with open(filename,'rb') as localFile:
                    localData = localFile.read()
                if remoteData == localData:
                    return # If the local file already matches the remote file, don't touch it to keep the modification date.
            with open(filename,'wb') as localFile:
                localFile.write(remoteData)
            return
        except urllib.error.HTTPError:
            if attempt < retries:
                Alert.caution(f"HTTP error when attempting to download {filename}. Retrying.")
            else:
                Alert.error(f"HTTP error when attempting to download {filename}. Giving up after {retries + 1} attempts.")
        

def DownloadSheetCSV(docId: str, sheetId: str, filename: str, writer: HashWriter|None = None) -> None:
    """Download a Google Sheet with the given docId and sheetId to filename.
    Use writer if given."""
    
    url = BuildSheetUrl(docId,sheetId)
    if writer:
        writer.DownloadFile(filename,url,retries = 2)
    else:
        DownloadSmallFile(filename,url)

def DownloadSummarySheet() -> None:
    "Download the Summary sheet to the csv directory"
        
    DownloadSheetCSV(gOptions.spreadsheetId,gOptions.summarySheetID,Utils.PosixJoin(gOptions.csvDir,gOptions.summaryFile))

def ReadSummarySheet(printSheetName: bool = False) -> tuple[dict[str,str],dict[str,str]]:
    "Read Summary.csv and return two dicts {sheetName : sheetId} and {sheetName : modifiedDate (str)}"
    
    with open(os.path.join(gOptions.csvDir,'Summary.csv'),encoding='utf8') as file:
        CSVToDictList(file,skipLines = 1,endOfSection = '<---->',camelCase = False)
            # Skip the first half of the summary file
        
        reader = csv.reader(file)
        next(reader)
        sheetInfo = next(reader)
        try:
            if printSheetName:
                Alert.info("Reading from spreadsheet",repr(sheetInfo[sheetInfo.index("Spreadsheet:") + 1]))
        except (ValueError,IndexError):
            pass

        summarySheet = CSVToDictList(file,camelCase = False,skipLines = 0)
    
    sheetIds = DictFromPairs(summarySheet,'Sheet','gid',camelCase=False)
    if 'Modified' in summarySheet[0]:
        modDates = DictFromPairs(summarySheet,'Sheet','Modified',camelCase=False)
    else:
        modDates = {sheetName:"" for sheetName in sheetIds}

    return sheetIds,modDates

def DownloadSheets(sheetIds: dict,writer: HashWriter) -> None:
    "Download the sheets specified by the sheetIds in the form {sheetName : sheetId}"
    
    with Utils.ConditionalThreader() as pool:
        for sheetName,sheetId in sheetIds.items():
            pool.submit(DownloadSheetCSV,gOptions.spreadsheetId,sheetId,sheetName + '.csv',writer)

def AddArguments(parser):
    "Add command-line arguments used by this module"
    parser.add_argument('--spreadsheet',type=str, help='URL of the QS Archive main Google Sheet')
    parser.add_argument('--summarySheetID',type=int,default = 0,help='GID of the "Summary" sheet in spreadsheet')
    parser.add_argument('--sheets',type=str,default='Changed',help='Download this list of named sheets; Default: Changed')
    parser.add_argument('--csvDir',type=str,default='csv',help="Read/write csv files in this directory; Default: ./csv")

def ParseArguments() -> None:
    if not gOptions.spreadsheet:
        Alert.error("A spreadsheet must be specified using --spreadsheet")
        return

    spreadsheetMatch = re.search(r'/d/([^/]*)/',gOptions.spreadsheet)
    if not spreadsheetMatch:
        Alert.error("Cannot find a spreadsheet ID in --spreadsheet",repr(gOptions.spreadsheet))
        return
    
    gOptions.spreadsheetId = spreadsheetMatch.groups()[0]
    gOptions.summaryFile = 'Summary.csv'

def Initialize() -> None:
    pass

gOptions = None

def main():
    """ Split the Q&A session mp3 files into individual excerpts.
    Read the beginning and end points from Database.json."""
    
    downloadSummary = False
    if gOptions.sheets not in {'All','Default','Changed'}:
        gOptions.sheets = gOptions.sheets.split(',')
        if 'Summary' in gOptions.sheets:
            downloadSummary = True
            gOptions.sheets.remove('Summary')
    
    if gOptions.sheets == 'Changed':
        downloadSummary = True
        oldSheetIds,oldSheetModDates = ReadSummarySheet()
    elif os.path.isfile(Utils.PosixJoin(gOptions.csvDir,gOptions.summaryFile)) and gOptions.sheets != 'All' and not downloadSummary:
        oldSheetIds,_ = ReadSummarySheet()
        
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
        for retries in range(3):
            DownloadSummarySheet()
            sheetIds,sheetModDates = ReadSummarySheet(printSheetName=True)
            if len(sheetIds) > 2:
                break
            Alert.caution("The google sheet may be recalculating. Will try to download it again in 20 seconds.")
            time.sleep(20)

        Alert.info("Downloaded Summary.csv")
    else:
        sheetIds = oldSheetIds
        Alert.info("Didn't download Summary.csv")
    
    sheetIds.pop('Summary',None) # No need to download summary again
    sheetIds = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName[0] != '_'}
        # Don't download special sheets begining with _

    if gOptions.sheets == 'Changed':
        blankModDates = [sheetName for sheetName in sheetIds if not sheetModDates[sheetName].strip()]
        if blankModDates:
            Alert.caution(len(blankModDates),"sheets do not have a modification date and will not be downloaded:",blankModDates)
            Alert.notice("For AP QS Archive version 3.3 and earlier, use --sheets All or specify which sheets to download.")
        sheetsToDownload = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetModDates[sheetName] != oldSheetModDates.get(sheetName,None)}
    else:
        if gOptions.sheets != 'All':
            for sheetName in gOptions.sheets:
                if sheetName not in sheetIds:
                    Alert.warning('Warning: Sheet name',repr(sheetName),'does not appear in the Summary sheet and will not be downloaded.')
            
            sheetsToDownload = {sheetName:sheetId for sheetName,sheetId in sheetIds.items() if sheetName in gOptions.sheets}
            sheetsToDownload.update((sheetName,sheetId) for sheetName,sheetId in sheetIds.items() if sheetName.rstrip('x') in gOptions.sheets)
                # Download sheet WR2015x (for example) if WR2015 appears in gOptions.sheets
        else:
            sheetsToDownload = sheetIds
    
    with HashWriter(gOptions.csvDir,exactDates=True) as writer:
        DownloadSheets(sheetsToDownload,writer)
        writerReport = writer.StatusSummary()
    
    downloadedSheets = list(sheetsToDownload.keys())
    if downloadSummary:
        downloadedSheets = ['Summary'] + downloadedSheets
    Alert.info(f'Downloaded {len(downloadedSheets)} sheets: {", ".join(downloadedSheets)}')
    Alert.extra(f'csv files:',writerReport)
