Automates my process of building Chromium:

On my online Windows machine:
- Downloads stable [version history](https://versionhistory.googleapis.com/v1/chrome/platforms/android/channels/stable/versions/all/releases)
- Downloads a source tarball
- Prepares a docker image that can build the tarball
- Copies the results to a USB drive

On my offline Linux machine:
- Builds chromium and produces apks and libchrome.so with symbols
- Creates idb files for libchrome.so
- Copies the results to a USB drive
- Deletes old build directories and old canary apks

Back on my online Windows machine:
- Copies the apks and idbs for storage
- Deletes old canary apks