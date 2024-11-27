import {configureLinks,frameSearch,setFrameSearch} from './frame.js';
import { loadToggleView } from './toggle-view.js';

const TEXT_DELIMITERS = "][{}<>^";
const METADATA_DELIMITERS = "#&@";
const METADATA_SEPERATOR = "|"
const SPECIAL_SEARCH_CHARS = TEXT_DELIMITERS + METADATA_DELIMITERS + "()";

const HAS_METADATADELIMITERS = new RegExp(`.*[${METADATA_DELIMITERS}]`);

const PALI_DIACRITICS = {
    "a":"ā","i":"ī","u":"ū",
    "d":"ḍ","l":"ḷ","t":"ṭ",
    "n":"ñṇṅ","m":"ṁṃ",
    "'": '‘’"“”'                // A single quote matches all types of quotes
};

let PALI_DIACRITIC_MATCH_ALL = {};
Object.keys(PALI_DIACRITICS).forEach((letter) => {
    PALI_DIACRITIC_MATCH_ALL[letter] = `[${letter}${PALI_DIACRITICS[letter]}]`;
});

const DEBUG = false;

export function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<>=:?.\/\\^$|#\s,]/g, '\\$&');
}

const ESCAPED_HTML_CHARS = regExpEscape(SPECIAL_SEARCH_CHARS);
const MATCH_END_DELIMITERS = new RegExp(`^\\\\[${regExpEscape(TEXT_DELIMITERS)}]+|\\\\[${regExpEscape(TEXT_DELIMITERS)}]+$`,"g");

function capitalizeFirstLetter(val) {
    return String(val).charAt(0).toUpperCase() + String(val).slice(1);
}

export async function loadSearchPage() {
    // Called when a search page is loaded. Load the database, configure the search button,
    // fill the search bar with the URL query string and run a search.

    let searchButtonsFound = 0;
    for (let searchCode in gSearchers) {
        let searchButton = document.getElementById(`search-${searchCode}-button`);
        if (searchButton) {
            searchButton.onclick = () => { searchButtonClick(searchCode); }
            searchButtonsFound += 1;
        }
    }

    if (!searchButtonsFound)
        return;

    let params = frameSearch();
    let query = params.has("q") ? decodeURIComponent(params.get("q")) : "";
    if (!query)
        document.getElementById("search-text").focus();

    // Execute a function when the user presses a key on the keyboard
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/keydown_event
    document.getElementById("search-text").addEventListener("keydown", function(event) {
        // If the user presses the "Enter" key on the keyboard
        if (event.key === "Enter") {
            // Cancel the default action, if needed
            event.preventDefault();
            // Trigger the button element with a click
            document.getElementById("search-x-button").click();
        }
    });

    if (!gDatabase) {
        await fetch('./assets/SearchDatabase.json')
        .then((response) => response.json())
        .then((json) => {
            gDatabase = json; 
            console.log("Loaded search database.");
            for (let code in gSearchers) {
                gSearchers[code].loadItemsFomDatabase(gDatabase)
            }
        });

    }

    searchFromURL();
}

function matchEnclosedText(separators,dontMatchAfterSpace) {
    // Return a regex string that matches the contents between separators.
    // Separators is a 2-character string like '{}'
    // Match all characters excerpt the end character until a space is encountered.
    // If any characters in dontMatchAfterSpace are encountered, match only up until the space.
    // If the end character is encountered, match it.

    let escapedStart = regExpEscape(separators[0]);
    let escapedEnd = regExpEscape(separators[1]);
    
    return [escapedStart,
        `[^${escapedEnd} ]*`,
        "(?:",
            `[^${escapedEnd + regExpEscape(dontMatchAfterSpace)}]*`,
            escapedEnd,
        ")"
    ].join("");
}

