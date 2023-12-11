const audioPlayer = document.querySelector("#audio-player");
const playButton = audioPlayer.querySelector("button.play");
const audioTitle = audioPlayer.querySelector("span.audio-title");
let durationTitle = audioTitle.querySelector("span");
const playBar = audioPlayer.querySelector("input[type=range]");
/** @type {HTMLAudioElement} */
let currentlyPlaying = null;
let shouldClose = false;
let playerTimeout;

const time = (sec) =>
	`${Math.floor(sec / 60)}:${(sec % 60).toString().padStart(2, "0")}`;

/**
 *
 * @param {string} title
 * @param {HTMLAudioElement} audio
 */
const playAudio = (title, audio) => {
	let duration = Math.round(audio.duration);

	audioTitle.innerHTML = `${title} <span>${time(0)} / ${time(duration)}</span>`;
	durationTitle = audioTitle.querySelector("span");

	audioPlayer.classList.add("show");
	playButton.classList.add("playing");

	if (currentlyPlaying instanceof HTMLAudioElement) {
		currentlyPlaying.pause();
		currentlyPlaying.currentTime = 0;
	}
	currentlyPlaying = audio;
	if (playerTimeout != null) clearTimeout(playerTimeout)
	audio.play();

	playBar.max = duration;
	playBar.value = 0;
};

const closePlayer = () => {
	console.log("closing player");
	currentlyPlaying.currentTime = 0;
	currentlyPlaying.pause();
	audioPlayer.classList.remove("show");
	playButton.classList.remove("playing");
	currentlyPlaying = null;
};

playBar.addEventListener("change", () => {
	shouldClose = false;
	let currentTime = Math.round(currentlyPlaying.currentTime);
	currentlyPlaying.currentTime = playBar.value;
	durationTitle.innerText = `${time(currentTime)} / ${time(
		Math.round(currentlyPlaying.duration)
	)}`;
});
playButton.addEventListener("click", () => {
	shouldClose = false;
	playButton.classList.toggle("playing");
	currentlyPlaying.paused ? currentlyPlaying.play() : currentlyPlaying.pause();
});

setInterval(() => {
	if (currentlyPlaying != null) {
		let currentTime = Math.round(currentlyPlaying.currentTime);
		let duration = Math.round(currentlyPlaying.duration);
		if (!currentlyPlaying.paused) {
			playBar.value = currentTime;
			durationTitle.innerText = `${time(currentTime)} / ${time(duration)}`;
		}

		if (currentTime === duration) {
			playButton.classList.remove("playing");
			currentlyPlaying.pause();
			currentlyPlaying.currentTime = 0;
			durationTitle.innerText = `${time(currentTime)} / ${time(duration)}`;

			shouldClose = true;
			playerTimeout = setTimeout(() => {
				if (shouldClose) closePlayer();
			}, 10_000);
		}
	}
}, 1000);

globalThis.playAudio = playAudio;
