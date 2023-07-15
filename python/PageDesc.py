"""Implements the PageDesc object and related functionality to """

from __future__ import annotations

from typing import NamedTuple
import pyratemp
import os
from pathlib import Path
from collections.abc import Iterator, Iterable, Callable
import copy

# The most basic information about a webpage
class PageInfo(NamedTuple):
    title: str|None = None
    file: str|None = None
    titleIB: str|None = None

    @property
    def titleInBody(self):
        if self.titleIB is not None:
            return self.titleIB
        else:
            return self.title

class Menu:
    items: list[PageInfo]
    highlightedItem:int|None
    prefix:str
    separator:int|str
    suffix:str
    highlightTags:tuple(str,str)
    renderAfterSection: int|None

    def __init__(self,items: list[PageInfo],highlightedItem:int|None = None,separator:int|str = 6,highlightTags:tuple[str,str] = ("<b>","</b>"),prefix:str = "",suffix:str = "") -> None:
        """items: a list of PageInfo objects containing the menu text (title) and html link (file) of each menu item.
        highlightedItem: which (if any) of the menu items is highlighted.
        separator: html code between each menu item; defaults to 6 spaces.
        highlightTags: the tags to apply to the highlighted menu item."""
        self.items = items
        self.highlightedItem = highlightedItem
        self.prefix = prefix
        self.separator = separator
        self.suffix = suffix
        self.highlightTags = highlightTags
        self.renderAfterSection = None # The menu appears after this section
    
    def Render(self,separator:int|str|None = None,highlightTags:tuple(str,str)|None = None,prefix:str|None = None,suffix:str|None = None) -> str:
        """Return an html string corresponding to the rendered menu."""
        if separator is None:
            separator = self.separator
        if type(separator) == int:
            separator = " " + (separator - 1) * "&nbsp"
        if highlightTags is None:
            highlightTags = self.highlightTags
        if prefix is None:
            prefix = self.prefix
        if suffix is None:
            suffix = self.suffix
        
        def RelativeLink(link: str) -> bool:
            return not ("://" in link or link.startswith("#"))

        # Render relative links as if the file is at directory depth 1. PageDesc.RenderWithTemplate will later produce the correct
        menuLinks = [f'<a href = "{"../" + i.file if RelativeLink(i.file) else i.file}">{i.title}</a>' for i in self.items]

        if self.highlightedItem is not None:
            menuLinks[self.highlightedItem] = highlightTags[0] + menuLinks[self.highlightedItem] + highlightTags[1]

        rawMenu = separator.join(menuLinks)
        if prefix:
            items = [prefix,rawMenu]
        else:
            items = [rawMenu]
        if suffix:
            items.append(suffix)
        return " ".join(items)

class PageDesc: # Define a dummy PageDesc class for the type definitions below
    pass

PageAugmentationMenuItem = Callable[[PageDesc],Iterable[PageInfo|PageDesc]]
"""Type defintion for a generator function that returns an iterator of pages associated with a menu item.
See PagesFromMenuGenerators for a full description."""

PageDescriptorMenuItem = Iterable[PageInfo | str | tuple[PageInfo,str] | PageDesc]
"""An iterable that describes a menu item and pages associate with it.
It first yields a PageInfo object containing the menu title and link.
For each page associated with the menu it then yields one of the following:
    str: html of the page following the menu. The page title and file name are those associated with the menu item.
        Note: if the iterable returns more than one str value, the pages will overwrite each other
    tuple(PageInfo,str): PageInfo describes the page title and file name; str is the html content of the page following the menu
    PageDesc: The description of the page after the menu, which will be merged with the base page and menu.
"""

