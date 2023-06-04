#!/bin/bash

set -xueEo pipefail

apt-get update
apt-get install -y lsb-release sudo curl git
git config --global --add safe.directory '*'

#
# Install depot_tools if needed
#

cd /home
if [ ! -d "/home/depot_tools" ]; then
	git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
fi
export PATH=$PATH:/home/depot_tools

#
# Checkout chromium and save it to /home/chrome/$VERSION/chromium.tgz
#

if [ ! -d "/home/chromium/src" ]; then
	mkdir chromium
	cd chromium
	fetch --nohooks android
	cd /home
fi

cd /home/chromium/src
git fetch --tags
git checkout $VERSION
gclient sync -D --with_tags --with_branch_heads

cd /home
mkdir -p chrome/$VERSION
tar czf chrome/$VERSION/chromium.tgz --exclude=.git chromium
tar czf chrome/$VERSION/depot_tools.tgz --exclude=.git depot_tools

#
# Install dependencies
#

# Installing snapcraft pauses for user input, but it's not required
cat - > /etc/apt/preferences.d/ban_snapcraft <<EOF
Package: snapcraft
Pin: release *
Pin-Priority: -1
EOF

# Installing tzdata pauses for the user to select the timezone
# From: https://stackoverflow.com/questions/44331836/apt-get-install-tzdata-noninteractive
echo 'tzdata tzdata/Areas select America' | debconf-set-selections
echo 'tzdata tzdata/Zones/America select New_York' | debconf-set-selections
DEBIAN_FRONTEND="noninteractive" apt-get install -y tzdata

cd /home/chromium/src
MAJOR=$(echo $VERSION | cut -d '.' -f 1)
if [ $MAJOR -le 110 ]; then
	./build/install-build-deps-android.sh --no-chromeos-fonts
else
	./build/install-build-deps.sh --android --no-chromeos-fonts
fi

# I don't think these are loaded when the entrypoint isn't bash
# echo "export VERSION=$VERSION" >> /root/.bashrc
# echo 'export PATH=$PATH:/home/chrome/$VERSION/depot_tools' >> /root/.bashrc
