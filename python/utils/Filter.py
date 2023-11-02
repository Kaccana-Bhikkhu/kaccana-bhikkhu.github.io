"""A module that implements filters for events, sessions, excerpts, and annotations."""

from __future__ import annotations

from collections.abc import Iterable, Callable
from typing import Tuple
import Utils

gDatabase:dict[str] = {} # This will be overwritten by the main program

Filter = Callable[[dict],bool]
"Returns whether the dict matches our filter function."

def PassAll(_) -> bool:
    return True

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

def AllItems(excerpt: dict) -> Iterable[dict]:
    """If this is an excerpt, iterate over the excerpt and annotations.
    If not, iterate just this item."""

    yield excerpt
    yield from excerpt.get("annotations",())

def AllSingularItems(excerpt: dict) -> Iterable[dict]:
    """Same as AllItems, but yield the excerpt alone without its annotations, followed by the annotations."""

    if "annotations" in excerpt:
        temp = excerpt["annotations"]
        excerpt["annotations"] = ()
        yield excerpt
        excerpt["annotations"] = temp
        yield from excerpt["annotations"]
    else:
        yield excerpt

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

def Partition(items:Iterable[dict],filter: Filter) -> Tuple[list[dict],list[dict]]:
    "Split items into two lists depending on the filter function."

    trueList = []
    falseList = []

    for i in items:
        (trueList if filter(i) else falseList).append(i)
    
    return trueList,falseList

def _Kind(item: dict,kind:set(str),category:set(str)) -> bool:
    "Helper function for Tag."

    for i in AllItems(item):
        if (i["kind"] in kind) and (gDatabase["kind"][i["kind"]]["category"] in category):
            return True
    return False

def Kind(kind:str|set(str) = All,category:str|set(str) = All) -> Filter:
    """Returns a Filter that passes any item with a given tag.
    If kind or category is specified, return only excerpts which have an item of that sort with a matching tag."""

    kind = StrToSet(kind)
    category = StrToSet(category)

    return lambda item,kind=kind,category=category: _Kind(item,kind,category)

def _Tag(item: dict,tag:set(str),kind:set(str),category:set(str)) -> bool:
    "Helper function for Tag."

    for i in AllItems(item):
        for t in i.get("tags",()):
            if t in tag:
                if "kind" in i:
                    if (i["kind"] in kind) and (gDatabase["kind"][i["kind"]]["category"] in category):
                        return True
                else:
                    return True
    return False

def Tag(tag: str|set(str),kind:str|set(str) = All,category:str|set(str) = All) -> Filter:
    """Returns a Filter that passes any item with a given tag.
    If kind or category is specified, return only excerpts which have an item of that sort with a matching tag."""

    tag = StrToSet(tag)
    kind = StrToSet(kind)
    category = StrToSet(category)

    return lambda item,tag=tag,kind=kind,category=category: _Tag(item,tag,kind,category)

def _QTag(excerpt: dict,tag:str) -> bool:
    return tag in excerpt["tags"][0:excerpt["qTagCount"]]

def QTag(tag:str) -> Filter:
    """Returns excerpts in which tag appears as a qTag, in other words, the subject of a question."""

    return lambda excerpt,tag=tag: _QTag(excerpt,tag)

def ATag(tag:str) -> Filter:
    """Returns excerpts in which tag appears but not as a qTag, in other words, part of the answer to a question."""

    return lambda excerpt,tag=tag: _Tag(excerpt,tag,All,All) and not _QTag(excerpt,tag)

def _Teacher(item: dict,teacher:set(str),kind:set(str),category:set(str),quotesOthers:bool,quotedBy:bool) -> bool:
    "Helper function for Teacher."

    fullNames = set(gDatabase["teacher"][t]["fullName"] for t in teacher)

    for i in AllItems(item):
        for t in i.get("teachers",()):
            if t in teacher:
                if "kind" in i:
                    if (i["kind"] in kind) and (gDatabase["kind"][i["kind"]]["category"] in category):
                        if i["kind"] == "Indirect quote" and not quotesOthers:
                            return False
                        else:
                            return True
                else:
                    return True

        if i.get("kind") == "Indirect quote" and quotedBy:
            if i.get("tags",(None))[0] in fullNames:
                if (i["kind"] in kind) and (gDatabase["kind"][i["kind"]]["category"] in category):
                    return True
    
    return False

def Teacher(teacher: str|set(str),kind:str|set(str) = All,category:str|set(str) = All,quotesOthers = True,quotedBy = True) -> Filter:
    """Returns a Filter that passes any item with a given teacher.
    In the case of indirect quotes, pass items in which the teacher quotes others or is quoted by others depending on the flags
    If kind or category is specified, return only excerpts which have an item of that sort with a matching tag."""

    teacher = StrToSet(teacher)
    kind = StrToSet(kind)
    category = StrToSet(category)

    return lambda item,teacher=teacher,kind=kind,category=category: _Teacher(item,teacher,kind,category,quotesOthers,quotedBy)

def AllTags(item: dict) -> set:
    """Return the set of all tags in item, which is either an excerpt or an annotation."""
    allTags = set(item.get("tags",()))

    for annotation in item.get("annotations",()):
        allTags.update(annotation.get("tags",()))

    return allTags

def AllTagsOrdered(item: dict) -> list:
    """Return the set of all tags in item, which is either an excerpt or an annotation."""
    allTags = item["tags"]

    for annotation in item.get("annotations",()):
        Utils.ExtendUnique(allTags,annotation.get("tags",()))

    return allTags

def AllTeachers(item: dict) -> set:
    """Return the set of all teachers in item, which is either an excerpt or an annotation."""
    allTeachers = set(item.get("teachers",()))

    for annotation in item.get("annotations",()):
        allTeachers.update(annotation.get("teachers",()))

    return allTeachers