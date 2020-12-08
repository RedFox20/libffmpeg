:: MSVC++
:: WARNING: THIS MUST BE RUN IN WINDOWS COMMAND PROMPT
:: You will need BASH and MAKE for Windows
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"

:: Don't install to system, install to a local folder
set DST=%cd%/install_msvc_64
mkdir -p %DST%

:: msvc-x64
echo configure msvc x64
bash configure --target-os=win64 --arch=x86_64 --toolchain=msvc --prefix="%DST%" ^
--enable-shared --disable-static ^
--enable-asm ^
--disable-doc 

:: Build and install
make -j8
make install