function substituteWildcards(regExpString) {
    // Convert the following wildcards to RegExp strings:
    // * Match any or no characters
    // _ Match exactly one character
    // $ Match word boundaries

    // Strip off leading and trailing * and $. The innermost symbol determines whether to match a word boundary.
    let bounded = regExpEscape(regExpString.replace(/^[$*]+/,"").replace(/[$*]+$/,""));
    if (regExpString.match(/^[$*]*/)[0].endsWith("$"))
        bounded = "\\b" + bounded;
    if (regExpString.match(/[$*]*$/)[0].startsWith("$"))
    bounded += "\\b";

    // Replace inner * and _ and $ with appropriate operators.
    return bounded.replaceAll("\\*",`[^${ESCAPED_HTML_CHARS}]*?`).replaceAll("_",`[^${ESCAPED_HTML_CHARS}]`).replaceAll("\\$","\\b");
}

class SearchBase {
    // Abstract search class; matches either nothing or everything depending on negate
    negate = false; // This flag negates the search

    matchesBlob(blob) { // Does this search term match a given blob?
        return negate; 
    }

    matchesItem(item) { // Does this search group match an item?
        if (this.negate) {
            console.log("negate")
        }
        for (const blob of item.blobs) {
            if (this.matchesBlob(blob))
                return !this.negate;
        }
        return this.negate;
    }

    filterItems(items) { // Return an array containing items that match this group
        let result = [];
        for (const item of items) {
            if (this.matchesItem(item))
                result.push(item)
        }
        return result;
    }
}

// A class to parse and match a single term in a search query
class SearchTerm extends SearchBase {
    matcher; // A RegEx created from searchElement
    matchesMetadata = false; // Does this search term apply to metadata?
    boldTextMatcher = ""; // A RegEx string used to highlight this term when displaying results

    constructor(searchElement) {
        // Create a searchTerm from an element found by parseQuery.
        // Also create boldTextMatcher to display the match in bold.
        super();

        this.matchesMetadata = HAS_METADATADELIMITERS.test(searchElement);

        this.negate = searchElement.startsWith("!");
        searchElement = searchElement.replace(/^!/,"");

        if (/^[0-9]+$/.test(searchElement)) // Enclose bare numbers in quotes so 7 does not match 37
            searchElement = '"' + searchElement + '"'

        let qTagMatch = false;
        let aTagMatch = false;
        if (/\]\/\/$/.test(searchElement)) { // Does this query match qTags only?
            searchElement = searchElement.replace(/\/*$/,"");
            qTagMatch = true;
        }
        if (/^\/\/\[/.test(searchElement)) { // Does this query match aTags only?
            searchElement = searchElement.replace(/^\/*/,"");
            aTagMatch = true;
        }
        
        let unwrapped = searchElement;
        switch (searchElement[0]) {
            case '"': // Items in quotes must match on word boundaries.
                unwrapped = "$" + searchElement.replace(/^"+/,'').replace(/"+$/,'') + "$";
                break;
        }

        // Replace inner * and $ with appropriate operators.
        let escaped = substituteWildcards(unwrapped);
        let finalRegEx = escaped;
        if (qTagMatch) {
            finalRegEx += "(?=.*//)";
        }
        if (aTagMatch) {
            finalRegEx += "(?!.*//)";
        }
        console.log("searchElement:",searchElement,finalRegEx);
        this.matcher = new RegExp(finalRegEx);

        if (this.matchesMetadata)
            return; // Don't apply boldface to metadata searches

        // Start processing again to create RegExps for bold text
        let boldItem = escaped;
        console.log("boldItem before:",boldItem);
        boldItem = boldItem.replaceAll(MATCH_END_DELIMITERS,"");

        for (const letter in PALI_DIACRITIC_MATCH_ALL) { // 
            boldItem = boldItem.replaceAll(letter,PALI_DIACRITIC_MATCH_ALL[letter]);
        }

        console.log("boldItem after:",boldItem);
        this.boldTextMatcher = boldItem;
    }

    matchesBlob(blob) { // Does this search term match a given blob?
        if (!this.matchesMetadata) {
            blob = blob.split(METADATA_SEPERATOR)[0];
        }
        return this.matcher.test(blob);
    }
}

class SearchGroup extends SearchBase {
    // An array of searchTerms. Subclasses define different operations (and, or, single item match)
    terms = []; // An array of searchBase items

    constructor() {
        super()
    }

    addTerm(searchString) {
        this.terms.push(new SearchTerm(searchString));
    }

