import mama

##
# Explore Mama docs at https://github.com/RedFox20/Mama
#
class libav(mama.BuildTarget):

    workspace = 'build'

    def dependencies(self):
        self.nothing_to_build()

    def configure(self):
        pass

    def package(self):
        if self.linux:
            self.export_include('linux64/include')
            self.export_libs('linux64/lib', ['.a'], src_dir=True)
        elif self.windows:
            if self.config.is_target_arch_x86():
                self.export_include('win32/include')
                self.export_libs('win32/bin', ['.lib','.dll'], src_dir=True)
            elif self.config.is_target_arch_x64():
                self.export_include('win64/include')
                self.export_libs('win64/bin', ['.lib','.dll'], src_dir=True)

