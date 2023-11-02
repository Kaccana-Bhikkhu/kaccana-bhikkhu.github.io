import posix from "./path.js";
const { join, dirname } = posix;
const frame = document.querySelector("div#frame");
const titleEl = document.querySelector("title");
const absoluteURLRegex = "^(//|[a-z+]+:)"

async function changeURL(pUrl) {
	await fetch("./" + pUrl)
		.then((r) => r.text())
		.then((text) => {
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			titleEl.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			["href","src"].forEach((attribute) => {
				frame.querySelectorAll("["+attribute+"]").forEach((el) => {
					let attributePath = el.getAttribute(attribute);
					if (!attributePath.match(absoluteURLRegex) && !attributePath.startsWith("#")) {
						el.setAttribute(attribute,join(dirname(pUrl),attributePath));
					};
				});
			});

			frame.querySelectorAll("a").forEach((el) => {
				let href = el.getAttribute("href");
				if (!href || href.match(absoluteURLRegex)) return;

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
								document.getElementById(url.split("#")[1])?.scrollIntoView();
						}
					});
				}
			});
		});
}

changeURL(location.hash.slice(1) || frame.dataset.url).then(() => {
	if (location.hash.slice(1).includes("#")) {
		document
			.getElementById(location.hash.slice(1).split("#")[1])
			?.scrollIntoView();
	}
});

addEventListener("popstate", () => {
	changeURL(location.hash.slice(1) || frame.dataset.url);
});
