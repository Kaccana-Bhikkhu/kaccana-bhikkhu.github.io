Q:
cd \qs-archive

echo Before first command

call gsutil -m rsync -r -d audio/excerpts gs://apqs_archive/audio/excerpts

echo Finished first command

call gsutil -m rsync -r -d -x ".*json$" pages gs://apqs_archive/pages

echo Finished second command

call gsutil cp "index.html" gs://apqs_archive

echo Finished third command