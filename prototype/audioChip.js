const css = `
	button.play {
		vertical-align: middle;
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
		if (!src.includes("://")) {
			src = "../" + src.replaceAll("../","")
		} // Hack: Relative to index.html, audio files are stored at ../audio/excerpts/..., but local references in a page depend on its directory depth.
		// Thus we change src to have exactly one "../" in its path.

		this.audio = new Audio(src);
		let loadAudio = this.dataset.duration == null;
		// let loadAudio = true;
		if (loadAudio) this.audio.load();

		const wrapper = document.createElement("div");
		wrapper.classList.add("wrapper");

		const button = document.createElement("button");
		button.classList.add("play");

		button.addEventListener("click", () => {
			playAudio(this.title, this.audio);
		});

		const timeLabel = document.createElement("span");
		if (loadAudio) {
			timeLabel.innerText = "...";
			this.audio.addEventListener("canplaythrough", () => {
				let duration = Math.round(this.audio.duration);
				timeLabel.innerText = time(duration);
			});
		} else timeLabel.innerText = time(this.dataset.duration);

		const style = document.createElement("style");
		style.innerText = css;

		wrapper.append(button, timeLabel);
		this.shadowRoot.append(style, wrapper);
	}
}

customElements.define("audio-chip", AudioChip);
