## Want to help?
If you would like to contribute to the Ajahn Pasanno Question and Story Archive, here are some possibilities.

-----

## Ways Anyone Can Contribute:
### Find stories in Dhamma talks
The APQS Archive indexes stories told in Q&A sessions and Dhamma discussions. Ajahn Pasanno tells many stories during Dhamma talks, but I’m not planning to hunt for them all. If you remember inspiring stories told by or about Ajahn Pasanno contained in recordings on [abhayagiri.org](https://www.abhayagiri.org/talks), please send them to me. If the story isn’t duplicated elsewhere in the archive and seems worthy to be included, I’ll aim to add it to a future version of the Archive.

When you submit stories, please include:

1. The title and date of the Dhamma talk.
2. A link to the talk on [abhayagiri.org](https://www.abhayagiri.org/) or the [Abhayagiri YouTube Channel](https://www.youtube.com/channel/UCFAuQ5fmYYVv5_Dim0EQpVA).
3. The time the story begins in the recording.
4. A suggested title for the story.

For example: “Master Hsu Yun and the Bandits,” 13:49 in the talk “Developing in Virtue” given by Ajahn Pasanno on May 19, 2012.

[](player:https://storage.googleapis.com/apqs_archive/audio/events/Talks/2012-05-19%20Master%20Hsu%20Yun%20and%20the%20Bandits.mp3)

----

### Point out typos or tagging errors
There is so much potential material for the Archive that I do little proofreading after typing in transcriptions. Thus typos are inevitable, and some tags intended for one excerpt might end up on another. There’s no need for the Archive to be as polished as a printed book, and it often quotes imperfectly phrased questions verbatim. Nevertheless, please let me know if you find any glitches.

-----

## Contributions That Require Skill and Commitment:
### Tag and transcribe Thanksgiving Retreat Questions
__Requirements:__ English proficiency, Comfortable using computers (spreadsheet experience a plus), Attended at least one retreat with Ajahn Pasanno

__Time commitment:__ I estimate it will take 20 hours to learn the system and transcribe your first retreat.

The Archive currently contains questions from the 2013-2016 Thanksgiving Retreats transcribed and time-stamped by the monks who produced the CDs issued shortly after these retreats. I have tagged the questions based on the transcriptions but have not listened to Ajahn Pasanno’s answers. I’m hoping that volunteers might listen to these questions, add tags based on the answers, and annotate noteworthy stories, references, and quotes.

If there is energy and enthusiasm after these retreats are finished, there are another half-dozen Thanksgiving Retreats that haven’t been transcribed at all.

----

### Help with programming
__Requirements:__ Proficiency with Javascript web programming, python, and/or Google Sheets gs script

__Time commitment:__ Variable, but programming projects always take longer than you think.

There are many ways a skilled and generous programmer could help with the Archive ([github](https://github.com/Kaccana-Bhikkhu/qs-archive)). Here are my ideas, ranked roughly in order of usefulness with the really big project last.


__Add search features:__ The lack of a search page is the most obvious weakness of the current website. There are multiple approaches to this problem. If you’re interested, please let me know your ideas or just go ahead and build something.



__Track changes in the main spreadsheet:__ The [main spreadsheet](https://docs.google.com/spreadsheets/d/1PR197U5m4dtSi-q2ibMwc2xA7TSczA_Df7YP8JGJ3No/edit#gid=2007732801) contains 50 sheets and continues to grow. There is currently no way to know which sheets have changed, so one must either remember which sheets have changed or download them all.

Modifying the Summary sheet to track the modification time of each sheet would solve this problem. The script needs to handle adding, deleting, renaming, and reordering sheets without breaking.



__Write a cross-platform mp3 splitter:__ The project currently uses Windows-only mp3DirectCut to quickly and losslessly split mp3 files. It appears that [no cross-platform equivalent exists](https://stackoverflow.com/questions/310765/python-library-to-modify-mp3-audio-without-transcoding). One could write a lossy mp3 splitter using pyaudio or similar module that could be used when mp3DirectCut wasn’t available. This would also enable splitting formats other than mp3.

Alternatively, one could write a python module equivalent to mp3DirectCut. This would need to work on VBR mp3 files and be tested extensively before it would be ready to use.

__Note:__ I plan to rewrite the audio splitting functions in the next few months. If you’re interested in the first approach to this project, you may want to wait until I’ve done so.



__Create a modern search-driven website:__ It had originally been my intention to write only the back end of the Archive and partner with a web developer to build the website. The current website began as a prototype to illustrate how to render excerpts and annotations from the database. However, my potential partner had much less time to dedicate to the project than a full website would require, and I found that an enhanced version of the prototype to be usable even on mobile devices.

Nevertheless, a modern website designed for mobile devices and fully integrated into abhayagiri.org would make the archive material substantially more accessible. If someone wanted to try his or her hand at this substantial project, I would be happy to support them, at least until I decide to call this project complete to focus on other aspects of monastic life. 

