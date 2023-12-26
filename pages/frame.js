import posix from "./path.js";
import { searchExcerpts } from "./search.js";
const { join, dirname } = posix;
const frame = document.querySelector("div#frame");
const titleEl = document.querySelector("title");
const absoluteURLRegex = "^(//|[a-z+]+:)"
const errorPage = "./about/Page-Not-Found.html"

function pageText(r,url) {
	if (r.ok) {
		return r.text().then((text) => Promise.resolve([text,url]))
	} else {
		console.log("Page not found. Fetching",errorPage)
		return fetch(errorPage)
			.then((r) => r.text())
			.then((text) => Promise.resolve([text.replace("$PAGE$",url),errorPage]))
	}
}

export function configureLinks(frame,url) {
	// Configure links within frame to be relative to url and link to #index.html
	console.log("configureLinks:",url);
	["href","src"].forEach((attribute) => {
		frame.querySelectorAll("["+attribute+"]").forEach((el) => {
			let attributePath = el.getAttribute(attribute);
			if (!attributePath.match(absoluteURLRegex) && !attributePath.startsWith("#")) {
				el.setAttribute(attribute,join(dirname(url),attributePath));
			};
		});
	});

	frame.querySelectorAll("a").forEach((el) => {
		let href = el.getAttribute("href");
		if (!href || href.match(absoluteURLRegex)) return;
		if (href.endsWith("#noscript")) { // Code to escape javascript
			el.href = el.href.replace("#noscript","");
			return;
		}

		let url = href.replaceAll("index.html", "homepage.html")
		if (href.startsWith("#")) {
			let noBookmark = decodeURIComponent(location.href).split("#").slice(0,2).join("#")
			el.href = noBookmark+href;
			el.addEventListener("click", () => {
				history.pushState({}, "", el.href);
				document.getElementById(href.slice(1)).scrollIntoView();
			});
		} else {
			el.href = "#" + url;

			el.addEventListener("click", async (event) => {
				history.pushState({}, "", "#" + url);
				event.preventDefault(); // Don't follow the href link
				await changeURL(url);

				if (!url.endsWith("#_keep_scroll")) {
					window.scrollTo(0, 0);
					if (url.includes("#"))
						delayedScroll(url.split("#")[1])
				}
			});
		}
	});
}

async function changeURL(pUrl) {
	pUrl = decodeURIComponent(pUrl)
	console.log("changeURL",pUrl)
	await fetch("./" + pUrl)
		.then((r) => pageText(r,pUrl))
		.then((result) => {
			let [text, resultUrl] = result
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			titleEl.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			frame.querySelector("#javascript-link")?.setAttribute("style","display:none;");
			let searchButton = frame.querySelector("#search-button")
			if (searchButton) {
				searchButton.onclick = () => {searchExcerpts(frame.querySelector('#search-text').value);}
			}

			configureLinks(frame,resultUrl)
		});
}

function delayedScroll(bookmark) {
	document.getElementById(bookmark)?.scrollIntoView();
	setTimeout(function(){
		document.getElementById(bookmark)?.scrollIntoView();
	}, 1000);
}

changeURL(location.hash.slice(1) || frame.dataset.url).then(() => {
	let urlHash = decodeURIComponent(location.hash)
	if (urlHash.slice(1).includes("#")) {
		delayedScroll(urlHash.slice(1).split("#")[1]);
	}
});

addEventListener("popstate", () => {
	changeURL(location.hash.slice(1) || frame.dataset.url);
});
