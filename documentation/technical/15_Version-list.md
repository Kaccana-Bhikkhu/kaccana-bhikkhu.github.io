<!--HTML <img src="../../pages/images/photos/LPP with novices Thailand Dec 2015.jpg" alt="Ajahn Pasanno in Thailand, December 2015" class="cover" title="Ajahn Pasanno in Thailand, December 2015" align="bottom" width="200" border="0"/> -->
# Version list
- 1.0: First publicly available prototype; contains all questions from Thanksgiving Retreats 2013-2015 from pre-existing transcriptions; subject tags are based on transcription text rather than audio content.

- 1.9: Index stories, quotes, and readings in addition to questions. Added Spirit Rock daylong events from 2010 and 2011. The tag list has expanded to include tags from many events transcribed on paper that have not yet been entered into the online archive. Almost all documentation still applies to version 1.0.

- 1.91: Added events: DRBU Q&A, The Teaching and the Training, and Living in a Changing Society. Remove unused tags from the tag list (possibly still a few glitches).

- 1.92: Added Teen Weekend 2017. Added teacher pages.

- 1.93: Added Tea Time Q&A and Abhayagiri Kaṭhina 2021. Embed audio players in the page for each excerpt. This allows one to read transcriptions while listening to the talk, but clutters the visual interface.

- 2.0 (May 15, 2023): All pages look much better thanks to css code contributed by Chris Claudius.

- 2.1 Added three Upāsikā Days: Thai Forest Tradition, Mindfulness of Breathing, and Jhāna: A Practical Approach

- 2.1.1 Added three Upāsikā Days: Honoring the Buddha, The Middle Way of Not-self, and Death and Dying. Added the Spirit Rock Daylong about Friendship.

- 2.1.2 Added the 2008 Metta Retreat and the Spirit Rock Daylong Desire or Aspiration. Assigned copyright to Abhayagiri Buddhist Monastery.

- 2.1.3 Added Upāsikā Day: Right Livelihood.

- 2.2 Implemented session excerpts. Added Stanford Communtiy Dhamma Discussion and Upāsikā Day: Buddhist Identity. Added three sessions from Winter Retreat 2014 for testing purposes.

- 2.3 Added Chanting Upāsikā Day and Path of Practice weekend.

- 2.3.1 Added three more Upāsikā Days and BIA New Year, New Life.

- 3.0 Floating media player (Thanks Owen!). Drill-down tag hierarchy. Category subsearch on All Excerpts and tag pages. About pages are rendered from markdown files in documentation/about.

- 3.1 Alphabetical tag listings. List events by series and year. List teachers chronologically and by lineage. Category search on teacher pages. Links between teacher and tag pages. Calming the Busy Mind Upāsikā Day.

- 3.2 Move website to pages directory. Reogranize python and assets files. Reorganize tag hierarchy. Document event series and tags. Render links to tags and events. Fix links to bookmarks from external pages.

- 3.2.1 Add About pages: Overview, Ways to Help, and Licence. Thanksgiving Retreat 2016. Retag Thanksgiving Retreat 2015.

- 3.2.2 Add About pages: What's new? and Contact. Render links to teachers, about pages, images, and the media player. Complex workaround needed to link to non-page items (e.g. images) in Document.RenderDocumenationFiles. Loading images properly in both the static html pages and frame.js will require modifications to frame.js.

- 3.3 Add Glosses column in Tag sheet. Improve alphabetical tag list. Enable tag sorting by date. Events listed in tag pages. Indirect quotes link to teacher. Added Upāsikā Day 2018: The New Ajahn Chah Biography.

- 3.3.1 Apply ID3 tags to excerpt mp3 files.

- 3.3.2 Download icon. Readings can now be annotations. Minor changes to session excerpts. Winter Retreat 2015 partially complete (through Session 13).

- 3.3.3 Download only changed sheets. Word count. Upload to abhayagiri.org. Audio icon on All/searchable pages. Links between about and series pages.