    matchesItem(item) { // Does this search group match an item?
        for (const blob of item.blobs) {
            let allTermsMatch = true;
            for (const term of this.terms) {
                if (!term.matchesBlob(blob))
                    allTermsMatch = false;
            }
            if (allTermsMatch)
                return true;
        }
        return false;
    }
}

class SearchAnd extends SearchGroup {
    // This class matches an item only if all of its terms match the item.
    matchesItem(item) { // Does this search group match an item?
        for (const term of this.terms) {
            if (!term.matchesItem(item))
                return self.negate;
        }
        return !self.negate;
    }
}

class SingleItemSearch extends SearchGroup {
    // This class matches an item only if all of its terms match a single blob within that item.
    // This can be used to match excerpts containing stories with tag [Animal]
    // as distinct from excerpts containing a story annotation and the tag [Animal] applied elsewhere.
    matchesItem(item) { // Does this search group match an item?
        for (const blob of item.blobs) {
            let allTermsMatch = true;
            for (const term of this.terms) {
                if (!term.matchesBlob(blob))
                    allTermsMatch = false;
            }
            if (allTermsMatch)
                return true;
        }
        return false;
    }
}

export class SearchQuery {
    // An array of searchGroups that describes an entire search query
    groups = []; // An array of searchGroups representing the query
    boldTextRegex; // A regular expression matching found texts which should be displayed in bold

    constructor(queryText) {
        // Construct a search query by parsing queryText into search groups containing search terms.
        // Search groups are specified by enclosure within parenthesis.
        // Each excerpt must match all search groups.
        // Search keys within a search group must be matched within the same blob.
        // So (#Read Pasanno}) matches only kind 'Reading' or 'Read by' with teacher ending with Pasanno
        
        queryText = queryText.toLowerCase();
        queryText = queryText.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // https://stackoverflow.com/questions/990904/remove-accents-diacritics-in-a-string-in-javascript
    
        // 1. Build a regex to parse queryText into items
        let parts = [
            matchEnclosedText('""',''),
                // Match text enclosed in quotes
            matchEnclosedText('{}',SPECIAL_SEARCH_CHARS),
                // Match teachers enclosed in braces
            "/*" + matchEnclosedText('[]',SPECIAL_SEARCH_CHARS) + "\\+?/*",
                // Match tags enclosed in brackets
                // Match the forms: [tag]// (qTag only), //[tag] (aTag only), [tag]+ (fTag only)
            "[^ ]+"
                // Match everything else until we encounter a space
        ];
        parts = parts.map((s) => "!?" + s); // Add an optional ! (negation) to these parts
        let partsSearch = "\\s*(" + parts.join("|") + ")"
        console.log(partsSearch);
        partsSearch = new RegExp(partsSearch,"g");
    
        // 2. Create items and groups from the found parts
        for (let match of queryText.matchAll(partsSearch)) {
            let group = new SearchAnd();
            group.addTerm(match[1].trim());
            this.groups.push(group);
        }

        // 3. Construct the regex to match bold text.
        let textMatchItems = [];
        for (const group of this.groups) {
            for (const term of group.terms) {
                if (term.boldTextMatcher)
                    textMatchItems.push(term.boldTextMatcher);
            }
        }
        console.log("textMatchItems",textMatchItems);
        if (textMatchItems.length > 0)
            this.boldTextRegex = new RegExp(`(${textMatchItems.join("|")})(?![^<]*\>)`,"gi");
                // Negative lookahead assertion to avoid modifying html tags.
        else
            this.boldTextRegex = /^a\ba/ // a RegEx that doesn't match anything
        console.log(this.boldTextRegex)
    }

    filterItems(items) { // Return an array containing items that match all groups in this query
        let found = items;
        for (const group of this.groups) {
            found = group.filterItems(found);
        }
        return found;
    }

    displayMatchesInBold(string) { // Add <b> and </b> tags to string to display matches in bold
       return string.replace(this.boldTextRegex,"<b>$&</b>")
    }
}

