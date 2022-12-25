Breaking changes to database.json:

+ 24/12/2022 Kaccana Bhikkhu:
Added "File #" field for each question in order make it easy to hide and show questions from the database:
"Question #" is what the user sees; Increments by 1 each question even when questions are hidden.
"File #" is the number of the mp3 file associated with each question; hidden questions keep their File #.

+ 25/12/2022 Kaccana Bhikkhu:
Make field names more consistent:

Questions field "Teacher" -> "Teachers"
 - This matches the corresponding fields in Event and Sessions
 - All lists now have plural names; dicts have singular names
 
 "Event tags" -> "Tags"
 "Session tags" -> "Tags"
  - This matches the Questions field "Tags"; it's obvious from context what the tags apply to