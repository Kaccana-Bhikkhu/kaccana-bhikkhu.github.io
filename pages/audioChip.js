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
		this.audio = new Audio(src);
		this.audio.preload = "none";
		let loadAudio = false // this.dataset.duration == null;
		// let loadAudio = true;
		if (loadAudio) this.audio.load();

		const wrapper = document.createElement("div");
		wrapper.classList.add("wrapper");

		const button = document.createElement("button");
		button.classList.add("play");

		let loaded = loadAudio;
		this.audio.addEventListener("canplaythrough", () => {
			loaded = true;
		});
		button.addEventListener("click", () => {
			if (loaded) {
				console.log("audio loaded");
				playAudio(this.title, this.audio);
			} else {
				this.audio.load();
				console.log("waiting for audio loading");
				let cb;
				this.audio.addEventListener(
					"canplaythrough",
					(cb = () => {
						console.log("starting");
						playAudio(this.title, this.audio);
						this.audio.removeEventListener("canplaythrough", cb);
					})
				);
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
		download.download = this.title + ".mp3";
		// download.target = "_blank";

		const style = document.createElement("style");
		style.innerText = css;

		wrapper.append(button, timeLabel, download);
		this.shadowRoot.append(style, wrapper);
	}
}

customElements.define("audio-chip", AudioChip);
