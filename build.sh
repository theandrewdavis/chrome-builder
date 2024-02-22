#!/bin/bash

set -xeuEo pipefail

cd /home
tar xzf chromium.tgz
tar xzf depot_tools.tgz
if [ -f vpython_root.tgz ]; then
	tar xzf vpython_root.tgz
fi
cd chromium/src

export PATH=$PATH:/home/depot_tools
export VPYTHON_VIRTUALENV_ROOT=/home/.vpython-root

mkdir -p out/arm64
cat - > out/arm64/args.gn <<EOF
target_os="android"
target_cpu="arm64"
is_debug=false
is_official_build=true
symbol_level=1
is_component_build=false
disable_fieldtrial_testing_config=true
chrome_pgo_phase=0
EOF
gn gen out/arm64
autoninja -C out/arm64 chrome_public_apk monochrome_public_apk monochrome_64_public_apk trichrome_library_32_apk trichrome_chrome_32_bundle trichrome_library_64_apk trichrome_chrome_64_bundle

# could do this before 'gn gen' to try to get object sizes
# git apply /home/tools/add_cflags.patch

mkdir -p /home/save
cp out/arm64/apks/*.apk /home/save/
mv /home/save/ChromePublic{,64}.apk
cp out/arm64/android_clang_arm/lib.unstripped/libmonochrome.so /home/save/libmonochrome32.so
cp out/arm64/lib.unstripped/libmonochrome_64.so /home/save/libmonochrome64.so
out/arm64/bin/trichrome_chrome_32_bundle build-bundle-apks --output-apks=/home/save/TrichromeChrome32.apks
unzip -d /home/save/org.chromium.chrome_32 /home/save/TrichromeChrome32.apks
out/arm64/bin/trichrome_chrome_64_bundle build-bundle-apks --output-apks=/home/save/TrichromeChrome64.apks
unzip -d /home/save/org.chromium.chrome_64 /home/save/TrichromeChrome64.apks

# Only needed for ChromePublic32 on Android 6 (removed sometime before 109)

# cat - > out/arm/args.gn <<EOF
# target_os="android"
# is_debug=false
# is_official_build=true
# symbol_level=1
# is_component_build=false
# disable_fieldtrial_testing_config=true
# EOF
# git apply /home/tools/add_cflags.patch
# gn gen out/arm
# autoninja -C out/arm chrome_public_apk
# cp out/arm/apks/ChromePublic.apk /home/save/ChromePublic32.apk
