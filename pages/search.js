import {configureLinks,frameSearch,setFrameSearch} from './frame.js';

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

let gDatabase = null; // The global database, loaded from assets/SearchDatabase.json
let gSearchers = {}; // A dictionary of searchers by item code

export function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<>=:?.\/\\^$|#\s,]/g, '\\$&');
}

const ESCAPED_HTML_CHARS = regExpEscape(SPECIAL_SEARCH_CHARS);
const MATCH_END_DELIMITERS = new RegExp(`^\\\\[${regExpEscape(TEXT_DELIMITERS)}]+|\\\\[${regExpEscape(TEXT_DELIMITERS)}]+$`,"g");

export async function loadSearchPage() {
    // Called when a search page is loaded. Load the database, configure the search button,
    // fill the search bar with the URL query string and run a search.

    for (let kind of "xg") {
        let searchButton = document.getElementById(`search-${kind}-button`);
        if (!searchButton)
            return; // Exit if it's a non-search page.
        searchButton.onclick = () => { searchButtonClick(kind); }
    }

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
            for (let code in gDatabase["searches"]) {
                if (code == "x")
                    gSearchers[code] = new excerptSearcher(gDatabase.searches[code]);
                else
                    gSearchers[code] = new searcher(gDatabase.searches[code]);
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

// A class to parse and match a single term in a search query
class searchTerm {
    matcher; // A RegEx created from searchElement
    negate = false; // Return true when matcher fails to match?
    matchesMetadata = false; // Does this search term apply to metadata?
    boldTextMatcher = ""; // A RegEx string used to highlight this term when displaying results

    constructor(searchElement) {
        // Create a searchTerm from an element found by parseQuery.
        // Also create boldTextMatcher to display the match in bold.
        this.matchesMetadata = HAS_METADATADELIMITERS.test(searchElement);

        if (/^[0-9]+$/.test(searchElement)) // Enclose bare numbers in quotes so 7 does not match 37
            searchElement = '"' + searchElement + '"'

        let unwrapped = searchElement;
        switch (searchElement[0]) {
            case '"': // Items in quotes must match on word boundaries.
                unwrapped = "$" + searchElement.replace(/^"+/,'').replace(/"+$/,'') + "$";
                break;
        }

        // Replace inner * and $ with appropriate operators.
        let escaped = substituteWildcards(unwrapped);
        console.log("searchElement:",searchElement,escaped);
        this.matcher = new RegExp(escaped);

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
        if (!this.matchesMetadata)
            blob = blob.split(METADATA_SEPERATOR)[0];
        return this.matcher.test(blob);
    }
}

class searchGroup {
    // An array of searchTerms. All searchTerms must match the same blob in order for an item to match.
    terms = []; // An array of searchTerms in the group
    negate = false; // Return true when searchGroup fails to match?

    constructor() {
        
    }

    addTerm(searchString) {
        this.terms.push(new searchTerm(searchString));
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

    filterItems(items) { // Return an array containing items that match this group
        let result = [];
        for (const item of items) {
            if (this.matchesItem(item))
                result.push(item)
        }
        return result;
    }
}

export class searchQuery {
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
        let partsSearch = "\\s*(" + [
            matchEnclosedText('""',''),
            matchEnclosedText('{}',SPECIAL_SEARCH_CHARS),
            matchEnclosedText('[]',SPECIAL_SEARCH_CHARS),
            "[^ ]+"
        ].join("|") + ")";
        console.log(partsSearch);
        partsSearch = new RegExp(partsSearch,"g");
    
        // 2. Create items and groups from the found parts
        for (let match of queryText.matchAll(partsSearch)) {
            let group = new searchGroup();
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

class searcher {
    code; // a one-letter code to identify the search.
    name; // the name of the search, e.g. "Tag"
    plural; // the plural name of the search.
    prefix; // html prefix of each search result.
    suffix; // hmtl suffix of each search result.
    separator; // the html code to separate each displayed search result.
    itemsPerPage; // The number of items to display per page. 
        // For the base class searcher, this is the number of items to display before the user clicks "Show all"
    showAtFirst; // The number of items to display at first in a multi-search
    divClass; // Enlcose the search results in a <div> tag with this class.
    items; // A list of items of the form:
        // database[n].blobs: an array of search blobs to match
        // database[n].html: the html code to display this item when found
    query = null; // A searchQuery object describing the search
    foundItems = []; // The items we have found.
    
    constructor(databaseItem) {
        // Build this search from an entry in the search database
        for (let element in databaseItem) {
            this[element] = databaseItem[element];
        }
    }

    search(searchQuery) {
        console.log(this.name,"search.");
        this.query = searchQuery
        this.foundItems = searchQuery.filterItems(this.items);
    }

    renderItems(startItem = 0,endItem = null) {
        // Return a string of the found items.

        if (endItem == null)
            endItem = undefined;
        let rendered = [];
        for (let item of this.foundItems.slice(0,endItem)) {
            rendered.push(this.prefix + this.query.displayMatchesInBold(item.html) + this.suffix);
        }

        return rendered.join(this.separator);
    }

    singleSearchHtmlResults() {
        // Return an html string containing the search results when displaying only this search.

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

            resultsFrame.innerHTML = this.singleSearchHtmlResults();
            configureLinks(resultsFrame,location.hash.slice(1));
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

export class excerptSearcher extends searcher {
    // Specialised search object for excerpts
    // sessionHeader;   // Contains rendered headers for each session.
                        // Its value is set in the base class constructor function.
                        // If we prototype the variable here, that overwrites the value set by the base class constructor.
                    
    renderItems(startItem = 0,endItem = null) {
        // Convert a list of excerpts to html code by concatenating their html attributes
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

    let searchGroups = new searchQuery(query);
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

    /* let newURL = new URL(location.href);
    newURL.search = `?q=${encodeURIComponent(query)}&search=${searchKind}`
    history.pushState({}, "",newURL.href); */

    searchFromURL();
}