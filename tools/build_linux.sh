#!/bin/bash
set -e

function logStatus() { # as green text
    echo -e "\033[32m$1\033[0m"
}
function logError() { # as red text
    echo -e "\033[31m$1\033[0m"
}

DST=${1:-"linux64"}
DST=$(realpath "${DST}")
mkdir -p "${DST}" "${DST}/lib" "${DST}/include"

logStatus "Building inside: ${DST}"
#sudo apt-get install -y nasm libdrm-dev libbz2-dev cmake

###################################################
# Build x264 from source as a static library
###################################################
if [ ! -f "${DST}/lib/libx264.a" ]; then
    logStatus "Building x264 from source..."
    if [ ! -d "${DST}/x264" ]; then
        git clone --depth 1 https://code.videolan.org/videolan/x264.git "${DST}/x264"
    fi
    pushd "${DST}/x264"
    ./configure --prefix="${DST}" \
        --enable-static \
        --enable-pic \
        --disable-cli
    make -j$(nproc) 2>&1 || [ -f libx264.a ] || { logError "x264 build failed"; exit 1; }
    make install
    popd
fi

###################################################
# Build x265 from source as a static library
###################################################
if [ ! -f "${DST}/lib/libx265.a" ]; then
    logStatus "Building x265 from source..."
    if [ ! -d "${DST}/x265" ]; then
        git clone --depth 1 https://bitbucket.org/multicoreware/x265_git.git "${DST}/x265"
    fi
    pushd "${DST}/x265/build/linux"
    cmake ../../source \
        -DCMAKE_INSTALL_PREFIX="${DST}" \
        -DENABLE_SHARED=OFF \
        -DENABLE_CLI=OFF \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    make -j$(nproc)
    make install
    popd

    # x265 CMake doesn't always install a pkg-config file, so create one
    if [ ! -f "${DST}/lib/pkgconfig/x265.pc" ]; then
        mkdir -p "${DST}/lib/pkgconfig"
        cat > "${DST}/lib/pkgconfig/x265.pc" <<EOF
prefix=${DST}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: x265
Description: H.265/HEVC video encoder
Version: 0.0
Libs: -L\${libdir} -lx265 -lstdc++ -lm -lpthread -ldl
Libs.private: -lstdc++ -lm -lpthread -ldl
Cflags: -I\${includedir}
EOF
    fi
fi

###################################################
# Build FFmpeg with statically linked x264/x265
###################################################
if [ ! -d "${DST}/FFmpeg-linux64" ]; then
    git clone --branch release/8.0 --depth 1 https://github.com/FFmpeg/FFmpeg.git "${DST}/FFmpeg-linux64"
fi

pushd "${DST}/FFmpeg-linux64"

logStatus "Configure Linux 64-bit"
export PKG_CONFIG_PATH="${DST}/lib/pkgconfig:${PKG_CONFIG_PATH}"
./configure --prefix="${DST}" \
    --disable-programs \
    --disable-doc \
    --disable-debug \
    --enable-static \
    --disable-shared \
    --enable-asm \
    --enable-gpl \
    --enable-nonfree \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libdrm \
    --extra-cflags="-I${DST}/include" \
    --extra-ldflags="-L${DST}/lib"

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
