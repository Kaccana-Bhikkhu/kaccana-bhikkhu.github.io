<!-- The content below has been extracted from the body of prototype/templates/index.html -->

<img src="images/AjahnPasanno.jpg" width="200">
<h3 class="western">Introduction</h3>
<p>Ajahn Pasanno excels at answering Dhamma questions. I estimate
there are perhaps 100 hours of his question and answer sessions
posted online. If you have a Dhamma question, it’s likely that
Ajahn Pasanno has spoken to it in the past. But how will you find his
answer amidst the hours of available recordings?</p>
<p>This is a demonstration prototype of a search engine to answer
this question. The database contains transcriptions/summaries of the
questions asked and links to Ajahn Pasanno’s recorded answers. The
questions are organised by event and tagged by subject. The web
design is ancient (hopefully you aren’t using a mobile device!),
but it’s enough to demonstrate the principle and debug the
database.</p>
<p>As I began to transcribe question and answer sessions during
Winter Retreat 2023 at Cittaviveka Monastery, I realized that the
stories that Ajahn Pasanno tells in the course of answering Dhamma
questions are as valuable as the questions themselves. The project
now includes these as well.</p>
<p>The principles described below are my best thinking so far. They
are open to revision if Ajahn Pasanno, Ajahn Ñāṇiko, or the
Abhayagiri Saṅgha object.</p>
<h3 class="western">Collaborators</h3>
<p>I created this demonstration prototype, but my web design skills
go no further. My nephew Owen (almost 13!) volunteered to design a
modern website using the same questions database as the prototype.
Owen’s father, Michael, who once worked on the Gmail design team,
has already provided valuable advice to both of us. I have done all
the tagging so far, but I intend to invite online volunteers to help
with transcription and tagging later on.</p>
<p>I plan to update the prototype as we transcribe additional
questions and refine the tagging scheme until Owen’s modern website
is up and running.</p>
<h3 class="western">Scope</h3>
<p>Initially the project will focus on Q&amp;A sessions with Ajahn
Pasanno, although we will transcribe questions incidentally answered
by other teachers in these Q&amp;A sessions. If there is energy and
interest, we might expand the scope to include questions and answers
from other Abhayagiri teachers or non-Abhayagiri teachers at
Abhayagiri-sponsored events. In this case, it would become the
Abhayagiri Q&amp;A Archive. However this is as far as the project
will go. We will source audio recordings only from abhayagiri.org and
Abhayagiri’s YouTube channel. Perhaps others might create a website
to index Q&amp;A sessions from other teachers (see Copyright below).
An <a href="http://birken.ca/qaa/qaa.php">index of Ajahn Sona YouTube
Q&amp;A sessions</a> already exists.</p>
<h3 class="western">Teacher consent</h3>
<p>Not all monks and nuns want their teachings widely distributed.
Most monastics in this tradition went forth due to their experience
of suffering and faith in the Dhamma rather than a desire or ability
to teach. Monastics are generally introverts. A properly-implemented
<a href="https://www.accesstoinsight.org/lib/authors/thanissaro/economy.html">economy
of gifts</a> ensures that material support for monastics is
independent of teaching activity, and the concern is more that people
receive skillful answers to their questions than that they listen to
<i>our</i> answers. At the same time, a diversity of voices answering
a question can help the listener understand multiple perspectives.</p>
<p>For these reasons, we will ask teachers individually about their
detailed preferences before including their questions in the archive.
If teachers prefer, they can review each question individually before
deciding whether it should be included in the archive. It’s too
much to ask volunteers to keep track of whether or not they should
transcribe a question based all these factors, so the database keeps
track of which teachers have given their consent for what. The
website generation engine excludes questions accordingly before they
become available online.</p>
<p>This part of the software is already functional. As of now, the
prototype archive excludes two questions answered by teachers other
than Ajahn Pasanno because I haven’t yet asked their preferences.</p>
<h3 class="western">Copyright</h3>
<p>There are three distinct parts to this project:</p>
<ol>
	<li><p>The audio Q&amp;A database format and the website engines
	that turn it into html code</p>
	<li><p>The tagging scheme partially based on lists from the Pāli
	Canon</p>
	<li><p>The recorded audio and its transcriptions within in the
	database and websites</p>
