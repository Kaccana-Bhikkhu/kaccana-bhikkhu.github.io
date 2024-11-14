import {configureLinks,frameSearch,setFrameSearch} from './frame.js';

const DEBUG = false;

let gDatabase = null; // The global database, loaded from assets/RandomExcerpts.json

export async function loadHomepage() {
    // Called when the search page is loaded. Load the random excerpt database
    // and configure the forward and back buttons

    for (let kind of "xg") {
        let searchButton = document.getElementById(`search-${kind}-button`);
        if (!searchButton)
            return; // Exit if it's a non-search page.
        searchButton.onclick = () => { searchButtonClick(kind); }
    }

    let params = frameSearch();
    let query = params.has("q") ? decodeURIComponent(params.get("q")) : "";
    if (!query)
        document.getElementById("search-text").focus();

    // Execute a function when the user presses a key on the keyboard
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/keydown_event
    document.getElementById("search-text").addEventListener("keydown", function(event) {
        // If the user presses the "Enter" key on the keyboard
        if (event.key === "Enter") {
            // Cancel the default action, if needed
            event.preventDefault();
            // Trigger the button element with a click
            document.getElementById("search-x-button").click();
        }
    });

    if (!gDatabase) {
        await fetch('./assets/SearchDatabase.json')
        .then((response) => response.json())
        .then((json) => {
            gDatabase = json; 
            console.log("Loaded search database.");
            for (let code in gDatabase["searches"]) {
                if (code == "x")
                    gSearchers[code] = new ExcerptSearcher(gDatabase.searches[code]);
                else
                    gSearchers[code] = new Searcher(gDatabase.searches[code]);
            }
        });

    }

    searchFromURL();
}

function searchButtonClick(searchKind) {
    // Read the search bar text, push the updated URL to history, and run a search.
    let query = frame.querySelector('#search-text').value;
    console.log("Called runFromURLSearch. Query:",query,"Kind:",searchKind);

    let search = new URLSearchParams({q : encodeURIComponent(query),search : searchKind});
    history.pushState({},"",location.href); // First push a new history frame
    setFrameSearch(search); // Then replace the history with the search query

    /* let newURL = new URL(location.href);
    newURL.search = `?q=${encodeURIComponent(query)}&search=${searchKind}`
    history.pushState({}, "",newURL.href); */

    searchFromURL();
}