"""Utility files to support QAarchive.py modules"""

from datetime import timedelta

def StrToTimeDelta(inStr):
    "Convert a string with format mm:ss or hh:mm:ss to a timedelta object"
    
    numbers = str.split(inStr,":")
    try:
        if len(numbers) == 2:
            return timedelta(minutes = int(numbers[0]),seconds = int(numbers[1]))
        elif len(numbers) == 3:
            return timedelta(hours = int(numbers[0]),minutes = int(numbers[1]),seconds = int(numbers[2]))
    except ValueError:
        pass
        
    raise ValueError(inStr + " cannot be converted to a time.")
