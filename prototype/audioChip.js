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

class AudioChip extends HTMLElement {
	/** @type {HTMLAudioElement} */
	audio;

	constructor() {
		super();

		this.attachShadow({ mode: "open" });
	}

	connectedCallback() {
		this.audio = new Audio(this.getAttribute("src"));
		this.audio.load();

		const wrapper = document.createElement("div");
		wrapper.classList.add("wrapper");

		const button = document.createElement("button");
		button.classList.add("play");

		const time = document.createElement("span");
		this.audio.addEventListener("canplaythrough", () => {
			let duration = Math.round(this.audio.duration);
			time.innerText = `${Math.floor(duration / 60)}:${duration % 60}`;
		});

		const style = document.createElement("style");
		style.innerText = css;

		wrapper.append(button, time);
		this.shadowRoot.append(style, wrapper);
	}
}

customElements.define("audio-chip", AudioChip);
