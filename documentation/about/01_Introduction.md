### Introduction
Ajahn Pasanno excels at answering Dhamma questions. I estimate there are perhaps 100 hours of his question and answer sessions posted online. If you have a Dhamma question, it’s likely that Ajahn Pasanno has spoken to it in the past. But how will you find his answer amidst the hours of available recordings?

This is a demonstration prototype of a search engine to answer this question. The database contains transcriptions/summaries of the questions asked and links to Ajahn Pasanno’s recorded answers. The questions are organised by event and tagged by subject. The web design is ancient (hopefully you aren’t using a mobile device!), but it’s enough to demonstrate the principle and debug the database.

As I began to transcribe question and answer sessions during Winter Retreat 2023 at Cittaviveka Monastery, I realized that the stories that Ajahn Pasanno tells in the course of answering Dhamma questions are as valuable as the questions themselves. The project now includes stories, quotes, and sutta references as well as questions and answers.

The principles described below are my best thinking so far. They are open to revision if Ajahn Pasanno, Ajahn Ñāṇiko, or the Abhayagiri Saṅgha object.

### Collaborators
I created this demonstration prototype, but my web design skills go no further. My nephew Owen volunteered to design a modern website using the same database as the prototype. Owen’s father, Michael, who once worked on the Gmail design team, has already provided valuable advice to both of us. I have done all the tagging so far, but I intend to invite online volunteers to help with transcription and tagging later on.

I plan to update the prototype as we transcribe additional questions and refine the tagging scheme until Owen’s modern website is up and running.

### Scope
Initially the project will focus on Q&A sessions with Ajahn Pasanno, although we will transcribe questions incidentally answered by other teachers in these Q&A sessions. Events including particularly valuable stories will be annotated in greater detail. If there is energy and interest, we might expand the scope to include questions and answers from other Abhayagiri teachers or non-Abhayagiri teachers at Abhayagiri-sponsored events. In this case, it would become the Abhayagiri Question and Story Archive. However this is as far as the project will go. We will source audio recordings only from abhayagiri.org and Abhayagiri’s YouTube channel. Perhaps others might create a website to index Q&A sessions from other teachers (see Copyright below). An index of Ajahn Sona YouTube Q&A sessions already exists.

### Teacher consent
Not all monks and nuns want their teachings widely distributed. Most monastics in this tradition went forth due to their experience of suffering and faith in the Dhamma rather than a desire or ability to teach. Monastics are generally introverts. A properly-implemented economy of gifts ensures that material support for monastics is independent of teaching activity, and the concern is more that people receive skillful answers to their questions than that they listen to our answers. At the same time, a diversity of voices answering a question can help the listener understand multiple perspectives.

For these reasons, we will ask teachers individually about their detailed preferences before including their questions in the archive. If teachers prefer, they can review each question individually before deciding whether it should be included in the archive. It’s too much to ask volunteers to keep track of whether or not they should transcribe a question based all these factors, so the database keeps track of which teachers have given their consent for what. The website generation engine excludes questions accordingly before they become available online.

This part of the software is already functional.

### Copyright
There are three distinct parts to this project:

1. The audio Q&A database format and the website engines that turn it into html code
1. The tagging scheme partially based on lists from the Pāli Canon
1. The recorded audio and its transcriptions within in the database and websites

I need to confer with my collaborators and fellow monastics, but I hope to license #1 and #2 such that they can be openly modified and reused, perhaps using something like the GPL. However, monastic Dhamma teachings usually use the CC BY-NC-ND license to prevent modification and commercial use. #3 falls in this category, and it’s important to reassure teachers that their recordings and question transcripts won’t be reused in harmful or undesired ways.

We will finalize copyright and licensing details in the first official release of the archive. For the time being, all newly created material in the project is:

© 2023 Abhayagiri Buddhist Monastery. All rights reserved

### Dedication
This project is dedicated to Luang Por Pasanno (Tan Chao Khun Phra Rajabodhividesa), my preceptor, teacher, and mentor. He has given his life to continuing Luang Pu Chah’s efforts to establish Westerners in the Saṅgha and the Saṅgha in the West. He founded and/or was a long-term abbot of all the monasteries where I trained before my tenth rains. He sets an impeccable example of the Holy Life well-lived, and I’ve watched him handle many challenging situations with confidence and ease. The epithet of the Saṅgha, “They give occasion for incomparable goodness to arise in the world” certainly applies to Luang Por.

Organising Luang Por’s questions and stories so others can find them barely begins to repay my debt of gratitude to him.

Ajahn Kaccāna

June 6, 2023

Version list
1.0: First publicly available prototype; contains all questions from Thanksgiving Retreats 2013-2015 from pre-existing transcriptions; subject tags are based on transcription text rather than audio content.

1.9: Index stories, quotes, and readings in addition to questions. Added Spirit Rock daylong events from 2010 and 2011. The tag list has expanded to include tags from many events transcribed on paper that have not yet been entered into the online archive. Almost all documentation still applies to version 1.0.

1.91: Added events: DRBU Q&A, The Teaching and the Training, and Living in a Changing Society. Remove unused tags from the tag list (possibly still a few glitches).

1.92: Added Teen Weekend 2017. Added teacher pages.

1.93: Added Tea Time Q&A and Abhayagiri Kaṭhina 2021. Embed audio players in the page for each excerpt. This allows one to read transcriptions while listening to the talk, but clutters the visual interface. The Abhayagiri 20th Anniversary page demonstrates a good solution, but it’s well beyond my web skills.

2.0 (May 15, 2023): All pages look much better thanks to css code contributed by Chris Claudius.

2.1 Added three Upasika Days: Thai Forest Tradition, Mindfulness of Breathing, and Jhāna: A Practical Approach

2.1.1 Added three Upasika Days: Honoring the Buddha, The Middle Way of Not-self, and Death and Dying. Added the Spirit Rock Daylong about Friendship.

2.1.2 Added the 2008 Metta Retreat and the Spirit Rock Daylong Desire or Aspiration. Assigned copyright to Abhayagiri Buddhist Monastery.

2.1.3 Added Upasika Day: Right Livelihood.

2.2 Implemented session excerpts. Added Stanford Communtiy Dhamma Discussion and Upasika Day: Buddhist Identity. Added three sessions from Winter Retreat 2014 for testing purposes.

2.3 Added Chanting Upasika Day and Path of Practice weekend.

2.3.1 Added three more Upasika Days and BIA New Year, New Life.
