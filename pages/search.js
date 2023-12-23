console.log("Loaded search.js")

let database = null
fetch('./assets/SearchDatabase.json')
    .then((response) => response.json())
    .then((json) => {database = json;});

export function searchExcerpts(query) {
    console.log("Called searchExcerpts.");
    if (!database) {
        console.log("Error: database not loaded.");
        return;
    }
    console.log(database);
    let found = [];
    let x = null;
    for (x of database.excerpts) {
        if (x.html.includes(query))
            found.push(x.html);
    }

    document.getElementById('results').innerHTML = query + found.join("\n");
}

/* let searchButton = document.getElementById('search-button')
searchButton.onclick = function () {
    document.getElementById('results').innerHTML = searchExcerpts(document.getElementById('search-text').value);
} */