export function renderExcerpts(excerpts,searcher,sessionHeaders) {
    // Convert a list of excerpts to html code by concatenating their html attributes
    // Display strings in boldTextItems in bold.

    let bits = [];
    let lastSession = null;

    for (const x of excerpts) {
        if (x.session != lastSession) {
            bits.push(sessionHeaders[x.session]);
            lastSession = x.session;
        }
        bits.push(searcher.displayMatchesInBold(x.html));
        bits.push("<hr>");
    }
    return bits.join("\n");
}

function clearSearchResults(message) {
    // Called when the search query is blank
    let messageFrame = document.getElementById('message');
    let instructionsFrame = document.getElementById('instructions');
    let resultsFrame = document.getElementById('results');

    instructionsFrame.style.display = "block";
    resultsFrame.innerHTML = "";

    if (message) {
        messageFrame.innerHTML = message;
        messageFrame.style.display = "block";
    } else
        messageFrame.style.display = "none";
}

class Searcher {
    code; // a one-letter code to identify the search.
    name; // the name of the search, e.g. "Tag"
    plural; // the plural name of the search.
    prefix = "<p>"; // html prefix of each search result.
    suffix = "</p>"; // hmtl suffix of each search result.
    separator = ""; // the html code to separate each displayed search result.
    itemsPerPage = null; // The number of items to display per page.
        // itemsPerPage = null displays all items regardless of length.
        // The base class Searcher displays only one page.
    divClass = "listing"; // Enlcose the search results in a <div> tag with this class.
    items = []; // A list of items of the form:
        // database[n].blobs: an array of search blobs to match
        // database[n].html: the html code to display this item when found
    query = null; // A searchQuery object describing the search
    foundItems = []; // The items we have found.
    
    constructor(code,name) {
        // Configure a search with a given code and name
        this.code = code;
        this.name = name;
        this.plural = this.name + "s";
    }

    loadItemsFomDatabase(database) {
        // Called after SearchDatabase.json is loaded to prepare for searching
        this.items = database.searches[this.code].items;
    }

    search(searchQuery) {
        console.log(this.name,"search.");
        this.query = searchQuery
        this.foundItems = searchQuery.filterItems(this.items);
    }

    renderItems(startItem = 0,endItem = null) {
        // Convert a list of items to html code by concatenating their html attributes
        // Display strings in boldTextItems in bold.

        if (endItem == null)
            endItem = undefined;
        let rendered = [];
        for (let item of this.foundItems.slice(0,endItem)) {
            rendered.push(this.prefix + this.query.displayMatchesInBold(item.html) + this.suffix);
        }

        return rendered.join(this.separator);
    }

    searchHtmlResults() {
        // Return an html string containing the search results.

        return `<div class="${this.divClass}" id="results-${this.code}">\n${this.renderItems(0,this.itemsPerPage)}\n</div>`;
    }

    showResults(message = "") {
        // excerpts are the excerpts to display
        // searcher is the search query object.
        // message is an optional message to display.
        let messageFrame = document.getElementById('message');
        let instructionsFrame = document.getElementById('instructions');
        let resultsFrame = document.getElementById('results');

        if (this.foundItems.length > 0) {
            message += `Found ${this.foundItems.length} ${this.foundItems.length > 1 ? this.plural : this.name}`;
            if (this.itemsPerPage && this.foundItems.length > this.itemsPerPage)
                message += `. Showing only the first ${this.itemsPerPage}:`;
            else
                message += ":"
            instructionsFrame.style.display = "none";

            resultsFrame.innerHTML = this.searchHtmlResults();
            configureLinks(resultsFrame,location.hash.slice(1));
            loadToggleView(resultsFrame);
        } else {
            message += `No ${this.plural} found.`
            instructionsFrame.style.display = "block";
            resultsFrame.innerHTML = "";
        }

        if (message) {
            messageFrame.innerHTML = message;
            messageFrame.style.display = "block";
        } else
            messageFrame.style.display = "none";
    }
}

class TruncatedSearcher extends Searcher {
    // A Searcher that shows only a few results to begin with followed by "Show all...".
    // The whole search can be hidden using a toggle-view object.
    // Displays its own header e.g. "Teachers (2):", so it's intended to be used with MultiSearcher.

    truncateAt; // Truncate the initial view if there are more than this many items

    constructor(code,name,truncateAt) {
        super(code,name);
        this.truncateAt = truncateAt;
    }

