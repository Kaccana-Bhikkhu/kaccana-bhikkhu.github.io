import {configureLinks} from './frame.js';

const MAX_RESULTS = 100;
const SPECIAL_SEARCH_CHARS = "][{}()#^@&";
const PALI_DIACRITICS = {
    "a":"ā","i":"ī","u":"ū",
    "d":"ḍ","l":"ḷ","t":"ṭ",
    "n":"ñṇṅ","m":"ṁṃ"
};

const DEBUG = false;

let database = null;

export function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');
}

const ESCAPED_SPECIAL_CHARS = regExpEscape(SPECIAL_SEARCH_CHARS);
const ESCAPED_HTML_CHARS = regExpEscape(SPECIAL_SEARCH_CHARS + "<>")

export async function loadSearchPage() {
    // Called when a search page is loaded. Load the database, configure the search button,
    // fill the search bar with the URL query string and run a search.

    let searchButton = document.getElementById("search-button");
    if (!searchButton)
        return; // Exit if it's a non-search page.
    searchButton.onclick = () => { searchButtonClick(); }

    // Execute a function when the user presses a key on the keyboard
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/keydown_event
    document.getElementById("search-text").addEventListener("keydown", function(event) {
        // If the user presses the "Enter" key on the keyboard
        if (event.key === "Enter") {
            // Cancel the default action, if needed
            event.preventDefault();
            // Trigger the button element with a click
            document.getElementById("search-button").click();
        }
    });

    if (!database) {
        await fetch('./assets/SearchDatabase.json')
        .then((response) => response.json())
        .then((json) => {database = json; console.log("Loaded search database.")});
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
    boldTextMatcher; // A RegEx used to highlight this term when displaying results

    constructor(seachElement) {
        // Create a searchTerm from an element found by parseQuery.
        // Also create boldTextMatcher to display the match in bold.
        let unwrapped = seachElement;
        switch (seachElement[0]) {
            case '"': // Items in quotes must match on word boundaries.
                unwrapped = "$" + seachElement.replace(/^"+/,'').replace(/"+$/,'') + "$";
                break;
        }

        // Replace inner * and $ with appropriate operators.
        let escaped = substituteWildcards(unwrapped);
        console.log("searchElement:",seachElement,escaped);
        this.matcher = new RegExp(escaped,"g");

        // Start processing again to create RegExps for bold text
        let boldItem = escaped;
        console.log("boldItem before:",boldItem);
        if (seachElement.match(/^\[|\]$/g)) { // are we matching a tag?
            boldItem = substituteWildcards(seachElement.replace(/^\[+/,'').replace(/\]+$/,''));
                // remove enclosing [ ]
        } else if (seachElement.match(/^\{|\}$/g)) { // are we matching a teacher?
            boldItem = substituteWildcards(seachElement.replace(/^\{+/,'').replace(/\}+$/,''));
                // remove enclosing { }
        }
        console.log("boldItem after:",boldItem);
        this.boldTextMatcher = new RegExp(boldItem,"g");
        gBoldTextItems.push(boldItem);
    }

    matchesBlob(blob) { // Does this search term match a given blob?
        return blob.search(this.matcher) != -1;
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
    groups = [];

    constructor(queryText) {
        // Construct a search query by parsing queryText into search groups containing search terms.
        // Search groups are specified by enclosure within parenthesis.
        // Each excerpt must match all search groups.
        // Search keys within a search group must be matched within the same blob.
        // So (#Read Pasanno}) matches only kind 'Reading' or 'Read by' with teacher ending with Pasanno
        
        queryText = queryText.toLowerCase();
        queryText = queryText.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // https://stackoverflow.com/questions/990904/remove-accents-diacritics-in-a-string-in-javascript
    
        let partsSearch = "\\s*(" + [
            matchEnclosedText('""',''),
            matchEnclosedText('{}',SPECIAL_SEARCH_CHARS),
            matchEnclosedText('[]',SPECIAL_SEARCH_CHARS),
            "[^ ]+"
        ].join("|") + ")";
        console.log(partsSearch);
        partsSearch = new RegExp(partsSearch,"g");
    
        gBoldTextItems = [];
        for (let match of queryText.matchAll(partsSearch)) {
            let group = new searchGroup();
            group.addTerm(match[1].trim());
            this.groups.push(group);
        }
    }

    filterItems(items) { // Return an array containing items that match all groups in this query
        let found = items;
        for (const group of this.groups) {
            found = group.filterItems(found);
        }
        return found;
    }
}

let gBoldTextItems = []; // A list of RegExps representing search matches that should be displayed in bold text.

export function parseQuery(query) {
    // Given a query string, parse it into searchGroups.
    // Return an array representing searchGroups specified by enclosure within parenthesis.
    // Each excerpt must match all search groups.
    // Search keys within a search group must be matched within the same blob.
    // So (#Read Pasanno}) matches only kind 'Reading' or 'Read by' with teacher ending with Pasanno

    query = query.toLowerCase();
    query = query.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // https://stackoverflow.com/questions/990904/remove-accents-diacritics-in-a-string-in-javascript

    let partsSearch = "\\s*(" + [
        matchEnclosedText('""',''),
        matchEnclosedText('{}',SPECIAL_SEARCH_CHARS),
        matchEnclosedText('[]',SPECIAL_SEARCH_CHARS),
        "[^ ]+"
    ].join("|") + ")";
    console.log(partsSearch);
    partsSearch = new RegExp(partsSearch,"g");

    gBoldTextItems = [];
    let returnValue = [];
    for (let match of query.matchAll(partsSearch)) {
        let group = new searchGroup();
        group.addTerm(match[1].trim());
        returnValue.push(group);
    }
    return returnValue;
}

export function renderExcerpts(excerpts,boldTextItems,sessionHeaders) {
    // Convert a list of excerpts to html code by concatenating their html attributes
    // Display strings in boldTextItems in bold.

    let x = null;
    let bits = [];
    let lastSession = null;

    console.log("boldTextItems",boldTextItems)
    let matchDiacritics = {}
    Object.keys(PALI_DIACRITICS).forEach((letter) => {
        matchDiacritics[letter] = `[${letter}${PALI_DIACRITICS[letter]}]`;
    });
    let textMatchItems = boldTextItems.map((regex) => {
        let letter = null;
        for (letter in matchDiacritics) {
            regex = regex.replaceAll(letter,matchDiacritics[letter]);
        }
        return regex;
    });
    console.log("textMatchItems:",textMatchItems);
    let boldTextRegex = new RegExp(`(${textMatchItems.join("|")})(?![^<]*\>)`,"gi");
        // Negative lookahead assertion to avoid modifying html tags.
    for (x of excerpts) {
        if (x.session != lastSession) {
            bits.push(sessionHeaders[x.session]);
            lastSession = x.session;
        }
        bits.push(x.html.replace(boldTextRegex,"<b>$&</b>"));
        bits.push("<hr>");
    }
    return bits.join("\n");
}

function showSearchResults(excerpts = [],boldTextItems = [],message = "") {
    // excerpts are the excerpts to display
    // boldTextItems is a list of strings to display in bold.
    // message is an optional message to display.
    let messageFrame = document.getElementById('message');
    let instructionsFrame = document.getElementById('instructions');
    let resultsFrame = document.getElementById('results');

    if (excerpts.length > 0) {
        //let resultParts = [query,
        //    "|" + regexList.join("|") + "|",
        //    `Found ${found.length} excerpts` + ((found.length > 100) ? `. Showing only the first ${MAX_RESULTS}` : "") + ":",
        //    renderExcerpts(found.slice(0,MAX_RESULTS),regexList)];
        
        message += `Found ${excerpts.length} excerpts` + ((excerpts.length > 100) ? `. Showing only the first ${MAX_RESULTS}` : "") + ":";
        instructionsFrame.style.display = "none";

        resultsFrame.innerHTML = renderExcerpts(excerpts.slice(0,MAX_RESULTS),boldTextItems,database.sessionHeader);
        configureLinks(resultsFrame,location.hash.slice(1));
    } else {
        message += "No excerpts found."
        instructionsFrame.style.display = "block";
        resultsFrame.innerHTML = "";
    }

    if (message) {
        messageFrame.innerHTML = message;
        messageFrame.style.display = "block";
    } else
        messageFrame.style.display = "none";
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

function searchFromURL() {
    // Find excerpts matching the search query from the page URL.
    if (!database) {
        console.log("Error: database not loaded.");
        return;
    }

    let params = new URLSearchParams(location.search.slice(1));
    let query = params.has("q") ? decodeURIComponent(params.get("q")) : "";
    console.log("Called searchFromURL. Query:",query);
    frame.querySelector('#search-text').value = query;

    if (!query.trim()) {
        clearSearchResults();
        return;
    }

    let searchGroups = new searchQuery(query);
    console.log(searchGroups);

    let found = searchGroups.filterItems(database.excerpts);
    
    /* let regexList = parsed.map((x) => {return x[0].source});
    let resultParts = DEBUG ? [query,
        "|" + regexList.join("|") + "|",
        ""] : []; */
    
    showSearchResults(found,gBoldTextItems)//resultParts.join("\n<hr>\n"));
}

function searchButtonClick() {
    // Read the search bar text, push the updated URL to history, and run a search.
    let query = frame.querySelector('#search-text').value;
    console.log("Called runFromURLSearch. Query:",query);

    let newURL = new URL(location.href);
    newURL.search = "?q=" + encodeURIComponent(query)
    history.pushState({}, "",newURL.href);

    searchFromURL();
}