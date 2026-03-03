#!/bin/bash
set -e

if [ ! -d "FFmpeg-imx8mp" ]; then
    git clone --branch release/8.0 --depth 1 https://github.com/FFmpeg/FFmpeg.git FFmpeg-imx8mp
fi

# Don't install to system, install to a local folder
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
DST=$(realpath "${SCRIPT_DIR}/../imx8mp")
mkdir -p ${DST}
echo "Installing to ${DST}"

pushd FFmpeg-imx8mp

(
    source /opt/imdt-imx-xwayland/5.0.4/environment-setup-cortexa53-crypto-poky-linux
    echo CC=$CC
    echo SDKTARGETSYSROOT=$SDKTARGETSYSROOT
    echo CFLAGS=$CFLAGS
    echo LDFLAGS=$LDFLAGS

    function logStatus() { # as green text
        echo -e "\033[32m$1\033[0m"
    }
    function logError() { # as red text
        echo -e "\033[31m$1\033[0m"
    }

    logStatus "Configure IMX Yocto ARMv8"
    # Use the CC/CXX/LD/AR/NM/STRIP variables set by the Yocto SDK environment
    # instead of --cross-prefix, which may not resolve to the correct tools
    ./configure \
        --enable-cross-compile \
        --cc="${CC}" \
        --cxx="${CXX}" \
        --ld="${CC}" \
        --ar="${AR}" \
        --nm="${NM}" \
        --strip="${STRIP}" \
        --sysroot="${SDKTARGETSYSROOT}" \
        --arch=aarch64 \
        --target-os=linux \
        --prefix="${DST}" \
        --disable-programs \
        --disable-doc \
        --disable-debug \
        --disable-static \
        --enable-shared \
        --enable-gpl \
        --enable-nonfree \
        --enable-v4l2-m2m \
        --enable-libdrm \
        --extra-cflags="${CFLAGS}" \
        --extra-ldflags="${LDFLAGS}" \
        --extra-libs="-lm -lpthread" \
        --pkg-config="pkg-config"

    # Build and install
    logStatus "Starting build..."
    make -j$(nproc) || { logError "BUILD FAILED"; exit 1; }

    logStatus "Installing to ${DST} ..."
    make install
    logStatus "Done."
)

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