    searchHtmlResults() {
        // Append 

        let header = `${capitalizeFirstLetter(this.plural)} (${this.foundItems.length}):`
        let resultsId = `search-results-${this.code}`;

        let firstItems = "";
        let moreItems = "";
        if (this.foundItems.length > this.truncateAt) {
            firstItems = this.renderItems(0,this.truncateAt - 1);
            let moreItemsBody = this.renderItems(this.truncateAt);
            moreItems = ` 
            <a class="toggle-view hide-self" id="${resultsId}-more"><i>Show all ${this.foundItems.length}...</i></a>
            <div class="no-padding" id="${resultsId}-more.b" style="display:none;">
            ${moreItemsBody}
            </div>
            `;
        } else {
            firstItems = this.renderItems();
        }
        
        return ` 
        <div class="${this.divClass}" id="results-${this.code}">
        <h3><a><i class="fa fa-minus-square toggle-view" id="${resultsId}"></i></a> ${header} </h3>
        <div id="${resultsId}.b">
        ${firstItems} 
        ${moreItems}
        </div>
        </div>
        `;
    }
}

export class ExcerptSearcher extends Searcher {
    // Specialised search object for excerpts
    code = "x"; // a one-letter code to identify the search.
    name = "excerpt"; // the name of the search, e.g. "Tag"
    plural = "excerpts"; // the plural name of the search.
    prefix = ""; // html prefix of each search result.
    suffix = ""; // hmtl suffix of each search result.
    separator = "<hr>"; // the html code to separate each displayed search result.
    itemsPerPage = 100; // The number of items to display per page.
        // itemsPerPage = 0 displays all items regardless of length.
        // The base class Searcher displays only one page.
    divClass = "main"; // Enlcose the search results in a <div> tag with this class.
    sessionHeader = {};   // Contains rendered headers for each session.

    loadItemsFomDatabase(database) {
        // Called after SearchDatabase.json is loaded to prepare for searching
        super.loadItemsFomDatabase(database);
        this.sessionHeader = database.searches[this.code].sessionHeader;
    }

    renderItems(startItem = 0,endItem = null) {
        // Convert a list of excerpts to html code by concatenating their html attributes and
        // inserting session headers where needed.
        // Display strings in boldTextItems in bold.

        if (endItem == null)
            endItem = undefined;

        let bits = [];
        let lastSession = null;

        for (const x of this.foundItems.slice(0,endItem)) {
            if (x.session != lastSession) {
                bits.push(this.sessionHeader[x.session]);
                lastSession = x.session;
            }
            bits.push(this.query.displayMatchesInBold(x.html));
            bits.push(this.separator);
        }
        return bits.join("\n");
    }
}

function searchFromURL() {
    // Find excerpts matching the search query from the page URL.
    if (!gDatabase) {
        console.log("Error: database not loaded.");
        return;
    }

    let params = frameSearch();
    let query = params.has("q") ? decodeURIComponent(params.get("q")) : "";
    console.log("Called searchFromURL. Query:",query);
    frame.querySelector('#search-text').value = query;

    if (!query.trim()) {
        clearSearchResults();
        return;
    }

    let searchGroups = new SearchQuery(query);
    console.log(searchGroups);

    let searchKind = params.has("search") ? decodeURIComponent(params.get("search")) : "x";
    gSearchers[searchKind].search(searchGroups);
    gSearchers[searchKind].showResults();
}

function searchButtonClick(searchKind) {
    // Read the search bar text, push the updated URL to history, and run a search.
    let query = frame.querySelector('#search-text').value;
    console.log("Called runFromURLSearch. Query:",query,"Kind:",searchKind);

    let search = new URLSearchParams({q : encodeURIComponent(query),search : searchKind});
    history.pushState({},"",location.href); // First push a new history frame
    setFrameSearch(search); // Then replace the history with the search query

    searchFromURL();
}

let gDatabase = null; // The global database, loaded from assets/SearchDatabase.json
let gSearchers = { // A dictionary of searchers by item code
    "x": new ExcerptSearcher(),
    "g": new TruncatedSearcher("g","tag",5),
    "t": new Searcher("t","teacher"),
};