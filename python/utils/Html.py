"""Implements the PageDesc object and related functionality to """

from __future__ import annotations

from typing import NamedTuple, TypeVar
import pyratemp
import itertools
from pathlib import Path
from collections.abc import Iterator, Iterable, Callable
import copy
import Utils

class Wrapper(NamedTuple):
    "A prefix and suffix to wrap an html object in."
    prefix: str = ""
    suffix: str = ""
    def Wrap(self,contents: str, joinStr: str = "") -> str:
        items = []
        if self.prefix:
            items.append(self.prefix)
        items.append(contents)
        if self.suffix:
            items.append(self.suffix)
        return joinStr.join(items)
    
    __call__ = Wrap
    
class PageInfo(NamedTuple):
    "The most basic information about a webpage. titleIB means titleInBody"
    title: str|None = None
    file: str|None = None
    titleIB: str|None = None

    @property
    def titleInBody(self):
        if self.titleIB is not None:
            return self.titleIB
        else:
            return self.title

class Renderable:
    """An object that supports the Render method to (optionally) substitute attributes and then convert to a str."""

    def Render(self,**attributes) -> str:
        if attributes:
            clone = copy(self)
            for attribute,value in attributes.items():
                setattr(clone,attribute,value)
            return str(clone)
        else:
            return str(self)

def Render(item: Renderable | str,**attributes) -> str:
    try:
        return item.Render(**attributes)
    except AttributeError:
        return str(item)

class Menu(Renderable):
    items: list[PageInfo]
    menu_highlightedItem:int|None
    menu_separator:int|str
    menu_wrapper:Wrapper
    menu_highlightTags:Wrapper

    def __init__(self,items: list[PageInfo],highlightedItem:int|None = None,separator:int|str = 6,highlightTags:Wrapper = Wrapper("<b>","</b>"),wrapper:Wrapper = Wrapper()) -> None:
        """items: a list of PageInfo objects containing the menu text (title) and html link (file) of each menu item.
        highlightedItem: which (if any) of the menu items is highlighted.
        separator: html code between each menu item; defaults to 6 spaces.
        highlightTags: the tags to apply to the highlighted menu item."""
        self.items = items
        self.menu_highlightedItem = highlightedItem
        self.menu_separator = separator
        self.menu_wrapper = wrapper
        self.menu_highlightTags = highlightTags
    
    def __str__(self) -> str:
        """Return an html string corresponding to the rendered menu."""
        
        def RelativeLink(link: str) -> bool:
            return not ("://" in link or link.startswith("#"))

        # Render relative links as if the file is at directory depth 1. PageDesc.RenderWithTemplate will later produce the correct
        menuLinks = [f'<a href = "{"../" + i.file if RelativeLink(i.file) else i.file}">{i.title}</a>' for i in self.items]

        if self.menu_highlightedItem is not None:
            menuLinks[self.menu_highlightedItem] = self.menu_highlightTags.Wrap(menuLinks[self.menu_highlightedItem])

        separator = self.menu_separator
        if type(separator) == int:
            separator = " " + (separator - 1) * "&nbsp"

        rawMenu = separator.join(menuLinks)
        return self.menu_wrapper.Wrap(rawMenu,joinStr=" ")

    def HighlightItem(self,itemFileName:str) -> None:
        "Highlight the item (if any) corresponding to itemFileName."
        self.menu_highlightedItem = None
        for n,item in enumerate(self.items):
            if item.file == itemFileName:
                self.menu_highlightedItem = n
    
class PageDesc: # Define a dummy PageDesc class for the type definitions below
    pass

# Make these type annotations strings to maintain compatibility with Python 3.9
PageAugmentorType = "[str | tuple[PageInfo,str] | PageDesc]"
"""The acceptable types that can be passed to PageDesc.Augment."""

PageGeneratorMenuItem = "Callable[[PageDesc],Iterable[PageInfo|PageDesc]]"
"""Type defintion for a generator function that returns an iterator of pages associated with a menu item.
See PagesFromMenuGenerators for a full description."""

PageDescriptorMenuItem = "Iterable[PageInfo | str | tuple[PageInfo,str] | PageDesc]"
"""An iterable that describes a menu item and pages associate with it.
It first (optionally) yields a PageInfo object containing the menu title and link. If the first item isn't a PageInfo object, no menu item is generated, but pages are produced as below.
For each page associated with the menu it then yields one of the following:
    str: html of the page following the menu. The page title and file name are those associated with the menu item.
        Note: if the iterable returns more than one str value, the pages will overwrite each other
    tuple(PageInfo,str): PageInfo describes the page title and file name; str is the html content of the page following the menu
    PageDesc: The description of the page after the menu, which will be merged with the base page and menu.
"""

