import {configureLinks} from './frame.js';

const MAX_RESULTS = 100;

let database = null;

function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');
}

export function configureSearch() {
    // Called when a search page is loaded. Load the database, etc.

    console.log("Running congfigureSearch().");
    if (!database) fetch('./assets/SearchDatabase.json')
        .then((response) => response.json())
        .then((json) => {database = json; console.log("Loaded search database.")});
    
    let searchButton = document.getElementById("search-button")
    searchButton.onclick = () => {searchExcerpts(frame.querySelector('#search-text').value);}

    // Execute a function when the user presses a key on the keyboard
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/keydown_event
    document.getElementById("search-text").addEventListener("keydown", function(event) {
        // If the user presses the "Enter" key on the keyboard
        console.log("keypress")
        if (event.key === "Enter") {
            // Cancel the default action, if needed
            event.preventDefault();
            // Trigger the button element with a click
            document.getElementById("search-button").click();
        }
    });
    console.log(searchButton)
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

    const specialChars = "[]{}()#^@"
    let partsSearch = "\\s*(" + [
        matchEnclosedText('""',''),
        matchEnclosedText('{}',specialChars),
        matchEnclosedText('[]',specialChars),
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

function renderExcerpts(excerpts) {
    // Convert a list of excerpts to html code by concatenating their html attributes

    let x = null;
    let bits = [];
    let lastSession = null;
    for (x of excerpts) {
        if (x.session != lastSession) {
            bits.push(database.sessionHeader[x.session]);
            lastSession = x.session;
        }
        bits.push(x.html);
        bits.push("<hr>");
    }
    return bits.join("\n");
}

export function searchExcerpts(query) {
    console.log("Called searchExcerpts.");
    if (!database) {
        console.log("Error: database not loaded.");
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
    let resultParts = [query,
        "|" + parsed.map((x) => {return x[0].source}).join("|") + "|",
        `Found ${found.length} excerpts` + ((found.length > 100) ? `. Showing only the first ${MAX_RESULTS}` : "") + ":",
        renderExcerpts(found.slice(0,MAX_RESULTS))];
    
    let resultsFrame = document.getElementById('results');
    resultsFrame.innerHTML = resultParts.join("\n<hr>\n");
    configureLinks(resultsFrame,location.hash.slice(1))
}