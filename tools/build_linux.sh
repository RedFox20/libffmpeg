#!/bin/bash

if [ ! -d "FFmpeg" ]; then
    git clone --branch release/8.0 --depth 1 https://github.com/FFmpeg/FFmpeg.git FFmpeg
fi

sudo apt-get install -y libx264-dev libx265-dev nasm libdrm-dev libbz2-dev

pushd FFmpeg

# Don't install to system, install to a local folder
DST=$PWD/../linux64
mkdir -p ${DST}

# msvc-x64
echo configure linux STATIC 64-bit
bash configure --prefix="${DST}" --disable-programs --enable-asm --disable-doc --disable-debug \
            --enable-gpl --enable-libx264 --enable-libx265

# Build and install
make -j$(nproc)
make install

popd
