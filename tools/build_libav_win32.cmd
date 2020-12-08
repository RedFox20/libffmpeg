:: MSVC++
:: WARNING: THIS MUST BE RUN IN WINDOWS COMMAND PROMPT
:: You will need BASH and MAKE for Windows
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars32.bat"

:: Don't install to system, install to a local folder
set DST=%cd%/install_msvc_32
mkdir -p %DST%

:: msvc-x86
echo configure msvc x86
bash configure --target-os=win32 --toolchain=msvc --prefix="%DST%" ^
--enable-shared --disable-static ^
--enable-asm ^
--disable-doc

:: Build and install
make -j8
make install
