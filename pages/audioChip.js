import posix from "./path.js";
const { join, dirname } = posix;
const absoluteURLRegex = "^(//|[a-z+]+:)"
const triggerOnce = {
	once: true,
  };

const css = `
	.wrapper {
		height: 40px;
		width: max-content;

		display: grid;
		grid-template-columns: 40px 50px 40px;
		grid-template-rows: 1fr;
		grid-column-gap: 5px;
		grid-row-gap: 0px; 
		align-items: center;
	}

	button.play {
		grid-area: 1 / 1 / 3 / 2;
		
		height: 40px;
		width: 40px;
		border-radius: 0.4rem;
		border: none;
		margin-right: 7px;

		background: url(assets/play.svg) center no-repeat;
		background-size: 40%;
		background-color: #f0f0f0;
		cursor: pointer;
	}

	a {
		opacity: 0.5;
		color: #0088cc !important;
		transition: opacity 200ms ease-out;
		font-size: 0.9em;

		background: url(assets/download.svg) center no-repeat;
		background-size: 40%;
		width: 40px;
		height: 40px;
	}

	a:hover {
		opacity: 1;
	}
`;
const time = (sec) =>
	`${Math.floor(sec / 60)}:${(sec % 60).toString().padStart(2, "0")}`;

class AudioChip extends HTMLElement {
	/** @type {HTMLAudioElement} */
	audio;

	constructor() {
		super();

		this.attachShadow({ mode: "open" });
	}

	connectedCallback() {
		let src = this.getAttribute("src");

		// This code makes src paths relative to the path specified in the hash section of the URL.
		// Remove it if not using frame.js.
		let url = location.hash.split("#")[1];
		if (url && !src.match(absoluteURLRegex)) {
			src = join(dirname(url),src);
		};

		this.audio = new Audio(src);
		let loadAudio = this.dataset.duration == null;
		if (loadAudio)
			this.audio.load()
		else
			this.audio.preload = "none";

		const wrapper = document.createElement("div");
		wrapper.classList.add("wrapper");

		const button = document.createElement("button");
		button.classList.add("play");

		let titleWithLink = this.title;
		if (this.dataset.titleLink) {
			titleWithLink = `<a href="#${this.dataset.titleLink}">${this.title}</a>`
		}

		button.addEventListener("click", () => {
			if (this.audio.readyState >= 3) {
				console.log("audio already loaded; begin playing");
				playAudio(titleWithLink, this.audio);
			} else {
				this.audio.addEventListener(
					"canplay",
					(() => {
						console.log("canplay event triggered; begin playing");
						playAudio(titleWithLink, this.audio);
					}),
					triggerOnce
				);
				this.audio.load();
				console.log("waiting for audio loading");
			}
		});

		const timeLabel = document.createElement("span");
		if (loadAudio) timeLabel.innerText = "...";
		else timeLabel.innerHTML = `<i>${time(this.dataset.duration)}</i>`;
		this.audio.addEventListener("canplaythrough", () => {
			let duration = Math.round(this.audio.duration);
			timeLabel.innerText = time(duration);
		});

		const download = document.createElement("a");
		download.title = "Download";
		download.href = src;
		if (this.dataset.downloadAs)
			download.download = this.dataset.downloadAs;
		else
			download.download = this.title + ".mp3";
		// download.target = "_blank";

		const style = document.createElement("style");
		style.innerText = css;

		wrapper.append(button, timeLabel, download);
		this.shadowRoot.append(style, wrapper);
	}
}

customElements.define("audio-chip", AudioChip);
