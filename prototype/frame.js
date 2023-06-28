const frame = document.querySelector("div#frame");
const title = document.querySelector("title");

let path = "";

function changeURL(url) {
	fetch("./" + url)
		.then((r) => r.text())
		.then((text) => {
			frame.innerHTML = text;

			let innerTitle = frame.querySelector("title");
			title.innerHTML = innerTitle.innerHTML;
			innerTitle.remove();

			frame.querySelectorAll("a").forEach((el) => {
				let url = el
					.getAttribute("href")
					.replaceAll("../", "")
					.replaceAll("index.html", "homepage.html");
				el.href = "#" + url;

				el.addEventListener("click", () => {
					changeURL(url);
				});
			});
		});
}

changeURL(location.hash.slice(1) || frame.dataset.url);
