console.log("Loaded search.js")

function searchExcerpts(query) {
    return query + query;
}

console.log(searchExcerpts("foo "))

console.log(document.getElementById('search-button'))

let searchButton = document.getElementById('search-button')
searchButton.onclick = function () {
    document.getElementById('results').innerHTML = searchExcerpts(document.getElementById('search-text').value);
}