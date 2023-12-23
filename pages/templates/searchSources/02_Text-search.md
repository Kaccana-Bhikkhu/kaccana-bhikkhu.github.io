<div>

<input type="text" id="search-text" />

<br><br>
<button type="button"
onclick="document.getElementById('results').innerHTML = searchExcerpts(document.getElementById('search-text').value)">
Search</button>

<p id="results"></p>
</div>