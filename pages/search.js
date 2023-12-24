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

function parseQuery(query) {
    // Given a query string, parse it into string search bits.
    // Return a two-dimensional array representing search groups specified by enclosure within parenthesis.
    // Each excerpt must match all search groups.
    // Search keys within a search group must be matched within the same blob.
    // So (#Read Pasanno}) matches only kind 'Reading' or 'Read by' with teacher ending with Pasanno

    const partsSerach = /\s*\S+/g;
    let returnValue = [];
    let match = null;
    for (match of query.matchAll(partsSerach)) {
        returnValue.push([match[0].trim()])
    }
    return returnValue
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
    let searchKey = null;
    for (x of database.excerpts) {
        let allGroupsMatch = true;
        for (group of parsed) { 
            let anyBlobMatches = false;
            for (blob of x.blobs) {
                let allKeysMatch = true
                for (searchKey of group) {
                    if (!blob.includes(searchKey)) {
                        allKeysMatch = false;
                    }
                }
                if (allKeysMatch) {
                    anyBlobMatches = true
                }
            }
            if (!anyBlobMatches) {
                allGroupsMatch = false;
                break;
            }
        }
        if (allGroupsMatch)
            found.push(x)
    }

    let resultParts = [query,
        parsed.join("|"),
        `Found ${found.length} excerpts:`,
        renderExcerpts(found)]
    document.getElementById('results').innerHTML = resultParts.join("\n<hr>\n");
}