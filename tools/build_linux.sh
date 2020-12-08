#!/bin/bash

# Don't install to system, install to a local folder
DST=$PWD/install_linux
mkdir -p ${DST}

# msvc-x64
echo configure linux STATIC 64-bit
bash configure --prefix="${DST}" --disable-programs --enable-asm --disable-doc --disable-debug

# Build and install
make -j8
make install

