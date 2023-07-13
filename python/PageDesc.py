"""Implements the PageDesc object and related functionality to """

from __future__ import annotations

from typing import NamedTuple
import pyratemp
import os

# The most basic information about a webpage
class PageInfo(NamedTuple):
    title: str|None = None
    file: str|None = None

class Menu:
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
            menuLinks[self.highlightedItem] = separator[0] + menuLinks[self.highlightedItem] + separator[1]
        
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
        
        directoryDepth = len(self.info.file.split("/")) - 1
        if directoryDepth != 1:
            pageHtml = pageHtml.replace('"../','"' + '../' * directoryDepth)
        return pageHtml
    
    def WriteFile(self,templateFile: str,directory = ".") -> None:
        """Write this page to disk."""
        pageHtml = self.RenderWithTemplate(templateFile)
        filePath = os.path.join(directory,self.info.file)

        with open(filePath,'w',encoding='utf-8') as file:
            print(pageHtml,file=file)

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

page.WriteFile("prototype/templates/Global.html","prototype")