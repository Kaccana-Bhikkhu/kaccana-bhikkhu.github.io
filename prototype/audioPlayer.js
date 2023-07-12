const audioPlayer = document.querySelector("#audio-player");
const playButton = audioPlayer.querySelector("button.play");
const audioTitle = audioPlayer.querySelector("span.audio-title");
let durationTitle = audioTitle.querySelector("span");
const playBar = audioPlayer.querySelector("input[type=range]");
/** @type {HTMLAudioElement} */
let currentlyPlaying = null;

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
	audio.play();

	playBar.max = duration;
	playBar.value = 0;

	playBar.addEventListener("change", () => {
		audio.currentTime = playBar.value;
	});
	playButton.addEventListener("click", () => {
		playButton.classList.toggle("playing");
		audio.paused ? audio.play() : audio.pause();
	});
};

setInterval(() => {
	if (currentlyPlaying != null) {
		let currentTime = Math.round(currentlyPlaying.currentTime);
		playBar.value = currentTime;
		durationTitle.innerText = `${time(currentTime)} / ${time(
			Math.round(currentlyPlaying.duration)
		)}`;
	}
}, 1000);

globalThis.playAudio = playAudio;