class PageDesc(Renderable):
    """A PageDesc object is used gradually build a complete description of the content of a page.
    When complete, the object will be passed to a pyratemp template to generate a page and write it to disk."""
    info: PageInfo
    numberedSections:int
    section:dict[int|str,str|Renderable]

    def __init__(self,info: PageInfo = PageInfo()) -> None:
        self.info = info # Basic information about the page
        self.numberedSections = 1
        self.section = {0:""} # A dict describing the content of the page. Sequential sections are given by integer keys, non-sequential sections by string keys.
    
    def Clone(self) -> PageDesc:
        """Clone this page so we can add more material to the new page without affecting the original."""
        return copy.deepcopy(self)

    def HasSection(self,sectionName: int|str) -> bool:
        return bool(self.section.get(sectionName,False))

    def AppendContent(self,content: str|Renderable,section:int|str|None = None,newSection:bool = False,overwrite:bool = False,joinStr = ' ') -> int|str|None:
        """Append html content to the specified section. Return the name of the section that was added to."""
        if newSection:
            self.BeginNewSection()
        if not content:
            return None
        if section is None:
            section = self.numberedSections - 1
        
        if type(section) == int and section >= self.numberedSections:
            raise ValueError(f"Cannot write to section {section} since there are only {self.NumberedSections} numbered sections.")

        existingSection = self.section.get(section,"")
        if overwrite or not existingSection:
            self.section[section] = content
            return section
        
        canMerge = type(existingSection) == str and type(content) == str
        if canMerge:
            self.section[section] = " ".join([existingSection,content])
            return section
        elif type(section) == int:
            self.BeginNewSection() # If we can't merge with a numbered section, create a new section
            self.section[self.numberedSections - 1] = content
            return self.numberedSections - 1
        else:
            raise TypeError(f"Cannot merge section type {type(existingSection)} with new content {type(content)}.")
    
    def BeginNewSection(self) -> None:
        "Begin a new numbered section."
        self.section[self.numberedSections] = ""
        self.numberedSections += 1
    
    def Merge(self,pageToAppend: PageDesc) -> PageDesc:
        """Append an entire page to the end of this one.
        Replace our page description with the new one.
        pageToAppend is modified and becomes unusable after this call."""
    
        self.info = pageToAppend.info # Substitute the information of the second page
        
        self.AppendContent(pageToAppend.section[0])
        for sectionNum in range(1,pageToAppend.numberedSections):
            self.BeginNewSection()
            self.AppendContent(pageToAppend.section[sectionNum])
        
        for key,content in pageToAppend.section.items():
            if type(key) != int:
                self.AppendContent(content,key)
        
        return self

    def Augment(self,newData: PageAugmentorType) -> PageDesc:
        """Append content depending on the type of newData as follows:
        str: add this html to the latest section.
        tuple(PageInfo,str): set info = PageInfo and add str to the latest section.
        PageDesc: call self.Merge."""
        if type(newData) == str:
            self.AppendContent(newData)
        elif type(newData) == PageDesc:
            self.Merge(newData)
        else:
            pageInfo,pageBody = newData
            self.info = pageInfo
            self.AppendContent(pageBody)
        
        return self

    def __str__(self) -> str:
        textToJoin = []
        for sect in self.section.values():
            textToJoin.append(Render(sect))
        return " ".join(textToJoin)
    
    def Render(self,**attributes) -> str: # Override Renderable.Render
        textToJoin = []
        for sect in self.section.values():
            textToJoin.append(Render(sect,**attributes))
        return " ".join(textToJoin)
    
    def RenderNumberedSections(self,startSection:int = 0,stopSection:int = 9999999,**attributes) -> str:
        """Return a string of the text of the page."""
        textToJoin = []
        for sectionNumber in range(startSection,min(self.numberedSections,stopSection)):
            textToJoin.append(Render(self.section[sectionNumber]),**attributes)

        return " ".join(textToJoin)

    def RenderWithTemplate(self,templateFile: str) -> str:
        """Render the page by passing it to a pyratemp template."""
        with open(templateFile,encoding='utf-8') as file:
            temp = file.read()

        pageHtml = pyratemp.Template(temp)(page = self)
        
        directoryDepth = len(Path(self.info.file).parents) - 1
        # All relative file paths in the template, menus, and sections are written as if the page is at directory depth 1.
        # If the page will be written somewhere else, change the paths accordingly
        if directoryDepth != 1:
            pageHtml = pageHtml.replace('"../','"' + '../' * directoryDepth)
        return pageHtml
    
    def WriteFile(self,templateFile: str,directory = ".") -> None:
        """Write this page to disk."""
        pageHtml = self.RenderWithTemplate(templateFile)
        filePath = Path(directory).joinpath(Path(self.info.file))

        filePath.parent.mkdir(parents = True,exist_ok = True)
        with open(filePath,'w',encoding='utf-8') as file:
            print(pageHtml,file=file)

    def _PagesFromMenuGenerators(self,menuGenerators: Iterable[PageGeneratorMenuItem],menuSection:str|None = None,**menuStyle) -> Iterator[PageDesc]:
        """Generate a series of PageDesc objects from a list of functions that each describe one item in a menu.
        self: The page we have constructed so far.
        menuGenerators: An iterable (often a list) of generator functions, each of which describes a menu item and its associated pages.
            Each generator function takes a PageDesc object describing the page constructed up to this point.
            Each generator function (optionally) first yields a PageInfo object containing the menu title and link.
            Next it yields a series of PageDesc objects which have been cloned from basePage plus the menu with additional material added.
            An empty generator means that no menu item is generated.
        PagesFromMenuDescriptors is a simpler version of this function."""
        
        menuGenerators = [m(self) for m in menuGenerators] # Initialize the menu iterators
        menuItems = [next(m,None) for m in menuGenerators] # The menu items are the first item in each iterator

        # Generators that yield None aren't associated with a menu item and will be proccessed last.
        generatorsWithNoAssociatedMenuItem = [m for m,item in zip(menuGenerators,menuItems) if not item]
        menuGenerators = [m for m,item in zip(menuGenerators,menuItems) if item]
        menuItems = [item for item in menuItems if item]

        menuSection = self.AppendContent(Menu(menuItems,**menuStyle),section=menuSection)

        for itemNumber,menuIterator in enumerate(menuGenerators):
            self.section[menuSection].menu_highlightedItem = itemNumber
            yield from menuIterator
        
        self.section[menuSection].menu_highlightedItem = None
        for morePages in generatorsWithNoAssociatedMenuItem:
            yield from morePages

    def AddMenuAndYieldPages(self,menuDescriptors: Iterable[PageGeneratorMenuItem | PageDescriptorMenuItem],menuSection:str|None = None,**menuStyle) -> Iterator[PageDesc]:
        """Add a menu described by the first item yielded by each item in menuDescriptors.
        Then generate a series of PageDesc objects from the remaining iterator items in menuDescriptors.
        this: The page we have constructed so far.
        menuIterators: An iterable of iterables, in which each item describes a menu item and its associated pages.
            Each item can be of type PageAugmentationMenuItem or PageDescriptorMenuItem.
            See the description of these types for what they mean."""
        
        def AppendBodyToPage(basePage: PageDesc,menuDescriptor: PageGeneratorMenuItem | PageDescriptorMenuItem) -> Iterable[PageInfo|PageDesc]:
            """A glue function so we can re-use the functionality of PagesFromMenuGenerators."""
            menuDescriptor = iter(menuDescriptor)
            menuItem = next(menuDescriptor,None)
            pageToProcessLater = []
            if menuItem:
                if type(menuItem) == PageInfo:
                    yield menuItem # If it's a menu item and link, yield that
                else:
                    pageToProcessLater = [menuItem]
                    yield None # Otherwise process the page later and return None to continue building the menu
            else:
                return
            
            for pageData in itertools.chain(pageToProcessLater,menuDescriptor): # Then yield PageDesc objects for the remaining pages
                newPage = basePage.Clone()
                newPage.info = menuItem
                newPage.Augment(pageData)
                yield newPage

        menuFunctions = [lambda bp,m=m: AppendBodyToPage(bp,m) for m in menuDescriptors]
            # See https://docs.python.org/3.4/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result 
            # and https://stackoverflow.com/questions/452610/how-do-i-create-a-list-of-lambdas-in-a-list-comprehension-for-loop 
            # for why we need to use m = m.
        yield from self._PagesFromMenuGenerators(menuFunctions,menuSection=menuSection,**menuStyle)


