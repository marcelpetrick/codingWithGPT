# minimalLvglProject

A minimal [LVGL v9](https://lvgl.io) desktop demo targeting x86 Linux (tested on Manjaro).  
Shows what the library looks like out of the box: gradient backgrounds, semi-transparent
glassmorphism card, accent-coloured buttons with glow shadows, a live status label, and a
styled slider — all in plain C with CMake.

## Purpose

Reference starting point for LVGL on a Linux desktop using the SDL2 backend.  
No cross-compiler, no embedded hardware required.  Useful for prototyping UIs before
flashing to a target.

## Dependencies

| Package | Arch / Manjaro |
|---------|---------------|
| CMake ≥ 3.20 | `sudo pacman -S cmake` |
| Ninja | `sudo pacman -S ninja` |
| SDL2 | `sudo pacman -S sdl2` |
| Git | `sudo pacman -S git` |
| C compiler | `sudo pacman -S base-devel` |

LVGL itself is fetched automatically by CMake (shallow clone, ~2 MB, one-time).

## Quick start — localPipeline.sh

```bash
bash localPipeline.sh
```

The script checks for missing packages, wipes and recreates the `build/` directory,
configures with Ninja, compiles, and launches the binary in one shot.  Use this when you
want a guaranteed clean state or after pulling changes.

## Incremental rebuild

After the first full build, skip the configure step and rebuild only changed files:

```bash
cmake --build build -- -j$(nproc)
./build/lvgl_demo
```

Or, if you only changed `main.c`:

```bash
cmake --build build --target lvgl_demo -- -j$(nproc)
./build/lvgl_demo
```

CMake/Ninja tracks dependencies automatically — only translation units that changed are
recompiled.  A single-file change typically rebuilds and links in under a second.

To force a full reconfigure (e.g. after editing `CMakeLists.txt` or `lv_conf.h`):

```bash
rm -rf build && bash localPipeline.sh
```

## Project layout

```
minimalLvglProject/
├── CMakeLists.txt      # FetchContent LVGL v9, SDL2, build target
├── lv_conf.h           # LVGL feature flags (SDL backend, fonts, widgets)
├── main.c              # UI source — everything in one file
└── localPipeline.sh    # One-shot dep-check + clean build + run
```

## License

GPLv3 — see [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

Author: Marcel Petrick — mail@marcelpetrick.it