</ol>
<p>I need to confer with my collaborators and fellow monastics, but I
hope to license #1 and #2 such that they can be openly modified and
reused, perhaps using something like the GPL. However, monastic
Dhamma teachings usually use the <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC
BY-NC-ND</a> license to prevent modification and commercial use. #3
falls in this category, and it’s important to reassure teachers
that their recordings and question transcripts won’t be reused in
harmful or undesired ways.</p>
<p>Most Abhayagiri publications are © Abhayagiri Buddhist Monastery.
This seems the most suitable organisation to assign the copyright to
#3, but I haven’t asked Abhayagiri yet. I would like to consult
with people more knowledgeable than I before deciding on license and
copyright matters. Thus for the time being, all newly created
material in the project is:</p>
<p style="margin-left: 2cm; background: transparent; page-break-before: auto; page-break-after: auto">
© Kaccāna Bhikkhu, All rights reserved</p>
<h3 class="western">Dedication</h3>
<p>This project is dedicated to Luang Por Pasanno (Tan Chao Khun Phra
Rajabodhividesa), my preceptor, teacher, and mentor. He has given his
life to continuing Luang Pu Chah’s efforts to establish Westerners
in the Saṅgha and the Saṅgha in the West. He founded and/or was a
long-term abbot of all the monasteries where I trained before my
tenth rains. He sets an impeccable example of the Holy Life
well-lived, and I’ve watched him handle many challenging situations
with confidence and ease. The epithet of the Saṅgha, “They give
occasion for incomparable goodness to arise in the world” certainly
applies to Luang Por.</p>
<p>Organising Luang Por’s questions so others can find them barely
begins to repay my debt of gratitude to him.</p>
<p style="margin-left: 2cm; background: transparent; page-break-before: auto; page-break-after: auto">
Ajahn Kaccāna</p>
<p style="margin-left: 2cm; background: transparent">December 28,
2022</p>
<hr/>

<h3 class="western">Version list</h3>
<p><b>1.0</b>: First publicly available prototype; contains all
questions from Thanksgiving Retreats 2013-2015 from pre-existing
transcriptions; subject tags are based on transcription text rather
than audio content.</p>
<p><b>1.9</b><span style="font-weight: normal">: Index stories,
quotes, and readings in addition to questions. Added Spirit Rock
daylong events from 2010 and 2011. The tag list has expanded to
include tags from many events transcribed on paper that have not yet
been entered into the online archive. Almost all documentation still
applies to version 1.0.</span></p>
<p><b>1.91</b><span style="font-weight: normal">: Added events: DRBU
Q&amp;A, The Teaching and the Training, and Living in a Changing
Society. Remove unused tags from the tag list (possibly still a few
glitches).</span></p>
<p><b>1.92</b><span style="font-weight: normal">: Added Teen Weekend
2017. Added teacher pages.</span></p>
<p><b>1.93</b><span style="font-weight: normal">: Added Tea Time Q&amp;A
and Abhayagiri Kaṭhina 2021. Embed audio players in the page for
each excerpt. This allows one to read transcriptions while listening
to the talk, but clutters the visual interface. The <a href="https://www.abhayagiri.org/20/index.html">Abhayagiri
20</a></span><a href="https://www.abhayagiri.org/20/index.html"><sup><span style="font-weight: normal">th</span></sup>
<span style="font-weight: normal">Anniversary page</span></a>
<span style="font-weight: normal">demonstrates a good solution, but
it’s well beyond my web skills.</span></p>
<p><b>2.0</b><span style="font-weight: normal"> (May 15, 2023): All pages look much better thanks to css code contributed by Chris Claudius.</span></p>
