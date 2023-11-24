"""The FileRegister base class maintains a cache of information about a group of semi-persistent files that
are typically updated every time the program runs.
Subclasses specify what information to store and how to use it.
The ChecksumWriter subclass stores checksums of utf-8 files. When requested to write a file, it touches the
disk only if the checksum has changed."""

from __future__ import annotations

from typing import TypedDict
from enum import Enum, auto
from datetime import datetime
import json, contextlib, copy, os, re
import posixpath
import hashlib
import Alert, Utils

class Status(Enum):
    STALE = auto()          # File loaded from disk cache but not registered
    UNCHANGED = auto()      # File registered; its record matched the cache
    UPDATED = auto()        # File registered; its record did not match the cache and has been updated 
    NEW = auto()            # New file registered that had no record in the cache
    BLOCKED = auto()        # There are changes to be made in the file, but something stopped us making them

Record = TypedDict("Record",{"_status": Status,"_modified": datetime})
"""Stores the information about a file. The elements requred by FileRegister are:
_status: the file status as described above
_modified: the date/time the file was last modified or registered
"""

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

class FileRegister():
    """The FileRegister base class maintains a cache of information about a group of semi-persistent files that
    are typically updated every time the program runs.
    Subclasses specify what information to store and how to use it."""
    basePath: str               # All file paths are relative to this
    cacheFile: str              # Path to the register cache file (.json format)
    record: dict[str,Record]    # Stores a record of each file; key = path
    exactDates: bool            # If True, key "_modified" is the file modification date.
                                # If False, key "_modified" is the last time the file was registered.

    def __init__(self,basePath: str,cacheFile: str,exactDates = False):
        self.basePath = basePath
        self.cacheFile = cacheFile
        self.exactDates = exactDates

        cachePath = posixpath.join(self.basePath,self.cacheFile)
        try:
            with open(cachePath, 'r', encoding='utf-8') as file:
                rawCache = json.load(file)
        except FileNotFoundError:
            rawCache = {}
        except json.JSONDecodeError:
            Alert.caution("FileRegister error when reading JSON cache",cachePath,". Beginning with an empty register.")
            rawCache = {}
        
        self.record = {fileName:self.JsonItemToRecord(data) for fileName,data in rawCache.items()}

    def CheckStatus(self,fileName: str,recordData: Record) -> Status:
        """Check the status value that would be returned if we registered this record,
        but don't change anything."""

        returnValue = Status.UNCHANGED
        if fileName in self.record:
            recordCopy = copy.copy(self.record[fileName])
            del recordCopy["_status"]
            del recordCopy["_modified"]
            if recordData != recordCopy:
                returnValue = Status.UPDATED
        else:
            returnValue = Status.NEW

        return returnValue

    def UpdatedOnDisk(self,fileName,checkDetailedContents = False) -> bool:
        """Check whether the file has been modified on disk.
        If checkDetailedContents, call ReadRecordFromDisk and compare.
        Otherwise, if self.excactDates, compare the file modified date with the cache.
        If neither of these are the case, return False if the file exists.
        If fileName is not in the cache, return True if the file exists."""

        fullPath = posixpath.join(self.basePath,fileName)
        if fileName in self.record:
            dataInCache = self.record[fileName]
            try:
                if checkDetailedContents:
                    dataOnDisk = self.ReadRecordFromDisk(fileName)
                    dataOnDisk["_status"] = dataInCache["_status"]
                    dataOnDisk["_modified"] = dataInCache["_modified"]
                    return dataOnDisk != dataInCache
                elif self.exactDates:
                    return Utils.ModificationDate(fullPath) != dataInCache["_modified"]
                else:
                    return not os.path.isfile(fullPath)
            except FileNotFoundError:
                return True
        else:
            return os.path.isfile(fullPath)

    def Register(self,fileName: str,recordData: Record) -> Status:
        """Register a file and its associated record.
        Returns the record status."""

        returnValue = self.CheckStatus(fileName,recordData)
        recordData["_status"] = returnValue
        self.record[fileName] = recordData
        self.UpdateModifiedDate(fileName)
        return returnValue

    def UpdateModifiedDate(self,fileName) -> None:
        """Update key "_modified" for record fileName."""
        if self.exactDates:
            with contextlib.suppress(FileNotFoundError):
                self.record[fileName]["_modified"] = Utils.ModificationDate(fileName)
        else:
            self.record[fileName]["_modified"] = datetime.now()

    def __enter__(self) -> FileRegister:
        return self

    def __exit__(self,exc_type, exc_val, exc_tb) -> None:
        self.Flush(disposingObject=True)

    def Flush(self,markAsStale:bool = False,disposingObject:bool = False) -> None:
        """Write the cache records to disk.
        markAsStale: Set status.STALE as if we had just read the cache from disk.
        disposingObject: The object will never be used again, so no need to preserve record."""
        
        if disposingObject:
            writeDict = self.record
        else:
            writeDict = {fileName:copy.copy(data) for fileName,data in self.record.items()}
        writeDict = {fileName:self.RecordToJsonItem(data) for fileName,data in writeDict.items()}

        with open(posixpath.join(self.basePath,self.cacheFile), 'w', encoding='utf-8') as file:
            json.dump(writeDict, file, ensure_ascii=False, indent=2)
        
        if markAsStale:
            for key in self.record:
                self.record[key]["_status"] = Status.STALE

    def Count(self,status: Status) -> int:
        "Return the number of records which have this status."
        return sum(r["_status"] == status for r in self.record.values())

    def StatusSummary(self,unregisteredStr = "unregistered.") -> str:
        "Summarize the status of our records."

        return f"{self.Count(Status.NEW)} new, {self.Count(Status.UPDATED)} updated, {self.Count(Status.UNCHANGED)} unchanged, {self.Count(Status.STALE)} {unregisteredStr}"

    def ReadRecordFromDisk(self,fileName) -> Record:
        """Reconstruct a record from the information on disk.
        Raise FileNotFoundError if the file does not exist.
        Subclasses should extend as necessary."""
        
        path = posixpath.join(self.basePath,fileName)
        if os.path.isfile(path):
            return {}
        else:
            raise FileNotFoundError(f"{path} is not found or is not a file.")

    def JsonItemToRecord(self,data: dict) -> Record:
        """Convert information read from the json cache file to a Record.
        Data is not reused, so the function can operate in-place.
        Subclasses can extend as necessary."""

        data["_status"] = Status.STALE
        data["_modified"] = datetime.strptime(data["_modified"],DATETIME_FORMAT)
        return data

    def RecordToJsonItem(self,recordData: Record) -> dict:
        """Perform the reverse of JsonItemToRecord in preparation for flushing.
        Can opereate (partially) in place, as a shallow copy of record has already been made.
        Subclasses can extend as necessary."""
        
        del recordData["_status"]
        recordData["_modified"] = recordData["_modified"].strftime(DATETIME_FORMAT)
        return recordData

