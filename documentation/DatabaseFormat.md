# Database.json and SpreadsheetDatabase.json format and change log

ParseCSV.py reads [AP QA archive main](https://docs.google.com/spreadsheets/d/1JIOwbYh6M1Ax9O6tFsgpwWYoDPJRbWEzhB_nwyOSS20/edit?usp=sharing) and writes prototype/SpreadsheetDatabase.json. Many sheets are simply read into the database as fields bearing the same name. Bold cell names in the spreadsheet indicate subfield names in the database. Documentation for many subfields can be found in cell comments in the spreadsheet.

OptimizeDatabase writes Database.json, which contains the same information optimized for the Javascript-based main website.

The best way to study the structure of these files is to compare their contents with the [prototype website](https://storage.googleapis.com/apqa_archive/prototype/index.html).

## Change log

Changes which might break already-written code are marked §.

### 24/12/2022 Enabled question redaction - Kaccana Bhikkhu:
 - Added teacher consent flags to the Database.Teacher
 - § Added "File #" subfield to Database.Questions in order make it easy to redact (remove) questions in the csv files from Database.json and the resulting website without breaking mp3 hyperlinks. "Question #" is what the user sees; this increments by 1 for each visible question even when previous questions have been redacted. "File #" is the number of the mp3 file associated with each question. Reacted questions keep their "File #".
 - Added Database.Questions_Redacted which contains enough information about the redacted questions to split mp3 files properly.

### 25/12/2022 - More consistent field names - Kaccana Bhikkhu:
§ Database.Questions field "Teacher" -> "Teachers"
 - This matches the corresponding fields in Database.Event and Database.Sessions
 - All lists now have plural names; dicts have singular names
 
 § Database.Event: "Event tags" -> "Tags",  Database.Sessions: "Session tags" -> "Tags"
  - These match Database.Questions field "Tags"; it's obvious from context what the tags apply to

### 27/12/2022 - Added "Location" subfield to Venues - Kaccana Bhikkhu

### 29/12/2022 - § Renamed database.json to Database.json
 - The convention is to use PascalCase for files, camelCase for directories

### 30/12/2022 - § Database.Sessions subfield renamed: "external mp3 URL" -> "Remote mp3 URL"

### 31/12/2022 - § Database.json forked to two versions:
 - Spreadsheet Database: prototype/SpreadsheetDatabase.json - dictionary keys match spreadsheet
 - Optimized Database: Database.json - camel dase dictionary keys for Javascript; extraneous fields deleted

### 1/1/2023 - § Renamed Database.Tag subfields based on Owen's suggestions:
 - "Alt. Trans." -> "Alternate Translations"
 - "See also" -> "Related"
