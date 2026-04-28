# Windows 11 Cross-Build Toolchain

This project can be cross-built on Linux as a 64-bit Windows 11 application with MinGW-w64 and Qt 5.15 libraries built for Windows.

The important constraint is that the host Linux Qt package cannot produce a Windows executable. CMake must find a Windows-target Qt 5 prefix that was built with the same MinGW triplet used by the compiler.

## Supported Layouts

### MXE

MXE is the most practical all-in-one route because it builds both MinGW-w64 and Windows Qt from Linux.

Expected environment:

```sh
export MXE_PREFIX=/opt/mxe
export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32.shared
export WINDOWS_MINGW_BIN=$MXE_PREFIX/usr/bin
```

The script then expects Qt here:

```text
$MXE_PREFIX/usr/$WINDOWS_MINGW_TRIPLET/lib/cmake/Qt5/Qt5Config.cmake
```

### Custom Windows Qt Prefix

Use this when Qt 5.15 was cross-built manually or unpacked into a known prefix:

```sh
export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32
export WINDOWS_QT_PREFIX=/opt/qt-windows-5.15/x86_64-w64-mingw32
```

The prefix must contain:

```text
lib/cmake/Qt5/Qt5Config.cmake
lib/cmake/Qt5Widgets/Qt5WidgetsConfig.cmake
lib/cmake/Qt5PrintSupport/Qt5PrintSupportConfig.cmake
lib/cmake/Qt5Network/Qt5NetworkConfig.cmake
plugins/platforms/qwindows.dll
```

## Verify

Run:

```sh
./scripts/verify-windows-toolchain.sh
```

The verifier checks:

- CMake and Ninja.
- `${WINDOWS_MINGW_TRIPLET}-gcc`, `g++`, and `windres`.
- Windows-target Qt 5 CMake package files.
- Windows build with the CMake toolchain file.
- Deployment bundle with the application executable, Qt DLLs, MinGW runtime DLLs, and `platforms/qwindows.dll`.
- Optional Wine smoke invocation when Wine is installed.

## Manual Build

```sh
cmake -S . -B build-win -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/windows-mingw-qt5.cmake \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build-win
```

## Deploy

```sh
./scripts/deploy-windows.sh build-win dist/windows
```

Copy `dist/windows` to a Windows 11 machine and run:

```bat
QtPrinterFinderExample.exe
```

For a release-quality package, test on a clean Windows 11 VM without Qt installed. That catches missing DLLs and plugin dependencies that can be hidden on a developer machine.