- 3.3.4 Add --mirror option to specify possible sources of audio and reference files. Winter Retreat 2015 through Session 24.

- 3.3.5 Suggested citation footer (needs polishing). Documentation updates.

- 3.4 Add photos to documentation. Much improved citation footer title. Html meta tag keywords. Remove meta robots search engine block. Several layout changes in preparation for Chris Claudius's new style sheet. --linkCheckLevel option.

- 3.4.1 Redirect plain pages to index.html#path. Add links to subsearches in All Excerpts pages. Add subsearch keywords and page descriptions. --urlList option for search engine submissions.

- 3.4.2 Fix back button after following bookmark links. Add many teacher dates. Documentation changes suggested by Ajahn Suhajjo.

- 3.5 Style update by Chris Claudius.

- 3.5.1 Updated license page, teacher ordination dates, and ID3 tags. Version list and License moved to Technical submenu. Remove mistaken robots exclusion tag introduced in Version 3.5.

- 3.5.2 Make no script website (homepage.html) more accessible.

- 3.5.3 (November 2023 Release) Don't preload audio to reduce data usage.

- 3.6 Added Upāsikā Days: On Pilgrimage and Tudong and Developing Skill in Reflective Meditation. Drilldown html files named by tag. Count excerpts referred to by subtags in hierarchical lists. Fix bug that removed "Refraining from:" and other list headings. Fix bug where bookmarks scroll to the wrong place in pages with slow-loading images.

- 3.6.1 Added three Upāsikā Days: Two Kinds of Thought, Practice in a Global Context, and Love, Attachement, and Friendship. Numerical tag page shows canonical numbered lists. Cache checksums of many files and overwrite them only when needed. Fix bug where csv files were downloaded multiple times.

- 3.6.2 Finished Winter Retreat 2015. DownloadFiles.py downloads needed mp3 and pdf files from remote URLs. System of clips and audioSources will allow more flexible audio processing. Fix bug displaying incorrect number of excerpts in event lists. Fix frame.js bug with #noscript links.

- 3.6.3 Add Page Not Found page. Add custom CLIP ID3 tag to excerpt mp3s to describe the audio source. Check if the mp3 CLIP tag matches the excerpt clip. If not, SplitMp3 recreates the mp3 file. Move unneded files to NoUpload directories.

- 3.6.4 Add CheckLinks module. Include only about pages and events in sitemap.xml. New command line options: --args Filename.args includes the arguments in Filename.args in the command line; --no-XXX sets boolean option XXX to False; --multithread allows multithreaded http operations.

- 3.6.5 (December 2023 release) Don't truncate player titles. Fix glitch in multipage excerpt list page menu.

- 3.7 More versatile audio processing framework. Don't split excluded excerpts. Allow overlapping clips. Fix player close timout (contributed by Owen). Don't redirect file:// URLs to index.html# to allow simple local browsing. WR2014 finished.

- 4.0 Search feature. Minor changes to WR2014. ParseCSV option --auditNames.

- 4.0.1 Updated many Thai Ajahns' names and dates with information from Krooba Kai. Teacher attributionName field. WR2014 table of contents. ParseCSV option --dumpCSV.

- 4.0.2 (January 2024 release) About page with search instructions.

- 4.1 (July 2024 release) 2001 Ajahn Chah Conference almost finished. Finalized the license. Allow search engines to index pages (fingers crossed). Apply smart quotes to text. ParseCSV option --pendingMeansYes. Unit tests for search feature. Fix several minor bugs.

- 4.1.1 Removed All/Searchable pages.

- 4.2 Added Upāsikā Day: Can We Function Without Attachement? and Ajahn Pasanno's Q&A sessions from the 25th Anniversary Retreat. Obtained teacher consent for almost all Chah2001 excerpts. Added tag search feature. Updated the tags with changes from Version 9. Alphabetical tag listing improvements. search.js is more readable. Database-related functions moved to Database.py.

- 4.2.1 (August 2024 release) Minor changes to tags and alphabetical tag listings. Minor fixes to search display.
