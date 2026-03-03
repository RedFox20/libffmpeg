import mama

##
# Explore Mama docs at https://github.com/RedFox20/Mama
#
class libffmpeg(mama.BuildTarget):

    workspace = 'build'

    def dependencies(self):
        self.nothing_to_build()

    def configure(self):
        pass

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
            self.export_include('linux64/include')
            self.export_libs('linux64/lib', ['.a'], src_dir=True, order=[
                'libavdevice', 'libavformat', 'libavfilter', 'libavcodec', 'libswresample', 'libswscale', 'libavutil'
            ])
            self.export_syslib('lzma', 'liblzma-dev')
            self.export_syslib('bz2', 'libbz2-dev')
            self.export_syslib('X11', 'libx11-dev')
            self.export_syslib('vdpau', 'libvdpau-dev')
            self.export_syslib('va', 'libva-dev')
            self.export_syslib('va-drm', 'libva-drm2')
            self.export_syslib('va-x11', 'libva-dev')
            self.export_syslib('drm', 'libdrm-dev')
            self.export_syslib('c')  # NOTE: current libffmpeg built with glibc: libc.so
        elif self.windows:
            if self.config.is_target_arch_x86():
                self.export_include('win32/include')
                self.export_libs('win32/bin', ['.lib','.dll'], src_dir=True)
            elif self.config.is_target_arch_x64():
                self.export_include('win64/include')
                self.export_libs('win64/bin', ['.lib','.dll'], src_dir=True)

