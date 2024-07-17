import {configureLinks} from './frame.js';

const MAX_RESULTS = 100;
const SPECIAL_SEARCH_CHARS = "][{}()#^@";
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

function makeRegExp(element) {
    // Take an element found by parseQuery and return a RegExp describing what it should match.
    // Also add regex strings to gBoldTextItems to indicate how to display the match in bold.
    let unwrapped = element;
    switch (element[0]) {
        case '"': // Items in quotes must match on word boundaries.
            unwrapped = "$" + element.replace(/^"+/,'').replace(/"+$/,'') + "$";
            break;
    }

    // Replace inner * and $ with appropriate operators.
    let escaped = substituteWildcards(unwrapped);
    console.log("processQueryElement:",element,escaped);

    // Start processing again to create RegExps for bold text
    let boldItem = escaped;
    console.log("boldItem before:",boldItem);
    if (element.match(/^\[|\]$/g)) { // are we matching a tag?
        boldItem = substituteWildcards(element.replace(/^\[+/,'').replace(/\]+$/,''));
            // remove enclosing [ ]
    } else if (element.match(/^\{|\}$/g)) { // are we matching a teacher?
        boldItem = substituteWildcards(element.replace(/^\{+/,'').replace(/\}+$/,''));
            // remove enclosing { }
    }
    console.log("boldItem after:",boldItem);

    gBoldTextItems.push(boldItem);
    return new RegExp(escaped,"g");
}

let gBoldTextItems = []; // A list of RegExps representing search matches that should be displayed in bold text.

export function parseQuery(query) {
    // Given a query string, parse it into string search bits.
    // Return a two-dimensional array representing search groups specified by enclosure within parenthesis.
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
    let match = null;
    for (match of query.matchAll(partsSearch)) {
        returnValue.push([makeRegExp(match[1].trim())]);
    }
    return returnValue;
}

export function searchExcerpts(excerpts,parsedQuery) {
    // search the database and return excerpts that match parsedQuery

    let found = [];
    let x = null;
    let blob = null;
    let group = null;
    let searchRegex = null;
    for (x of excerpts) {
        let allGroupsMatch = true;
        for (group of parsedQuery) { 
            let anyBlobMatches = false;
            for (blob of x.blobs) {
                let allKeysMatch = true;
                for (searchRegex of group) {
                    if ((searchRegex.source == '(?:)') || (blob.search(searchRegex) == -1)) {
                        allKeysMatch = false;
                    }
                }
                if (allKeysMatch) {
                    anyBlobMatches = true;
                }
            }
            if (!anyBlobMatches) {
                allGroupsMatch = false;
                break;
            }
        }
        if (allGroupsMatch)
            found.push(x);
    }
    return found;
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

    let params = new URLSearchParams(decodeURIComponent(location.search.slice(1)));
    let query = params.has("q") ? params.get("q") : "";
    console.log("Called searchFromURL. Query:",query);
    frame.querySelector('#search-text').value = query;

    if (!query.trim()) {
        clearSearchResults();
        return;
    }

    let parsed = parseQuery(query);
    console.log(parsed);

    let found = searchExcerpts(database.excerpts,parsed);
    
    let regexList = parsed.map((x) => {return x[0].source});
    let resultParts = DEBUG ? [query,
        "|" + regexList.join("|") + "|",
        ""] : [];
    showSearchResults(found,gBoldTextItems,resultParts.join("\n<hr>\n"));
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