# Write the file to disk if...
class Write(Enum):
    ALWAYS = auto()                 # always.
    CHECKSUM_CHANGED = auto()       # the new checksum differs from the cached checksum.
    DESTINATION_UNCHANGED = auto()  # the checksum differs and the destination is unchanged.
                                    # This protects changes to the destination file we might want to save.
                                    # (Status.BLOCKED in this case.)
    DESTINATION_CHANGED = auto()    # the checksum differs or the destination has changed (default).
                                    # (UpdatedOnDisk returns True)

class ChecksumWriter(FileRegister):
    """Stores checksums of utf-8 files. When requested to write a file, it touches the
    disk only if the checksum has changed."""

    def __init__(self,basePath: str,cacheFile: str = "ChecksumCache.json",exactDates = False):
        super().__init__(basePath,cacheFile,exactDates)
    
    def __enter__(self) -> ChecksumWriter:
        return self

    def WriteFile(self,fileName: str,fileContents: str,writeCondition:Write = Write.DESTINATION_CHANGED) -> Status:
        """Write fileContents to fileName if the stored checksum differs from fileContents."""

        fullPath = posixpath.join(self.basePath,fileName)
        os.makedirs(posixpath.split(fullPath)[0],exist_ok=True)

        fileContents += "\n" # Append a newline to mimic printing the string.
        utf8Encoded = fileContents.encode("utf-8")
        checksum = hashlib.md5(utf8Encoded,usedforsecurity=False).hexdigest()

        if writeCondition in {Write.DESTINATION_CHANGED,Write.DESTINATION_UNCHANGED}:
            updatedOnDisk = self.UpdatedOnDisk(fileName,checkDetailedContents=False)
        else:
            updatedOnDisk = False
        
        if writeCondition == Write.DESTINATION_UNCHANGED:
            if updatedOnDisk:
                if fileName in self.record:
                    self.record[fileName]["_status"] = Status.BLOCKED
                    return Status.BLOCKED

        newRecord = {"checksum":checksum}
        status = self.Register(fileName,newRecord)
        if writeCondition == Write.DESTINATION_CHANGED and updatedOnDisk:
            status = Status.UPDATED
        if writeCondition == Write.ALWAYS:
            status = Status.UPDATED
        
        if status != Status.UNCHANGED:
            with open(fullPath, 'wb') as file:
                file.write(utf8Encoded)
            self.UpdateModifiedDate(fileName)
            self.record[fileName]["_status"] = status
        
        return status
    
    def ReadRecordFromDisk(self, fileName) -> Record:
        fullPath = posixpath.join(self.basePath,fileName)
        with open(fullPath, 'rb') as file:
            contents = file.read()
        
        checksum = hashlib.md5(contents,usedforsecurity=False).hexdigest()
        return {"checksum":checksum}

    def DeleteStaleFiles(self,filterRegex = ".*") -> int:
        """Delete stale files appearing in the register if their full path matches filterRegex."""

        deleteCount = 0
        matcher = re.compile(filterRegex)
        for r in list(self.record):
            if self.record[r]["_status"] == Status.STALE and matcher.match(r):
                try:
                     os.remove(posixpath.join(self.basePath,r))
                     deleteCount += 1
                except FileNotFoundError:
                    pass
                del self.record[r]
        return deleteCount
    
    def DeleteUnregisteredFiles(self,directory = "",filterRegex = ".*") -> int:
        """Delete files in directory (relative to baseDir) that are either stale or unregistered and
        that match filterRegex."""

        deleteCount = 0
        matcher = re.compile(filterRegex)
        baseDir = posixpath.join(self.basePath,directory)
        stale = {"_status":Status.STALE}
        for fileName in sorted(os.listdir(baseDir)):
            fullPath = posixpath.join(baseDir,fileName)
            relativePath = posixpath.join(directory,fileName)
            if matcher.match(fullPath) and self.record.get(relativePath,stale)["_status"] == Status.STALE:
                try:
                     os.remove(fullPath)
                     deleteCount += 1
                except FileNotFoundError:
                    pass
                self.record.pop(relativePath,None)

        return deleteCount
                     