class PageDesc:
    """A PageDesc object is used gradually build a complete description of the content of a page.
    When complete, the object will be passed to a pyratemp template to generate a page and write it to disk."""
    info: PageInfo
    numberedSections:int
    section:dict[int|str,str]
    menus: list[Menu]

    def __init__(self,info: PageInfo = PageInfo()) -> None:
        self.info = info # Basic information about the page
        self.numberedSections = 1
        self.section = {0:""} # A dict describing the content of the page. Sequential sections are given by integer keys, non-sequential sections by string keys.
        self.menus = [] # A list of menus on the page
    
    def Clone(self) -> PageDesc:
        """Clone this page so we can add more material to the new page without affecting the original."""
        return copy.deepcopy(self)

    def AddContent(self,content: str,section:int|str|None = None) -> None:
        """Add html content to the specified section."""
        if not content:
            return
        if section is None:
            section = self.numberedSections - 1
        existingSection = self.section.get(section,"")
        if existingSection:
            self.section[section] = " ".join([existingSection,content])
        else:
            self.section[section] = content
    
    def BeginNewSection(self) -> None:
        "Begin a new numbered section."
        self.section[self.numberedSections] = ""
        self.numberedSections += 1
    
    def AddMenu(self,menu: Menu) -> None:
        "Add a menu to the page."
        menu.renderAfterSection = self.numberedSections - 1
        self.menus.append(menu)
        self.BeginNewSection()
    
    def Merge(self,pageToAppend: PageDesc) -> None:
        """Append an entire page to the end of this one.
        Replace our page description with the new one.
        pageToAppend is modified and becomes unusable after this call."""
    
        self.info = pageToAppend.info # Substitute the information of the second page
        
        for menu in pageToAppend.menus:
            menu.renderAfterSection += self.numberedSections - 1
        self.menus += pageToAppend.menus
        
        self.AddContent(pageToAppend.section[0])
        for sectionNum in range(1,pageToAppend.numberedSections):
            self.BeginNewSection()
            self.AddContent(pageToAppend.section[sectionNum])
        
        for key,content in pageToAppend.section.items():
            if type(key) != int:
                self.AddContent(content,key)
        
    
    def PageText(self,startingWithSection: int = 0) -> str:
        """Return a string of the text of the page."""
        textToJoin = []
        for sectionNumber in range(startingWithSection,self.numberedSections):
            textToJoin.append(self.section[sectionNumber])
            renderedMenus = [m.Render() for m in self.menus if m.renderAfterSection == sectionNumber]
            textToJoin += renderedMenus
        
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

    def _PagesFromMenuGenerators(self,menuGenerators: Iterable[PageAugmentationMenuItem],**menuStyle) -> Iterator[PageDesc]:
        """Generate a series of PageDesc objects from a list of functions that each describe one item in a menu.
        self: The page we have constructed so far.
        menuGenerators: An iterable (often a list) of generator functions, each of which describes a menu item and its associated pages.
            Each generator function takes a PageDesc object describing the page constructed up to this point.
            Each generator function first yields a PageInfo object containing the menu title and link.
            Next it yields a series of PageDesc objects which have been cloned from basePage plus the menu with additional material added.
            An empty generator means that no menu item is generated.
        PagesFromMenuDescriptors is a simpler version of this function."""
        
        menuGenerators = [m(self) for m in menuGenerators] # Initialize the menu iterators
        menuItems = [next(m,None) for m in menuGenerators] # The menu items are the first item in each iterator
        menuGenerators = [m for m,item in zip(menuGenerators,menuItems,strict=True) if item] # Remove menu iterators if the menu doesn't exist
        menuItems = [m for m in menuItems if m] # Same for menu items

        self.AddMenu(Menu(menuItems,**menuStyle))

        for itemNumber,menuIterator in enumerate(menuGenerators):
            self.menus[-1].highlightedItem = itemNumber
            for page in menuIterator:

                yield page

    def AddMenuAndYieldPages(self,menuDescriptors: Iterable[PageAugmentationMenuItem | PageDescriptorMenuItem],**menuStyle) -> Iterator[PageDesc]:
        """Add a menu described by the first item yielded by each item in menuDescriptors.
        Then generate a series of PageDesc objects from the remaining iterator items in menuDescriptors.
        this: The page we have constructed so far.
        menuIterators: An iterable of iterables, in which each item describes a menu item and its associated pages.
            Each item can be of type PageAugmentationMenuItem or PageDescriptorMenuItem.
            See the description of these types for what they mean."""
        
        def AppendBodyToPage(basePage: PageDesc,menuDescriptor: PageAugmentationMenuItem | PageDescriptorMenuItem) -> Iterable[PageInfo|PageDesc]:
            """A glue function so we can re-use the functionality of PagesFromMenuGenerators."""
            menuDescriptor = iter(menuDescriptor)
            menuItem = next(menuDescriptor,None)
            if menuItem:
                yield menuItem # First yield the menu item name and link
            else:
                return
            
            for pageData in menuDescriptor: # Then yield PageDesc objects for the remaining pages
                newPage = basePage.Clone()
                if type(pageData) == str: # Simplest case: the page corresponds exactly to the menu item
                    newPage.info = menuItem
                    newPage.AddContent(pageData)
                elif type(pageData) == PageDesc:
                    newPage.Merge(pageData)
                else:
                    pageInfo,pageBody = pageData
                    newPage.info = pageInfo
                    newPage.AddContent(pageBody)
                yield newPage

        menuFunctions = [lambda bp,m=m: AppendBodyToPage(bp,m) for m in menuDescriptors]
            # See https://docs.python.org/3.4/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result 
            # and https://stackoverflow.com/questions/452610/how-do-i-create-a-list-of-lambdas-in-a-list-comprehension-for-loop 
            # for why we need to use m = m.
        yield from self._PagesFromMenuGenerators(menuFunctions,**menuStyle)

"""page = PageDesc()
page.AddContent("This shouldn't show.")

mainMenu = []
mainMenu.append([PageInfo("Home","home.html","Title in Home Page"),"Text of home page."])
mainMenu.append([PageInfo("Tag/subtag hierarchy","tags.html"),(PageInfo("Tags","tags.html"),"Some tags go here.")])
mainMenu.append([])
mainMenu.append([PageInfo("Events","events.html"),(PageInfo("Events","events.html"),"Some events go here.")])

for newPage in PagesFromMenuDescriptors(page,mainMenu):
    newPage.WriteFile("prototype/templates/Global.html","prototype/testDir")
"""

"""
mainMenu = []
mainMenu.append(PageInfo("Homepage","../index.html"))
mainMenu.append(PageInfo("Tag/subtag hierarchy","../indexes/AllTags.html"))
mainMenu.append(PageInfo("Most common tags","../indexes/SortedTags.html"))
mainMenu.append(PageInfo("Events","../indexes/AllEvents.html"))
mainMenu.append(PageInfo("Teachers","../indexes/AllTeachers.html"))
mainMenu.append(PageInfo("All excerpts","../indexes/AllExcerpts.html"))

page = PageDesc()
page.info = PageInfo("Home Page","homepage.html")
#page.AddContent("Title in body")
page.AddMenu(Menu(mainMenu))
page.AddContent("<p>This is the text of a new page.</p>")

page.WriteFile("prototype/templates/Global.html","prototype")"""