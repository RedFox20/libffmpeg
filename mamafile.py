import os
import mama

##
# Explore Mama docs at https://github.com/RedFox20/Mama
#
class libffmpeg(mama.BuildTarget):

    workspace = 'build'

    def settings(self):
        # Literal so the artifactory shim can predict the archive name pre-clone. The `lgpl` arg
        # separates the two profiles via mama's variant suffix, so it must NOT be encoded here.
        self.version = '8.0.1'

    def dependencies(self):
        if not self.linux:
            self.nothing_to_build()

    def configure(self):
        pass

    def build(self):
        if self.linux:
            if not os.path.exists(self.build_dir('lib/libavcodec.a')):
                # Build x264/x265/FFmpeg with the SAME compiler and C++ runtime as the rest
                # of the build so the static libs (notably the C++ libx265) link into krattcam.
                # mama forces -stdlib=libc++ for clang, so a gcc/libstdc++ x265 won't link there.
                cc, cxx, _ = self.config.get_preferred_compiler_paths()
                stdlib = 'libc++' if self.config.clang else 'libstdc++'
                lgpl = ' --lgpl' if 'lgpl' in self.args else ''
                self.run(f'python3 ./tools/ffmpeg_build.py --platform linux'
                         f' --prefix "{self.build_dir()}" --cc "{cc}" --cxx "{cxx}"'
                         f' --stdlib "{stdlib}"{lgpl}', src_dir=True)

    def package(self):
        if self.imx8mp:
            self.export_include('imx8mp/include')
            self.export_libs('imx8mp/lib', ['.so'], src_dir=True, order=[
                'libavdevice', 'libavformat', 'libavfilter', 'libavcodec', 'libswresample', 'libswscale', 'libavutil'
            ])
            self.export_syslib('m', 'libm-dev')
            self.export_syslib('atomic', 'libatomic-dev')
            self.export_syslib('drm', 'libdrm-dev')
            self.export_syslib('lzma', 'liblzma-dev')
            self.export_syslib('bz2', 'libbz2-dev')
            self.export_syslib('z', 'libz-dev')
        elif self.linux:
            self.export_include('include', build_dir=True)
            self.export_libs('lib', ['.a'], build_dir=True, order=[
                'libavdevice', 'libavformat', 'libavfilter', 'libavcodec', 'libswresample', 'libswscale', 'libavutil'
            ])
            self.export_syslib('lzma', 'liblzma-dev')
            self.export_syslib('bz2', 'libbz2-dev')
            self.export_syslib('z', 'libz-dev')
            self.export_syslib('xcb-shm', 'libxcb-shm0-dev')     # X11: xcb-shm before xcb
            self.export_syslib('xcb', 'libxcb1-dev')
            self.export_syslib('Xv', 'libxv-dev')                 # Xv/Xext before X11
            self.export_syslib('Xext', 'libxext-dev')
            self.export_syslib('X11', 'libx11-dev')
            self.export_syslib('vdpau', 'libvdpau-dev')          # Video accel
            self.export_syslib('va-x11', 'libva-dev')            # VA-API: x11/drm before va
            self.export_syslib('va-drm', 'libva-drm2')
            self.export_syslib('va', 'libva-dev')
            self.export_syslib('drm', 'libdrm-dev')
            self.export_syslib('m', 'libm-dev')
            self.export_syslib('c')  # NOTE: current libffmpeg built with glibc: libc.so
        elif self.windows:
            if self.config.is_target_arch_x86():
                self.export_include('win32/include')
                self.export_libs('win32/bin', ['.lib','.dll'], src_dir=True)
            elif self.config.is_target_arch_x64():
                self.export_include('win64/include')
                self.export_libs('win64/bin', ['.lib','.dll'], src_dir=True)

