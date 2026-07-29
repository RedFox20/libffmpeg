#!/usr/bin/env python3
"""Build FFmpeg from source into a mama build dir, for linux, windows or imx8mp.

FFmpeg's configure generates config.h and libavutil/avconfig.h per target, so headers from one
platform are unusable on another. Every backend therefore installs into its own --prefix, which
mama already keeps per platform.

Two license profiles. The default is the full GPL build krattcam and opencv have always used.
--lgpl drops x264/x265 and enables hardware decode instead: KrattGCS only ever decodes (native
LGPL h264/hevc) and encodes MJPEG, so GPL would buy it nothing and constrain redistribution.

  ffmpeg_build.py --platform linux --prefix <dir> [--cc gcc] [--cxx g++]
                  [--stdlib libstdc++|libc++] [--lgpl] [--sdk <yocto env-setup>] [--jobs N]
"""
import argparse, os, re, shutil, subprocess, sys
from pathlib import Path

X264_URL = 'https://code.videolan.org/videolan/x264.git'
X265_URL = 'https://bitbucket.org/multicoreware/x265_git.git'
FFMPEG_URL = 'https://github.com/FFmpeg/FFmpeg.git'
FFMPEG_BRANCH = 'release/8.0'

# FFmpeg's configure gate is `x265 >= 68`, so a synthesized .pc must never fall below it.
X265_BUILD_FALLBACK = 68


def log(msg): print(f'\033[32m{msg}\033[0m', flush=True)
def err(msg): print(f'\033[31m{msg}\033[0m', file=sys.stderr, flush=True)


def run(cmd, cwd=None, env=None, shell=False):
    """Run a build step, aborting the whole script on failure - a half-built FFmpeg is not usable."""
    status = subprocess.run(cmd, cwd=cwd, env=env, shell=shell).returncode
    if status != 0:
        err(f'FAILED ({status}): {cmd if shell else " ".join(map(str, cmd))}')
        sys.exit(status)


def shallow_clone(url, dst: Path, branch=None):
    if (dst / '.git').exists(): return
    log(f'Cloning {url} -> {dst}')
    cmd = ['git', 'clone', '-q', '--depth', '1']
    if branch: cmd += ['--branch', branch]
    run(cmd + [url, str(dst)])


def cxx_runtime(stdlib: str):
    """(-stdlib flag, C++ runtime libs). x265 is C++, so FFmpeg's link test needs the SAME runtime
    the rest of the build uses or detection fails with 'x265 not found using pkg-config'."""
    if stdlib == 'libc++': return '-stdlib=libc++', '-lc++ -lc++abi'
    return '', '-lstdc++'


def build_x264(prefix: Path, cc: str, jobs: int):
    if (prefix / 'lib/libx264.a').exists(): return
    src = prefix / 'x264'
    shallow_clone(X264_URL, src)
    log('Building x264')
    env = {**os.environ, 'CC': cc}
    run(['./configure', f'--prefix={prefix}', '--enable-static', '--enable-pic', '--disable-cli'],
        cwd=src, env=env)
    run(['make', f'-j{jobs}'], cwd=src, env=env)
    run(['make', 'install'], cwd=src, env=env)


def build_x265(prefix: Path, cc: str, cxx: str, stdlib_flag: str, jobs: int):
    if (prefix / 'lib/libx265.a').exists(): return
    src = prefix / 'x265'
    shallow_clone(X265_URL, src)
    log('Building x265')
    build = src / 'build/linux'
    # ENABLE_LIBNUMA=OFF: x265 auto-links libnuma when libnuma-dev is present, leaving numa_* refs
    # the downstream krattcam link does not provide.
    run(['cmake', '../../source', f'-DCMAKE_INSTALL_PREFIX={prefix}',
         f'-DCMAKE_C_COMPILER={cc}', f'-DCMAKE_CXX_COMPILER={cxx}',
         f'-DCMAKE_CXX_FLAGS={stdlib_flag}', '-DENABLE_SHARED=OFF', '-DENABLE_CLI=OFF',
         '-DENABLE_LIBNUMA=OFF', '-DCMAKE_POSITION_INDEPENDENT_CODE=ON'], cwd=build)
    run(['make', f'-j{jobs}'], cwd=build)
    run(['make', 'install'], cwd=build)


def write_x265_pc(prefix: Path, runtime_libs: str):
    """x265's CMake often installs no pkg-config file. Outside the build guard so deleting a stale
    .pc regenerates it without rebuilding x265. The Version must be the real X265_BUILD number."""
    pc = prefix / 'lib/pkgconfig/x265.pc'
    if not (prefix / 'lib/libx265.a').exists() or pc.exists(): return
    build_no = X265_BUILD_FALLBACK
    for header in ('include/x265_config.h', 'include/x265.h'):
        try: text = (prefix / header).read_text(errors='replace')
        except OSError: continue
        m = re.search(r'#define\s+X265_BUILD\s+(\d+)', text)
        if m: build_no = int(m.group(1)); break
    pc.parent.mkdir(parents=True, exist_ok=True)
    pc.write_text(f'''prefix={prefix}
exec_prefix=${{prefix}}
libdir=${{exec_prefix}}/lib
includedir=${{prefix}}/include

Name: x265
Description: H.265/HEVC video encoder
Version: {build_no}
Libs: -L${{libdir}} -lx265 {runtime_libs} -lm -lpthread -ldl
Libs.private: {runtime_libs} -lm -lpthread -ldl
Cflags: -I${{includedir}}
''')


