## Implemented in this repository

The repository now contains a reproducible Windows 11 cross-build setup:

- `cmake/toolchains/windows-mingw-qt5.cmake`
- `scripts/verify-windows-toolchain.sh`
- `scripts/deploy-windows.sh`
- `docs/windows-crosscompile.md`

Run the verifier from the project root:

```bash
./scripts/verify-windows-toolchain.sh
```

Current host verification result:

- Present: `cmake`, `ninja`, `wine`
- Missing: `x86_64-w64-mingw32-gcc`, `x86_64-w64-mingw32-g++`, `x86_64-w64-mingw32-windres`
- Missing: Windows-target Qt 5 MinGW prefix (`WINDOWS_QT_PREFIX` or `MXE_PREFIX`)

On this Manjaro/Arch-like host, the MinGW compiler can be installed with:

```bash
sudo pacman -S --needed mingw-w64-gcc mingw-w64-crt mingw-w64-headers
```

The Qt dependency must be a Windows-target Qt 5.15 build. A Linux Qt install is not enough. The recommended route is MXE:

```bash
export MXE_PREFIX=/opt/mxe
export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32.shared
export WINDOWS_MINGW_BIN=$MXE_PREFIX/usr/bin
```

For MXE, Windows Qt 5 is expected below:

```bash
$MXE_PREFIX/usr/$WINDOWS_MINGW_TRIPLET/qt5
```

Then rerun:

```bash
./scripts/verify-windows-toolchain.sh
```

Yes, possible: **Linux x86_64 → Windows 11 x86_64 Qt/C++ build**. The practical target is usually **Windows x86_64 MinGW**, not MSVC, because MSVC cross-compilation from Linux is not the normal route.

What to prepare:

1. **Windows cross toolchain**

   * `mingw-w64` for `x86_64-w64-mingw32`
   * CMake/Ninja or qmake
   * `wine` optional, for smoke-testing `.exe` on Linux

2. **Qt built for Windows, not Linux**

   * Your Linux Qt install cannot link a Windows executable.
   * You need Qt libraries compiled for target: **Windows x86_64 MinGW**.
   * Options:

     * use **MXE**, often easiest for Linux → Windows Qt builds
     * build Qt yourself with MinGW cross toolchain
     * build inside a Windows VM/CI instead, usually simpler long-term

3. **CMake toolchain file**
   Example shape:

```cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)

set(CMAKE_FIND_ROOT_PATH /opt/mxe/usr/x86_64-w64-mingw32)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

4. **Build command**
   Example:

```bash
cmake -B build-win -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=mingw-toolchain.cmake \
  -DCMAKE_PREFIX_PATH=/path/to/windows-qt/lib/cmake \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build-win
```

5. **Deployment**
   You must ship:

   * your `.exe`
   * Qt DLLs
   * MinGW runtime DLLs
   * Qt platform plugin, especially `platforms/qwindows.dll`
   * image plugins, TLS/OpenSSL DLLs, SQL drivers, QML modules if used

   Qt’s normal deployment helper is `windeployqt`, but it is a Windows-target tool, so with Linux cross builds you may need MXE packaging scripts, Wine, or manual collection. Qt documents `windeployqt` as the Windows deployment tool. ([Qt Documentation][1])

6. **Windows 11 notes**

   * No special “Windows 11 compiler mode” is usually needed.
   * Build a normal 64-bit Windows executable.
   * Test on a clean Windows 11 VM.
   * For GUI apps, check DPI scaling, dark mode behavior, fonts, TLS/networking, and code signing.

Best recommendation: **use Windows CI/VM if you can**. Cross-compiling Qt from Linux works, but deployment/testing is where time gets lost. If you must stay on Linux, use **MXE + MinGW-w64 + CMake/Ninja**.

[1]: https://doc.qt.io/qt-6/cross-compiling-qt.html?utm_source=chatgpt.com "Cross-compiling Qt | Qt 6.11"
