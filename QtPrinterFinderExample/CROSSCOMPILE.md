# Cross-Compile Windows 11 App From Manjaro Linux

This project can be built on Manjaro Linux as a 64-bit Windows 11 executable using MinGW-w64 and a Windows-target Qt 5 build.

Important: the normal Manjaro/Linux Qt package cannot link a Windows `.exe`. You need Qt libraries that were built for Windows MinGW.

## 1. Install Host Tools

On Manjaro:

```sh
sudo pacman -S --needed base-devel git cmake ninja mingw-w64-gcc mingw-w64-crt mingw-w64-headers wine
```

These provide:

- `cmake` and `ninja` for configuring/building.
- `x86_64-w64-mingw32-gcc`, `g++`, and `windres` for Windows builds.
- `wine` for optional smoke testing on Linux.

## 2. Install Windows Qt 5

Recommended route: MXE. It builds a Windows MinGW Qt prefix on Linux.

One typical setup:

```sh
sudo mkdir -p /opt/mxe
sudo chown "$USER:$USER" /opt/mxe
git clone https://github.com/mxe/mxe.git /opt/mxe
cd /opt/mxe
make MXE_TARGETS=x86_64-w64-mingw32.shared qtbase
```

This can take a while. `qtbase` is the important Qt part for this app because it contains the Qt modules used here: Widgets, PrintSupport, Network, and Concurrent.

## 3. Export Build Environment

For MXE:

```sh
export MXE_PREFIX=/opt/mxe
export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32.shared
export WINDOWS_MINGW_BIN=$MXE_PREFIX/usr/bin
```

With MXE, the Windows Qt 5 prefix is:

```text
$MXE_PREFIX/usr/$WINDOWS_MINGW_TRIPLET/qt5
```

If you built or unpacked Windows Qt somewhere else, use:

```sh
export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32
export WINDOWS_QT_PREFIX=/path/to/windows/qt5/mingw/prefix
```

The Qt prefix must contain:

```text
lib/cmake/Qt5/Qt5Config.cmake
lib/cmake/Qt5Widgets/Qt5WidgetsConfig.cmake
lib/cmake/Qt5PrintSupport/Qt5PrintSupportConfig.cmake
lib/cmake/Qt5Network/Qt5NetworkConfig.cmake
plugins/platforms/qwindows.dll
```

## 4. Verify Toolchain

From this repository:

```sh
./scripts/verify-windows-toolchain.sh
```

The script checks the compiler, Qt prefix, configures CMake, builds the `.exe`, creates a deployment folder, and optionally runs a Wine smoke command.

## 5. Manual Build

If you want to run the steps manually:

```sh
cmake -S . -B build-win -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/windows-mingw-qt5.cmake \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build-win
```

The executable should be:

```text
build-win/QtPrinterFinderExample.exe
```

## 6. Deploy

Create a Windows deployment folder:

```sh
./scripts/deploy-windows.sh build-win dist/windows
```

Copy this folder to Windows 11:

```text
dist/windows
```

It should contain:

- `QtPrinterFinderExample.exe`
- Qt DLLs
- MinGW runtime DLLs
- `platforms/qwindows.dll`

Run on Windows:

```bat
QtPrinterFinderExample.exe
```

## 7. Current Host Status

When last checked on this host:

- Present: `cmake`, `ninja`, `wine`
- Missing: MinGW-w64 compiler commands
- Missing: Windows-target Qt 5 prefix

So the next required actions are:

```sh
sudo pacman -S --needed base-devel git cmake ninja mingw-w64-gcc mingw-w64-crt mingw-w64-headers wine
```

Then install/build MXE Qt and rerun:

```sh
./scripts/verify-windows-toolchain.sh
```

## 8. Free Disk Space

The MXE checkout and build tree can become large. On this host `/opt/mxe` was about `1.5G` after the first setup attempt.

To remove MXE completely:

```sh
sudo rm -rf /opt/mxe
```

This is safe for the repository because `/opt/mxe` is external generated toolchain state. Removing it means the Windows cross-toolchain and Windows Qt build must be recreated later:

```sh
sudo ./setup-windows-toolchain.sh
```

If you want to keep the MXE checkout but remove downloaded packages and logs:

```sh
rm -rf /opt/mxe/pkg /opt/mxe/log
```

On this host that smaller cleanup was about `137M`.

Project-local generated directories are also safe to delete when present:

```sh
rm -rf build build-win dist
```

Those directories contain local Linux builds, Windows cross-build output, and deployment bundles. They can be regenerated with the normal build or verification commands.
