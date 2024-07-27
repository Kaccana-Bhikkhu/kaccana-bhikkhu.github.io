## Test the mp3 player on a local mp3 file:

<p>This is a player pointing to LocalMp3PlayerTest.mp3 in this directory (`pages/about/`):</p>
<audio-chip src="LocalMp3PlayerTest.mp3" title="A veritable blizzard of questions"><a href="LocalMp3PlayerTest.mp3" download="LocalMp3PlayerTest.mp3">Download audio</a> ()</audio-chip><br />

## Live Server path oddity:

This is the image at `../assets/download.svg`: ![download icon](../assets/download.svg)

This is the image at `../../pages/assets/download.svg`: ![download icon](../../pages/assets/download.svg)

This is the image at `../../../pages/assets/download.svg`: ![download icon](../../../pages/assets/download.svg)

This is the image at `../../../../pages/assets/download.svg`: ![download icon](../../../../pages/assets/download.svg)

No matter how many `../` we concatenate, VSCode Live Server still loads the same file. Don't try this on your production server!