T = TypeVar("T")
def ListWithHeadings(items: list[T],itemRenderer: Callable[[T],tuple(str,str)],headingWrapper:Wrapper = Wrapper('<h3 id="HEADING_ID">','</h3>'),addMenu = True,countItems = True,betweenSections = "<hr>") -> PageDesc:
    """Create a list grouped by headings from items.
    items: The list of items; should be sorted into groups which each have the same heading.
    itemRenderer: Takes an item and returns the tuple heading,htmlBody.
    headingWrapper: Wrap the heading in the body with this html code.
    addMenu: Generate a horizontal menu linking to each section at the top?
    """

    bodyParts = []
    menuItems = []

    itemCount = 0
    prevHeading = None
    for item in items:
        heading,htmlBody = itemRenderer(item)
        if heading != prevHeading:
            if prevHeading is not None and betweenSections:
                bodyParts.append(betweenSections)
            
            if countItems and menuItems: # Append the number of items to the previous menu item
                menuItems[-1] = menuItems[-1]._replace(title=menuItems[-1].title + f" ({itemCount})")

            headingID = Utils.slugify(heading)
            menuItems.append(PageInfo(heading,f"#{headingID}"))
            idWrapper = headingWrapper._replace(prefix=headingWrapper.prefix.replace("HEADING_ID",headingID))
            bodyParts.append(idWrapper.Wrap(heading))

            prevHeading = heading
            itemCount = 0
        bodyParts.append(htmlBody)
        itemCount += 1
    
    page = PageDesc()
    if addMenu:
        if countItems: # Append the number of items to the last menu item
            menuItems[-1] = menuItems[-1]._replace(title=menuItems[-1].title + f" ({itemCount})")
        menu = Menu(menuItems)
        page.AppendContent(menu,section = addMenu if type(addMenu) == str else None)
    
    page.AppendContent("<hr>")
    page.AppendContent("\n".join(bodyParts))

    return page
