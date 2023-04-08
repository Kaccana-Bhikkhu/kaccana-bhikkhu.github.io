"""Utility files to support QAarchive.py modules"""

from datetime import timedelta, datetime
import unicodedata
import re

def Mp3FileName(event:str ,session:int ,question:int) -> str:
    "Return the name of the mp3 file associated with a given event, session, and question"
    return f"{event}_S{session:02d}_Q{question:02d}.mp3"

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
        
    raise ValueError("'" + inStr + "' cannot be converted to a time.")

def TimeDeltaToStr(time):
    "Convert a timedelta object to the form [HH:]MM:SS"
    
    seconds = (time.days * 24 * 60 * 60) + time.seconds
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def ReformatDate(dateStr:str, formatStr:str = "%b %d, %Y") -> str:
    "Take a date formated as DD/MM/YYYY and reformat it as mmm d YYYY."
    
    date = datetime.strptime(dateStr,"%d/%m/%Y")
    
    return f'{date.strftime("%b. ")} {int(date.day)}, {int(date.year)}'

def FindSession(sessions:list, event:str ,sessionNum: int) -> dict:
    "Return the index of a session specified by event and sessionNum."
    
    for session in sessions:
        if session["event"] == event and session["sessionNumber"] == sessionNum:
            return session
    
    raise ValueError(f"Can't locate session {sessionNum} of event {event}")
    
    """if not sessionIndexCache: # For speed, create a dictionary of sessions the first time we run
        sessionIndexCache = {}
        s = database["sessions"]
        for index in range(len(s)):
            sessionIndexCache[(s[index]["event"],s[index]["sessionNumber"])] = index
    
    try:
        return sessionIndexCache[(event,sessionNum)]
    except KeyError:
        raise ValueError(f"Can't locate session {sessionNum} of event {event}")"""

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')