def ffmpeg_flags(args, prefix: Path, stdlib_flag: str) -> list:
    """configure flags shared by every backend, plus the profile and platform specific ones."""
    flags = ['--disable-programs', '--disable-doc', '--disable-debug',
             '--enable-static', '--disable-shared', '--enable-asm']
    if args.platform != 'windows':
        flags += ['--disable-sndio', '--disable-alsa', f'--cc={args.cc}', f'--cxx={args.cxx}']

    if args.lgpl:
        # No x264/x265: KrattGCS decodes only and encodes MJPEG, both native LGPL. Decode speed
        # comes from the hardware paths below, which are all LGPL-compatible.
        flags += ['--enable-version3']
        if args.platform == 'windows': flags += ['--enable-d3d11va', '--enable-dxva2']
        else:                          flags += ['--enable-vaapi', '--enable-vdpau', '--enable-libdrm']
    else:
        flags += ['--enable-gpl', '--enable-nonfree', '--enable-libx264', '--enable-libx265',
                  '--enable-libdrm']

    flags += [f'--extra-cflags=-I{prefix}/include',
              f'--extra-ldflags=-L{prefix}/lib {stdlib_flag}'.rstrip()]
    return flags


def normalize_libs(prefix: Path):
    """Drop symlinks and shorten libfoo.so.62.11.100 to libfoo.so.62, which is what links."""
    lib = prefix / 'lib'
    if not lib.is_dir(): return
    for path in lib.iterdir():
        if path.is_symlink(): path.unlink()
    for path in lib.glob('lib*.so.*'):
        m = re.match(r'(lib.*\.so\.\d+)', path.name)
        if m and m.group(1) != path.name:
            print(f'Renaming {path.name} to {m.group(1)}')
            path.replace(lib / m.group(1))


def build_linux(args, prefix: Path):
    stdlib_flag, runtime_libs = cxx_runtime(args.stdlib)
    log(f'Building in {prefix} (cc={args.cc} cxx={args.cxx} stdlib={args.stdlib} '
        f'profile={"lgpl" if args.lgpl else "full"})')
    if not args.lgpl:
        build_x264(prefix, args.cc, args.jobs)
        build_x265(prefix, args.cc, args.cxx, stdlib_flag, args.jobs)
        write_x265_pc(prefix, runtime_libs)

    src = Path(args.src) if args.src else prefix / 'FFmpeg'
    shallow_clone(FFMPEG_URL, src, FFMPEG_BRANCH)

    env = {**os.environ, 'TERM': 'dumb',  # TERM=dumb: configure's progress output breaks CI logs
           'PKG_CONFIG_PATH': f'{prefix}/lib/pkgconfig:{os.environ.get("PKG_CONFIG_PATH", "")}'}
    log('Configuring FFmpeg')
    run(['./configure', f'--prefix={prefix}'] + ffmpeg_flags(args, prefix, stdlib_flag), cwd=src, env=env)
    log('Building FFmpeg')
    run(['make', f'-j{args.jobs}'], cwd=src, env=env)
    log(f'Installing to {prefix}')
    run(['make', 'install'], cwd=src, env=env)
    normalize_libs(prefix)
    log('Done.')


def main():
    p = argparse.ArgumentParser(description='Build FFmpeg from source into a mama build dir')
    p.add_argument('--platform', required=True, choices=['linux', 'windows', 'imx8mp'])
    p.add_argument('--prefix', required=True, help='install prefix, normally the mama build dir')
    p.add_argument('--src', help='existing FFmpeg source dir; cloned under --prefix when omitted')
    p.add_argument('--cc', default='gcc')
    p.add_argument('--cxx', default='g++')
    p.add_argument('--stdlib', default='libstdc++', choices=['libstdc++', 'libc++'])
    p.add_argument('--lgpl', action='store_true', help='LGPLv3 decode profile, no x264/x265')
    p.add_argument('--sdk', help='imx8mp: Yocto environment-setup script')
    p.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    args = p.parse_args()

    prefix = Path(args.prefix).resolve()
    for sub in ('', 'lib', 'include'): (prefix / sub).mkdir(parents=True, exist_ok=True)

    if args.platform == 'linux':
        build_linux(args, prefix)
    else:
        err(f'--platform {args.platform} is not implemented yet (phase 2/4 of the unification plan)')
        sys.exit(2)


if __name__ == '__main__':
    main()
