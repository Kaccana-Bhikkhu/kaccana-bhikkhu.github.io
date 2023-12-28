import {configureLinks} from './frame.js';

const MAX_RESULTS = 100;
const SPECIAL_SEARCH_CHARS = "][{}()#^@";
const PALI_DIACRITICS = {
    "a":"ā","i":"ī","u":"ū",
    "d":"ḍ","l":"ḷ","t":"ṭ",
    "n":"ñṇṅ","m":"ṁṃ"
};

let database = null;

function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');
}

const ESCAPED_SPECIAL_CHARS = regExpEscape(SPECIAL_SEARCH_CHARS);

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

function processQueryElement(element) {
    let processed = element.replace(/^"+/,'').replace(/"+$/,'');
    console.log("processQueryElement:",element,processed);
    return processed;
}

function parseQuery(query) {
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

    let returnValue = [];
    let match = null;
    for (match of query.matchAll(partsSearch)) {
        returnValue.push([new RegExp(processQueryElement(regExpEscape(match[1].trim())),"g")]);
    }
    return returnValue;
}

function renderExcerpts(excerpts,boldTextItems) {
    // Convert a list of excerpts to html code by concatenating their html attributes
    // Display strings in boldTextItems in bold.

    let x = null;
    let bits = [];
    let lastSession = null;

    console.log("boldTextItems",boldTextItems)
    let trimLeft = new RegExp(`^[${ESCAPED_SPECIAL_CHARS + "\\\\"}]+`)
    let trimRight = new RegExp(`[${ESCAPED_SPECIAL_CHARS + "\\\\"}]+$`)
    let matchDiacritics = {}
    Object.keys(PALI_DIACRITICS).forEach((letter) => {
        matchDiacritics[letter] = `[${letter}${PALI_DIACRITICS[letter]}]`;
    });
    let textMatchItems = boldTextItems.map((regex) => {
        regex = regex.replace(trimLeft,"").replace(trimRight,"");
        let letter = null;
        for (letter in matchDiacritics) {
            regex = regex.replaceAll(letter,matchDiacritics[letter]);
        }
        return regex;
    });
    console.log(trimLeft,trimRight,"textMatchItems:",textMatchItems);
    let boldTextRegex = new RegExp(`(${textMatchItems.join("|")})(?![^<]*\>)`,"gi");
        // Negative lookahead assertion to avoid modifying html tags.
    for (x of excerpts) {
        if (x.session != lastSession) {
            bits.push(database.sessionHeader[x.session]);
            lastSession = x.session;
        }
        bits.push(x.html.replace(boldTextRegex,"<b>$&</b>"));
        bits.push("<hr>");
    }
    return bits.join("\n");
}

function clearSearchResults() {
    
}

function searchFromURL() {
    // Find excerpts matching the search query from the page URL.
    if (!database) {
        console.log("Error: database not loaded.");
        return;
    }

    let query = decodeURIComponent(location.search.slice(1));
    console.log("Called runFromURLSearch. Query:",query);
    frame.querySelector('#search-text').value = query;

    if (!query.trim()) {
        clearSearchResults();
        return;
    }

    let parsed = parseQuery(query);
    console.log(parsed);

    let found = [];
    let x = null;
    let blob = null;
    let group = null;
    let searchRegex = null;
    for (x of database.excerpts) {
        let allGroupsMatch = true;
        for (group of parsed) { 
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
    
    console.log(parsed);
    let regexList = parsed.map((x) => {return x[0].source});
    let resultParts = [query,
        "|" + regexList.join("|") + "|",
        `Found ${found.length} excerpts` + ((found.length > 100) ? `. Showing only the first ${MAX_RESULTS}` : "") + ":",
        renderExcerpts(found.slice(0,MAX_RESULTS),regexList)];
    
    let resultsFrame = document.getElementById('results');
    resultsFrame.innerHTML = resultParts.join("\n<hr>\n");
    configureLinks(resultsFrame,location.hash.slice(1));
}

function searchButtonClick() {
    // Read the search bar text, push the updated URL to history, and run a search.
    let query = frame.querySelector('#search-text').value;
    console.log("Called runFromURLSearch. Query:",query);

    let newURL = new URL(location.href);
    newURL.search = "?" + encodeURIComponent(query)
    history.pushState({}, "",newURL.href);

    searchFromURL();
}