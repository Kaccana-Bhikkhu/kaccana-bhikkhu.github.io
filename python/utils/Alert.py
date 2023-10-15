"""A module to print and log errors and notifications taking into account verbosity and debug status."""
from __future__ import annotations
from typing import Any

verbosity = 0
ObjectPrinter = repr # Call this function to convert items to print into strings

class AlertClass:
    def __init__(self,name: str,message: str|None = None, plural = None, printAtVerbosity: int = 0, logging:bool = False,indent = 0,lineSpacing = 0):
        "Defines a specific type of alert."
        self.name = name
        self.message = message if message is not None else name + ":"
        if plural:
            self.plural = plural
        elif plural is None:
            self.plural = self.name + "s"
        else:
            self.plural = self.name
        self.printAtVerbosity = printAtVerbosity
        self.logging = logging # log these alerts?
        self.log = {} # A log of printed alerts
        self.count = 0
        self.indent = indent # print this many spaces before the message
        self.lineSpacing = lineSpacing # print this many blank lines after the alert

    def Show(self,*items,indent:int|None = None) -> None:
        """Generate an alert from a list of items to print.
        Print it if verbosity is high enough.
        Log it if we are logging."""
        if items:
            self.count += 1
        if verbosity >= self.printAtVerbosity or self.logging:
            if indent is None:
                indent = self.indent
            strings = []
            if indent:
                strings.append(" " * (indent - 1))
            if self.message:
                strings.append(self.message)
            for item in items:
                if type(item) == str:
                    strings.append(item)
                else:
                    strings.append(ObjectPrinter(item))
            
            if verbosity >= self.printAtVerbosity:
                print(" ".join(strings))
                for _ in range(self.lineSpacing):
                    print()
    
    __call__ = Show

    def CountString(self) -> str:
        "Return a string describing how many alerts have occured."

        if self.count > 1:
            return f"{self.count} {self.plural}"
        elif self.count == 1:
            return f"{self.count} {self.name}"
        else:
            return ""

error = AlertClass("Error","ERROR:",printAtVerbosity=-2,logging=True,lineSpacing = 1)
warning = AlertClass("Warning","WARNING:",printAtVerbosity = -1,logging = True,lineSpacing = 1)
caution = AlertClass("Caution",printAtVerbosity = 0, logging = True,lineSpacing = 1)
notice = AlertClass("Notice",printAtVerbosity = 1,logging=True,lineSpacing = 1)

essential = AlertClass("Essential","",printAtVerbosity = -1,indent = 3)
structure = AlertClass("Structure","",printAtVerbosity = 0)
status = AlertClass("Status","",printAtVerbosity = 0,indent = 3)
info = AlertClass("Information","",printAtVerbosity = 1,indent = 3)
extra = AlertClass("Extra","",printAtVerbosity = 2,indent = 3)

debug = AlertClass("Debug","DEBUG:",printAtVerbosity=999,logging = False)

def Debugging(flag: bool):
    if flag:
        debug.printAtVerbosity = -999
        debug.logging = True
    else:
        debug.printAtVerbosity = 999
        debug.logging = False