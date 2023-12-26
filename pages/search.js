console.log("Loaded search.js")

let database = null
fetch('./assets/SearchDatabase.json')
    .then((response) => response.json())
    .then((json) => {database = json;});

function renderExcerpts(excerpts) {
    // Convert a list of excerpts to html code by concatenating their html attributes

    let x = null
    let bits = []
    let lastSession = null
    for (x of excerpts) {
        if (x.session != lastSession) {
            bits.push(database.sessionHeader[x.session])
            lastSession = x.session
        }
        bits.push(x.html)
        bits.push("<hr>")
    }
    return bits.join("\n");
}

function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');
}

function parseQuery(query) {
    // Given a query string, parse it into string search bits.
    // Return a two-dimensional array representing search groups specified by enclosure within parenthesis.
    // Each excerpt must match all search groups.
    // Search keys within a search group must be matched within the same blob.
    // So (#Read Pasanno}) matches only kind 'Reading' or 'Read by' with teacher ending with Pasanno

    query = query.toLowerCase()
    query = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "") // https://stackoverflow.com/questions/990904/remove-accents-diacritics-in-a-string-in-javascript

    const partsSerach = /\s*\S+/g;
    let returnValue = [];
    let match = null;
    for (match of query.matchAll(partsSerach)) {
        returnValue.push([new RegExp([match[0].trim()],"g")]);
    }
    return returnValue;
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
                    if (blob.search(searchRegex) == -1) {
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
        parsed.map((x) => {return x[0].source}).join("|"),
        `Found ${found.length} excerpts:`,
        renderExcerpts(found)]
    document.getElementById('results').innerHTML = resultParts.join("\n<hr>\n");
}