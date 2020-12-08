#!/bin/bash

# Don't install to system, install to a local folder
DST=$PWD/install_linux
mkdir -p ${DST}

# msvc-x64
echo configure linux 64-bit
bash configure --prefix="${DST}" --enable-shared --disable-static --enable-asm --disable-doc 

# Build and install
make -j8
make install

