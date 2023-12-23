console.log("Loaded search.js")

export function searchExcerpts(query) {
    console.log("Called searchExcerpts.")
    document.getElementById('results').innerHTML = query + query;
}

/* let searchButton = document.getElementById('search-button')
searchButton.onclick = function () {
    document.getElementById('results').innerHTML = searchExcerpts(document.getElementById('search-text').value);
} */