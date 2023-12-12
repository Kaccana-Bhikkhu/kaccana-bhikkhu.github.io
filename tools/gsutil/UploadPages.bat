Q:
cd \qs-archive

call gsutil -m rsync -r -d -x ".*json$" pages gs://apqs_archive/pages

call gsutil cp "index.html" gs://apqs_archive
