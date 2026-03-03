#!/bin/bash

if [ ! -d "FFmpeg-linux64" ]; then
    git clone --branch release/8.0 --depth 1 https://github.com/FFmpeg/FFmpeg.git FFmpeg-linux64
fi

sudo apt-get install -y libx264-dev libx265-dev nasm libdrm-dev libbz2-dev

# Don't install to system, install to a local folder
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
DST=$(realpath "${SCRIPT_DIR}/../linux64")
mkdir -p ${DST}

pushd FFmpeg-linux64

function logStatus() { # as green text
    echo -e "\033[32m$1\033[0m"
}
function logError() { # as red text
    echo -e "\033[31m$1\033[0m"
}

logStatus "Configure Linux 64-bit"
./configure --prefix="${DST}" \
    --disable-programs \
    --disable-doc \
    --disable-debug \
    --disable-static \
    --enable-shared \
    --enable-asm \
    --enable-gpl \
    --enable-nonfree \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libdrm

# Build and install
logStatus "Starting build..."
make -j$(nproc) || { logError "BUILD FAILED"; exit 1; }

logStatus "Installing to ${DST} ..."
make install
logStatus "Done."

popd

# delete all symlinks in the lib folder so we have cleaner packaging
find "${DST}/lib" -type l -delete

# rename .so.62.11.100 to .so.62 for correct linkage
# and .so.6.1.100 to .so.6 for correct linkage
for lib in "${DST}/lib/lib"*".so."*; do
    base=$(basename "$lib")
    if [[ $base =~ (lib.*\.so\.[0-9]+) ]]; then
        newname="${BASH_REMATCH[1]}"
        echo "Renaming $base to $newname"
        mv "$lib" "${DST}/lib/${newname}"
    fi
done
