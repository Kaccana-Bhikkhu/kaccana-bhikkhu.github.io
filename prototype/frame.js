import posix from "./path.js";
const { join, dirname } = posix;
const frame = document.querySelector("div#frame");
const titleEl = document.querySelector("title");

let path = "";

async function changeURL(pUrl) {
	await fetch("./" + pUrl)
		.then((r) => r.text())
		.then((text) => {
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			titleEl.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			frame.querySelectorAll("a").forEach((el) => {
				let href = el.getAttribute("href");
				if (el.getAttribute("href").includes("://")) return;

				let url = join(
					dirname(pUrl),
					href.replaceAll("index.html", "homepage.html")
				);

				if (href.startsWith("#")) {
					el.href = "javascript:void 0";
					el.addEventListener("click", () => {
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
		console.log("double hash!");
		document
			.getElementById(location.hash.slice(1).split("#")[1])
			?.scrollIntoView();
	}
});

addEventListener("popstate", () => {
	changeURL(location.hash.slice(1) || frame.dataset.url);
});
