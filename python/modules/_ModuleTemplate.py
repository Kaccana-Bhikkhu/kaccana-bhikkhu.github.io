"""A template for creating new modules.
"""

from __future__ import annotations

import os
import Utils, Alert
from typing import NamedTuple, Iterable

def AddArguments(parser) -> None:
    "Add command-line arguments used by this module"
    # parser.add_argument('--option',**Utils.STORE_TRUE,help='This is an option.')

def ParseArguments() -> None:
    pass    

def Initialize() -> None:
    pass

gOptions = None
gDatabase:dict[str] = {} # These globals are overwritten by QSArchive.py, but we define them to keep Pylance happy

def main() -> None:
    Alert.extra("Ran the module.")
    
