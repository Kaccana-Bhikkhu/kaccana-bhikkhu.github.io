<!--TITLE:Want to help?-->
[Preparing for Abhayagiri's 20th Anniversary Celebration](photo:Abhayagiri 20th Anniversary.jpg)
# Want to Help?
If you would like to contribute to the Ajahn Pasanno Question and Story Archive, here are some possibilities.

-----

## Ways Anyone Can Contribute:
### Find stories in Dhamma talks
The APQS Archive indexes stories told in Q&A sessions and Dhamma discussions. Ajahn Pasanno tells many stories during Dhamma talks, but we’re not planning to hunt for them all. If you remember inspiring stories told by or about Ajahn Pasanno contained in recordings on [abhayagiri.org](https://www.abhayagiri.org/talks), please send them to me. If the story isn’t duplicated elsewhere in the archive and seems worthy to be included, we’ll aim to add it to a future version of the Archive.

When you submit stories, please include:

1. The title and date of the Dhamma talk.
2. A link to the talk on [abhayagiri.org](https://www.abhayagiri.org/) or the [Abhayagiri YouTube Channel](https://www.youtube.com/channel/UCFAuQ5fmYYVv5_Dim0EQpVA).
3. The time the story begins in the recording.
4. A suggested title for the story.

For example: “Master Hsu Yun and the Bandits,” 13:49 in the talk “Developing in Virtue” given by Ajahn Pasanno on May 19, 2012.

[Master Hsu Yun and the Bandits](player:https://storage.googleapis.com/apqs_archive/audio/events/Talks/2012-05-19%20Master%20Hsu%20Yun%20and%20the%20Bandits.mp3)

----

### Point out typos or tagging errors
There is so much potential material for the Archive that little proofreading has been done after typing in transcriptions. Thus typos are inevitable, and some tags intended for one excerpt might end up on another. There’s no need for the Archive to be as polished as a printed book, and it often quotes imperfectly phrased questions verbatim. Nevertheless, please let me know if you find any glitches.

-----

## Contributions That Require Skill and Commitment:
### Tag and transcribe Thanksgiving Retreat Questions
__Requirements:__ English proficiency, Comfortable using computers (spreadsheet experience a plus), Attended at least one retreat with Ajahn Pasanno

__Time commitment:__ Most likely 20 hours to learn the system and transcribe your first retreat.

The Archive currently contains questions from the 2013-2016 Thanksgiving Retreats transcribed and time-stamped by the monks who produced the CDs issued shortly after these retreats. The questions are taged based on the transcribe questions but not the audio content of Ajahn Pasanno's answers. I’m hoping that volunteers might listen to these questions, add tags based on the answers, and annotate noteworthy stories, references, and quotes.

If there is energy and enthusiasm after these retreats are finished, there are another half-dozen Thanksgiving Retreats that haven’t been transcribed at all.

----

### Help with programming
__Requirements:__ Proficiency with Javascript web programming, python, and/or Google Sheets gs script

__Time commitment:__ Variable, but programming projects always take longer than you think.

There are many ways a skilled and generous programmer could help with the Archive ([github](https://github.com/Kaccana-Bhikkhu/qs-archive)). Here are some ideas, ranked roughly in order of usefulness with the really big project last.

__Fix bugs:__ For the current list, see [About: status](about:status) and [Github issues](https://github.com/Kaccana-Bhikkhu/qs-archive/issues).

__Add search features:__ The lack of a search page is the most obvious weakness of the current website. There are multiple approaches to this problem. If you’re interested, please let us know your ideas or just go ahead and build something.


__Write a cross-platform mp3 splitter:__ The project currently uses Windows-only mp3DirectCut to quickly and losslessly split mp3 files. It appears that [no cross-platform equivalent exists](https://stackoverflow.com/questions/310765/python-library-to-modify-mp3-audio-without-transcoding). One could write a lossy mp3 splitter using pyaudio or similar module that could be used when mp3DirectCut wasn’t available. This would also enable splitting formats other than mp3.

Alternatively, one could write a python module equivalent to mp3DirectCut. This would need to work on VBR mp3 files and be tested extensively before it would be ready to use.

__Note:__ The the audio splitting functions are slated to be rewritten in the next few months. If you’re interested in the first approach to this project, you may want to wait until this is finished.

__Create a modern search-driven website:__ A modern website designed for mobile devices (and perhaps fully integrated into abhayagiri.org) would make the Archive material substantially more accessible.
