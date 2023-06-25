"""A module to print and log errors and notifications taking into account verbosity and debug status."""
from __future__ import annotations

verbosity = 0
ObjectPrinter = repr # Call this function to convert items to print into strings

class AlertClass:
    def __init__(self,name: str,message: str|None = None, printAtVerbosity: int = 0, logging:bool = False,indent = 0):
        "Defines a specific type of alert."
        self.name = name
        self.message = message if message is not None else name + ":"
        self.printAtVerbosity = printAtVerbosity
        self.logging = logging # log these alerts?
        self.log = {} # A log of e
        self.indent = indent

    def Show(self,*items):
        """Generate aan alert from a list of items to print.
        Print it if verbosity is high enough.
        Log it if we are logging."""
        if verbosity >= self.printAtVerbosity or self.logging:
            strings = []
            if self.indent:
                strings.append(" " * (self.indent - 1))
            if self.message:
                strings.append(self.message)
            for item in items:
                if type(item) == str:
                    strings.append(item)
                else:
                    strings.append(ObjectPrinter(item))
            
            if verbosity >= self.printAtVerbosity:
                print(" ".join(strings))

error = AlertClass("Error","ERROR:",printAtVerbosity=-2,logging=True)
warning = AlertClass("Warning","WARNING:",printAtVerbosity = -1,logging = True)
caution = AlertClass("Caaution",printAtVerbosity = 0, logging = True)
notice = AlertClass("Notice",printAtVerbosity = 1,logging=True)

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