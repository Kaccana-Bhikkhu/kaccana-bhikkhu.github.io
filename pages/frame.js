import posix from "./path.js";
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

async function changeURL(pUrl) {
	await fetch("./" + pUrl)
		.then((r) => pageText(r,pUrl))
		.then((result) => {
			let [text, resultUrl] = result
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			titleEl.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			frame.querySelector("#javascript-link")?.setAttribute("style","display:none;");

			["href","src"].forEach((attribute) => {
				frame.querySelectorAll("["+attribute+"]").forEach((el) => {
					let attributePath = el.getAttribute(attribute);
					if (!attributePath.match(absoluteURLRegex) && !attributePath.startsWith("#")) {
						el.setAttribute(attribute,join(dirname(resultUrl),attributePath));
					};
				});
			});

			frame.querySelectorAll("a").forEach((el) => {
				let href = el.getAttribute("href");
				if (!href || href.match(absoluteURLRegex)) return;
				if (href == "homepage.html#noscript") { // Code to escape javascript
					el.href = "homepage.html";
					return;
				}

				let url = href.replaceAll("index.html", "homepage.html")
				if (href.startsWith("#")) {
					let noBookmark = location.href.split("#").slice(0,2).join("#")
					el.href = noBookmark+href;
					el.addEventListener("click", () => {
						history.pushState({}, "", el.href);
						document.getElementById(href.slice(1)).scrollIntoView();
					});
				} else {
					el.href = "#" + url;

					el.addEventListener("click", async () => {
						history.pushState({}, "", "#" + url);
						await changeURL(url);

						if (!url.endsWith("#_keep_scroll")) {
							window.scrollTo(0, 0);
							if (url.includes("#"))
								delayedScroll(url.split("#")[1])
						}
					});
				}
			});
		});
}

function delayedScroll(bookmark) {
	document.getElementById(bookmark)?.scrollIntoView();
	setTimeout(function(){
		document.getElementById(bookmark)?.scrollIntoView();
	}, 1000);
}

changeURL(location.hash.slice(1) || frame.dataset.url).then(() => {
	if (location.hash.slice(1).includes("#")) {
		delayedScroll(location.hash.slice(1).split("#")[1]);
	}
});

addEventListener("popstate", () => {
	changeURL(location.hash.slice(1) || frame.dataset.url);
});
