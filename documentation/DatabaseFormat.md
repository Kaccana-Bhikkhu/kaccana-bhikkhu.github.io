# database.json format and change log

ParseCSV.py reads [AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) and writes database.json. Many sheets are simply read into the database as fields bearing the same name. Bold cell names in the spreadsheet indicate subfield names in the database. Documentation for many subfields can be found in cell comments in the spreadsheet.

The best way to study the structure of database.json is to compare its file contents with the [prototype website](https://storage.googleapis.com/apqa_archive/prototype/indexes/AllQuestions.html).

## Change log

Changes which might break already-written code are marked §.

### 24/12/2022 Enabled question redaction - Kaccana Bhikkhu:
 - Added teacher consent flags to the database.Teacher
 - § Added "File #" subfield to database.Questions in order make it easy to redact (remove) questions in the csv files from database.json and the resulting website without breaking mp3 hyperlinks. "Question #" is what the user sees; this increments by 1 for each visible question even when previous questions have been redacted. "File #" is the number of the mp3 file associated with each question. Reacted questions keep their "File #".
 - Added database.Questions_Redacted which contains enough information about the redacted questions to split mp3 files properly.

### 25/12/2022 - More consistent field names - Kaccana Bhikkhu:
§ database.Questions field "Teacher" -> "Teachers"
 - This matches the corresponding fields in database.Event and database.Sessions
 - All lists now have plural names; dicts have singular names
 
 § database.Event: "Event tags" -> "Tags",  database.Sessions: "Session tags" -> "Tags"
  - These match database.Questions field "Tags"; it's obvious from context what the tags apply to
