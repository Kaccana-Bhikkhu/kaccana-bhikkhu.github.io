const frame = document.querySelector("div#frame");
const titleEl = document.querySelector("title");

let path = "";

async function changeURL(url) {
	await fetch("./" + url)
		.then((r) => r.text())
		.then((text) => {
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			titleEl.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			frame.querySelectorAll("a").forEach((el) => {
				let url = el
					.getAttribute("href")
					.replaceAll("../", "")
					.replaceAll("index.html", "homepage.html");

				if (url.includes("://")) return;
				else if (url.startsWith("#")) {
					el.href = location.hash;
					el.addEventListener("click", () => {
						document.getElementById(url.slice(1)).scrollIntoView();
					});
				} else {
					el.href = "#" + url;

					el.addEventListener("click", async () => {
						history.pushState({}, "", "#" + url);
						await changeURL(url);
						if (url.includes("#")) {
							if (!url.endsWith("#_keep_scroll")) {
								bookmark = document.getElementById(url.split("#")[1])
								if (bookmark != null) {
									bookmark.scrollIntoView();
								} else {
									window.scrollTo(0, 0);
								}
							}
						} else {
							window.scrollTo(0, 0);
						}
					});
				}
			});
		});
}

changeURL(location.hash.slice(1) || frame.dataset.url);

addEventListener("popstate", () => {
	changeURL(location.hash.slice(1) || frame.dataset.url);
});
