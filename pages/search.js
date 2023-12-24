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

    const partsSerach = /\s*\S+/g;
    let returnValue = [];
    let match = null;
    for (match of query.matchAll(partsSerach)) {
        returnValue.push(match[0].trim())
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
    for (x of database.excerpts) {
        for (blob of x.blobs) {
            if (blob.includes(query)) {
                found.push(x)
                break
            }
        }
    }

    let resultParts = [query,
        parsed.join("|"),
        `Found ${found.length} excerpts:`,
        renderExcerpts(found)]
    document.getElementById('results').innerHTML = resultParts.join("\n<hr>\n");
}