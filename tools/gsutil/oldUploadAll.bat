Q:
cd \qs-archive

echo "Before first command"

"Q:\Programs\Google Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe" "Q:\Programs\Google Cloud SDK\google-cloud-sdk\platform\gsutil\gsutil.py" -m rsync -r -d audio/excerpts gs://apqs_archive/audio/excerpts

echo "Finished first command"

"Q:\Programs\Google Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe" "Q:\Programs\Google Cloud SDK\google-cloud-sdk\platform\gsutil\gsutil.py" -m rsync -r -d -x ".*json$" prototype gs://apqs_archive/prototype

echo "Finished second command"