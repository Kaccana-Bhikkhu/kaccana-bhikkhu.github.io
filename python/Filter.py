"""A module that implements filters for events, sessions, excerpts, and annotations."""

from __future__ import annotations

from collections.abc import Iterator, Iterable, Callable

Filter = Callable[[dict],bool]
"Returns whether the dict matches our filter function."

gDatabase = None # This will be overwritten by the main program

class InverseSet:
    """A class which contains everything except the objects in self.inverse"""
    inverse: set

    def __init__(self,inverse = None):
        if inverse is None:
            self.inverse = set()
        else:
            self.inverse = inverse
    
    def __contains__(self,item):
        return item not in self.inverse
    
    def __repr__(self):
        return f"InverseSet({repr(self.inverse)})"

All = InverseSet(frozenset())

def StrToSet(item:str|set) -> set:
    """Convert a single string to a set containing that string."""
    if type(item) == str:
        return {item}
    else:
        return item

def Apply(items:Iterable[dict],filter: Filter) -> Iterable[dict]:
    """Apply filter to items."""
    for i in items:
        if filter(i):
            yield i

def Indexes(items:Iterable[dict],filter: Filter) -> Iterable[int]:
    """Apply filter to items."""
    for n,i in enumerate(items):
        if filter(i):
            yield n

def _Tag(item: dict,tag:set(str),kind:set(str),category:set(str)) -> bool:
    "Helper function for Tag."

    returnValue = False
    for t in item.get("tags",()):
        if t in tag:
            returnValue = True
    
    if returnValue and "kind" in item:
        if item["kind"] not in kind:
            returnValue = False
        if gDatabase["kind"][item["kind"]]["category"] not in category:
            returnValue = False
    
    if not returnValue:
        return any(_Tag(annotation,tag,kind,category) for annotation in item.get("annotations",()))
    else:
        return True

def Tag(tag: str|set(str),kind:str|set(str) = All,category:str|set(str) = All) -> Filter:
    """Returns a Filter that passes any item with a given tag.
    If kind or category is specified, return only excerpts which have an item of that sort with a matching tag."""

    tag = StrToSet(tag)
    kind = StrToSet(kind)
    category = StrToSet(category)

    return lambda item,tag=tag,kind=kind,category=category: _Tag(item,tag,kind,category)

def AllTags(item: dict) -> set:
    """Return the set of all tags in item, which is either an excerpt or an annotation."""
    allTags = set(item["tags"])

    for annotation in item.get("annotations",()):
        allTags.update(annotation.get("tags",()))

    return allTags

def AllTeachers(item: dict) -> set:
    """Return the set of all teachers in item, which is either an excerpt or an annotation."""
    allTeachers = set(item.get("teachers",()))

    for annotation in item.get("annotations",()):
        allTeachers.update(annotation.get("teachers",()))

    return allTeachers