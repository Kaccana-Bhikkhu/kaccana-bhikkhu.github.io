"""Implements the PageDesc object and related functionality to """

from __future__ import annotations

from typing import NamedTuple
import pyratemp
import os
from collections.abc import Iterator, Iterable, Callable
import copy

# The most basic information about a webpage
class PageInfo(NamedTuple):
    title: str|None = None
    file: str|None = None

class Menu:
    items: list[PageInfo]
    highlightedItem:int|None
    separator:int|str
    highlightTags:tuple(str,str)
    renderAfterSection: int|None

    def __init__(self,items: list[PageInfo],highlightedItem:int|None = None,separator:int|str = 6,highlightTags:tuple(str,str) = ("<b>","</b>")) -> None:
        """items: a list of PageInfo objects containing the menu text (title) and html link (file) of each menu item.
        highlightedItem: which (if any) of the menu items is highlighted.
        separator: html code between each menu item; defaults to 6 spaces.
        highlightTags: the tags to apply to the highlighted menu item."""
        self.items = items
        self.highlightedItem = highlightedItem
        self.separator = separator
        self.highlightTags = highlightTags
        self.renderAfterSection = None # The menu appears after this section
    
    def Render(self,separator:int|str|None = None,highlightTags:tuple(str,str)|None = None) -> str:
        """Return an html string corresponding to the rendered menu."""
        if separator is None:
            separator = self.separator
        if type(separator) == int:
            separator = " " + (separator - 1) * "&nbsp"
        if highlightTags is None:
            highlightTags = self.highlightTags
        
        menuLinks = [f'<a href = "{i.file}">{i.title}</a>' for i in self.items]
        if self.highlightedItem is not None:
            menuLinks[self.highlightedItem] = highlightTags[0] + menuLinks[self.highlightedItem] + highlightTags[1]

        print(self.highlightedItem, menuLinks[self.highlightedItem])
        return separator.join(menuLinks)

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
        clone = copy.copy(self)
        clone.section = copy.copy(self.section)
        clone.menus = copy.deepcopy(self.menus) # menus are mutable objects, so deep copy this list
        return clone

    def AddContent(self,content: str,section:int|str|None = None) -> None:
        """Add html content to the specified section."""
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
        
        directoryDepth = 1
        # All relative file paths in the template and menus are written as if the page is at directory depth 1.
        # If the page will be written somewhere else, change the paths accordingly
        if directoryDepth != 1:
            pageHtml = pageHtml.replace('"../','"' + '../' * directoryDepth)
        return pageHtml
    
    def WriteFile(self,templateFile: str,directory = ".") -> None:
        """Write this page to disk."""
        pageHtml = self.RenderWithTemplate(templateFile)
        filePath = os.path.join(directory,self.info.file)

        os.makedirs(directory,exist_ok=True)
        with open(filePath,'w',encoding='utf-8') as file:
            print(pageHtml,file=file)

def PagesFromMenuIterators(basePage: PageDesc,menuIterators: Iterable[Callable[[PageDesc],Iterable[PageInfo|PageDesc]]]) -> Iterator[PageDesc]:
    """Generate a series of PageDesc objects from a list of functions that each describe one item in a menu.
    basePage: The page we have constructed so far.
    menuIterators: An iterable (often a list) of generator functions, each of which describes a menu item and its associated pages.
        Each generator function takes a PageDesc object describing the page constructed up to this point.
        Each generator function first returns a PageInfo object containing the menu title and link.
        Next it returns a series of PageDesc objects which have been cloned from basePage plus the menu with additional material added.
        An empty generator means that no menu item is generated.
    PagesFromMenuDescriptors is a simpler version of this function."""
    
    menuIterators = [m(basePage) for m in menuIterators] # Initialize the menu iterators
    menuItems = [next(m,None) for m in menuIterators] # The menu items are the first item in each iterator
    menuIterators = [m for m,item in zip(menuIterators,menuItems,strict=True) if item] # Remove menu iterators if the menu doesn't exist
    menuItems = [m for m in menuItems if m] # Same for menu items

    print(menuItems)
    basePage.AddMenu(Menu(menuItems))

    for itemNumber,menuIterator in enumerate(menuIterators):
        basePage.menus[-1].highlightedItem = itemNumber
        for page in menuIterator:

            yield page

def PagesFromMenuDescriptors(basePage: PageDesc,menuDescriptors: Iterable[Iterable[PageInfo|tuple(PageInfo,str)]]) -> Iterator[PageDesc]:
    """Generate a series of PageDesc objects from a list of iterables that each describe one item in a menu.
    basePage: The page we have constructed so far.
    menuIterators: An iterable of iterables (usually list of a generator functions), in which each item describes a menu item and its associated pages.
        The first item in each iterable is a PageInfo object containing the menu item and link.
        Next it returns a series of PageDesc objects which have been cloned from basePage plus the menu with additional material added.
        Each subsequent item a tuple (pageInfo,htmlBody) describing each page associated with this menu item.
        An empty generator means that no menu item is generated."""
    
    def AppendBodyToPage(basePage: PageDesc,menuDescriptor: Iterable[PageInfo|tuple(PageInfo,str)]) -> Iterable[PageInfo|PageDesc]:
        """A glue function so we can re-use the functionality of PagesFromMenuIterators."""
        menuDescriptor = iter(menuDescriptor)
        value = next(menuDescriptor,None)
        if value:
            yield value # First yield the menu item name and link
        else:
            return
        
        for pageInfo,pageBody in menuDescriptor: # Then yield PageDesc objects for the remaining pages
            newPage = basePage.Clone()
            newPage.info = pageInfo
            newPage.AddContent(pageBody)
            yield newPage

    for n,m in enumerate(menuDescriptors):
        print(n,m)
    menuFunctions = [lambda bp,m=m: AppendBodyToPage(bp,m) for m in menuDescriptors]
        # See https://docs.python.org/3.4/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result 
        # and https://stackoverflow.com/questions/452610/how-do-i-create-a-list-of-lambdas-in-a-list-comprehension-for-loop 
        # for why we need to use m = m.
    yield from PagesFromMenuIterators(basePage,menuFunctions)



page = PageDesc()
page.AddContent("Title in body")

mainMenu = []
mainMenu.append([PageInfo("Home","home.html"),(PageInfo("Here is home","home.html"),"Text of home page.")])
mainMenu.append([PageInfo("Tag/subtag hierarchy","tags.html"),(PageInfo("Tags","tags.html"),"Some tags go here.")])
mainMenu.append([])
mainMenu.append([PageInfo("Events","events.html"),(PageInfo("Events","events.html"),"Some events go here.")])

for newPage in PagesFromMenuDescriptors(page,mainMenu):
    newPage.WriteFile("prototype/templates/Global.html","prototype/testDir")


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