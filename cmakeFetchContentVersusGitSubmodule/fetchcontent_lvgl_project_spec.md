# Project Vision and Requirements: CMake `FetchContent` + Minimal LVGL Demo

## 1. Vision

Create a **small, modern CMake-based C++ repository hosted on GitHub** that demonstrates one idea as clearly as possible:

> A CMake project can fetch, configure, build, and update a Git dependency with `FetchContent` without using Git submodules.

Use **LVGL** as the real external dependency and build a tiny desktop application that opens a window and displays one centered label such as **`Hello LVGL`**.

The visible application is only proof that LVGL was not merely downloaded: it was configured, compiled, linked, and used successfully.

The repository is a teaching/showcase project. Optimize for:

1. **Clarity** — the important CMake mechanism is immediately visible.
2. **Minimalism** — the GUI is intentionally tiny.
3. **Proof** — local execution and GitHub Actions both prove the mechanism works.
4. **No submodules** — CMake owns dependency acquisition for this example.
5. **Update behavior** — changing the requested LVGL revision and rerunning CMake configure is a first-class use case.

This project is **not** intended to be:

- a production LVGL application architecture;
- an embedded-board port;
- an LVGL feature showcase;
- a package-manager comparison;
- an SDL tutorial;
- an example of vendoring third-party code;
- an argument that `FetchContent` is universally better than Git submodules.

Git submodules remain valid when Git should own an external checkout in the source tree. This repository intentionally demonstrates the alternative model: **CMake owns a build dependency in the build tree**.

---

## 2. Core behavior to demonstrate

The normal flow must be:

```text
git clone
    ↓
cmake configure
    ↓
CMake FetchContent obtains LVGL into build/_deps
    ↓
cmake build
    ↓
run a tiny LVGL desktop window
```

The update flow must also be demonstrated:

```text
change LVGL_GIT_TAG
    ↓
rerun cmake configure in the SAME build directory
    ↓
FetchContent updates/switches the LVGL checkout
    ↓
no git submodule command is involved
```

The dependency-management story must remain the obvious focus of the repository.

---

## 3. Repository requirements

The result must be a normal GitHub repository.

Requirements:

- **Do not use Git submodules.**
- Do not create `.gitmodules`.
- Do not vendor or copy LVGL into the repository.
- Do not create a checked-in `third_party/lvgl`, `vendor/lvgl`, or equivalent source directory.
- A fresh clone must work with a normal command:

  ```bash
  git clone <repository-url>
  ```

- It must not require:

  ```bash
  git clone --recursive
  git submodule update --init --recursive
  ```

- Generated build output, including `build/_deps/`, must be excluded through `.gitignore`.

Keep the repository intentionally small, approximately:

```text
cmake-fetchcontent-lvgl-demo/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── CMakeLists.txt
├── README.md
├── lv_conf.h
└── src/
    └── main.cpp
```

Do not introduce extra CMake modules, helper frameworks, package managers, or directory layers unless they are technically necessary.

---

## 4. CMake requirements

### 4.1 General

Use a reasonably modern CMake baseline, preferably **CMake 3.28 or newer**.

Use target-based CMake and enable both C and C++ because LVGL is primarily C while the demonstration executable is C++.

Use at least C++17.

Prefer Ninja in documentation and CI, but do not make the project fundamentally dependent on Ninja.

The top-level file should conceptually start like this:

```cmake
cmake_minimum_required(VERSION 3.28)
project(cmake_fetchcontent_lvgl_demo LANGUAGES C CXX)
```

### 4.2 LVGL must be acquired with plain CMake `FetchContent`

Use CMake's built-in module:

```cmake
include(FetchContent)
```

Declare LVGL directly from its official GitHub repository:

```cmake
FetchContent_Declare(
    lvgl
    GIT_REPOSITORY https://github.com/lvgl/lvgl.git
    GIT_TAG        ${LVGL_GIT_TAG}
    GIT_PROGRESS   TRUE
)
```

Make the requested revision visible in configure output and then make the dependency available:

```cmake
message(STATUS "LVGL FetchContent revision: ${LVGL_GIT_TAG}")
FetchContent_MakeAvailable(lvgl)
```

Do not use:

- Git submodules;
- `ExternalProject_Add()`;
- `execute_process()` to clone, fetch, checkout, or update LVGL;
- Conan;
- vcpkg;
- CPM.cmake;
- Hunter;
- a custom shell or Python dependency script.

The purpose is specifically to demonstrate **plain CMake `FetchContent`**.

### 4.3 LVGL revision selection

Use a clearly visible variable immediately near the dependency declaration.

Default to a stable, human-readable LVGL release tag, for example:

```cmake
if(NOT DEFINED LVGL_GIT_TAG)
    set(LVGL_GIT_TAG "v9.5.0")
endif()
```

This structure is intentional:

- the default tag is easy to see and edit in `CMakeLists.txt`;
- `-DLVGL_GIT_TAG=...` can override it from the command line;
- a command-line override stays in the CMake cache until changed or removed.

Do not track `master`, `main`, or another moving branch by default.

For this teaching project, a release tag is preferred over a raw commit hash because switching between releases is part of the demonstration. The README should note that production projects requiring stronger reproducibility may prefer an exact commit hash.

Do not enable `FETCHCONTENT_FULLY_DISCONNECTED` or `FETCHCONTENT_UPDATES_DISCONNECTED`, because update behavior is part of the showcase.

Do not use `GIT_SHALLOW TRUE` in this showcase. A normal checkout keeps switching between demonstration tags straightforward.

### 4.4 Make the FetchContent section visually obvious

The most important section in `CMakeLists.txt` must be easy to spot immediately.

Use concise section comments such as:

```cmake
# -----------------------------------------------------------------------------
# Dependency: LVGL via CMake FetchContent
# -----------------------------------------------------------------------------
# No Git submodule is used. CMake owns the checkout under build/_deps.
# Change LVGL_GIT_TAG and rerun configure to switch the dependency revision.
```

Comments should explain **why** the code exists, not narrate every command.

The complete top-level `CMakeLists.txt` should remain short enough to understand in a few minutes.

A good structure is:

```text
Project setup
Host dependency: SDL2
Dependency: LVGL via FetchContent
Application target
```

Do not hide `FetchContent_Declare()` in another `.cmake` file.

### 4.5 LVGL configuration

Commit a local `lv_conf.h` for the demo.

For the pinned LVGL release, configure LVGL through the upstream CMake mechanism intended for supplying the configuration file, for example `LV_BUILD_CONF_PATH`, before `FetchContent_MakeAvailable(lvgl)` if that is the correct interface for the selected release.

Disable unnecessary LVGL extras, especially upstream examples and demos, where practical.

Enable only what is necessary for the minimal SDL-backed desktop application.

Keep the configuration explicit and readable. Avoid copying a huge configuration file full of unrelated options if a smaller valid configuration is possible.

### 4.6 Link through upstream CMake targets

The application must link to LVGL through the target supplied by LVGL, for example:

```cmake
target_link_libraries(<demo-target> PRIVATE lvgl::lvgl)
```

Use the exact target names exported by the selected LVGL release.

Do not glob LVGL sources manually.

Do not hard-code LVGL include paths when the upstream CMake target already publishes them.

---

## 5. Minimal LVGL desktop application

This must be more than a compile-only demonstration. Running the executable locally must visibly prove that LVGL works.

Use LVGL's supported SDL desktop integration for the selected LVGL release together with the system SDL2 development package.

The application should do only the following:

1. initialize LVGL;
2. create a small desktop display/window, for example 480×320;
3. create one LVGL label on the active screen;
4. set the text to something obvious such as `Hello LVGL`;
5. center the label;
6. run the normal LVGL timer/event loop until the window is closed.

Conceptually, the interesting part of the program should remain close to:

```cpp
lv_init();

lv_display_t* display = lv_sdl_window_create(480, 320);
(void)display;

lv_obj_t* label = lv_label_create(lv_screen_active());
lv_label_set_text(label, "Hello LVGL");
lv_obj_center(label);
```

Use the exact API that is valid for the pinned LVGL version.

Do not use LVGL's large demo applications. Do not add buttons, animations, images, themes, menus, input logic, multiple screens, or business logic unless something is strictly required for the window to function.

The visual result should be intentionally boring: **one window, one centered label**.

---

## 6. SDL requirement

SDL exists only as the host/display backend for the demo. It is **not** the dependency-management concept being showcased.

Therefore:

- obtain LVGL with `FetchContent`;
- use the system SDL2 development package through normal CMake discovery;
- do not add another `FetchContent` dependency merely to fetch SDL unless absolutely necessary;
- document the SDL2 development package as a host prerequisite.

For Ubuntu and GitHub Actions, installation may use:

```bash
sudo apt-get update
sudo apt-get install -y libsdl2-dev ninja-build
```

Keep all SDL-specific CMake logic minimal.

---

## 7. GitHub Actions requirements

Create:

```text
.github/workflows/ci.yml
```

Trigger it on pushes and pull requests.

Run at least on:

```yaml
runs-on: ubuntu-latest
```

### 7.1 Main build proof

The workflow must:

1. check out only this repository with `actions/checkout`;
2. explicitly keep submodule checkout disabled, e.g. `submodules: false`;
3. never initialize Git submodules;
4. avoid caching `build/` or `build/_deps/` in the primary showcase workflow, because a warm dependency cache would obscure the first-run `FetchContent` behavior;
5. install minimal host dependencies such as `libsdl2-dev` and `ninja-build`;
6. run CMake configure from a clean build directory;
7. let that configure step fetch LVGL;
8. build the project successfully.

Use clear, explicit commands such as:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Step names should make it obvious that **CMake fetches LVGL during configuration**.

### 7.2 FetchContent update proof

CI must also prove the central update behavior.

After the initial configure/build, reconfigure the **same build directory** with another valid LVGL release tag, for example:

```bash
cmake -S . -B build -DLVGL_GIT_TAG=v9.4.0
```

Then verify that the checkout below CMake's dependency area now corresponds to the requested revision.

A read-only Git command may be used to inspect `build/_deps/lvgl-src` and prove which revision CMake selected. Git must **not** be used to perform the clone, fetch, checkout, or update itself.

The CI log should tell this story explicitly:

```text
Configure with default LVGL tag
Build
Reconfigure same build directory with another LVGL tag
Verify FetchContent changed the LVGL checkout
```

It is acceptable for the second revision-switch step to be configure + verification only if rebuilding against both releases would add unnecessary fragility. The default pinned release must always be fully built.

### 7.3 GUI behavior in CI

The GitHub Actions runner does not need to display the GUI.

CI is responsible for proving:

- configure works;
- LVGL is fetched by CMake;
- compilation and linking work;
- changing `LVGL_GIT_TAG` causes `FetchContent` to switch revisions.

The local executable provides the visible GUI proof.

---

## 8. README requirements

`README.md` is a major part of the showcase. It must explain both **how** and **why** the project works.

### 8.1 Opening explanation

The first section must state plainly that:

- this is a minimal LVGL/CMake demonstration;
- LVGL is **not** a Git submodule;
- LVGL is fetched during CMake configure via `FetchContent`;
- the fetched source lives in the build tree rather than the repository source tree;
- GitHub Actions proves the same behavior in CI.

### 8.2 Prerequisites

Document approximately:

- Git;
- CMake 3.28+;
- a C/C++ compiler;
- SDL2 development package;
- Ninja recommended.

Include an Ubuntu example:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build libsdl2-dev
```

### 8.3 Clone, configure, build, run

Document the exact normal workflow:

```bash
git clone <repository-url>
cd <repository-directory>
cmake -S . -B build -G Ninja
cmake --build build
./build/<demo-executable>
```

Explain that the first configure invocation populates LVGL under CMake's build-managed dependency area, normally:

```text
build/_deps/lvgl-src
```

### 8.4 Explain exactly how to change/update the LVGL tag

This is one of the main lessons and must be explicit.

Show:

```bash
cmake -S . -B build -DLVGL_GIT_TAG=v9.4.0
cmake --build build
```

Explain that:

- this reruns the configure step in the existing build directory;
- CMake sees that the requested dependency revision changed;
- `FetchContent` updates/switches the LVGL checkout as required;
- no `git submodule update` is involved.

Show switching again:

```bash
cmake -S . -B build -DLVGL_GIT_TAG=v9.5.0
```

### 8.5 Explain CMake cache behavior precisely

If `LVGL_GIT_TAG` has been supplied with `-D`, the value is stored in the CMake cache and continues to override the source default.

Document how to remove that override and return to the default in `CMakeLists.txt`:

```bash
cmake -S . -B build -U LVGL_GIT_TAG
```

If the developer edits the default tag directly in `CMakeLists.txt` and there is no cached `-DLVGL_GIT_TAG=...` override, the normal action is simply:

```bash
cmake -S . -B build
```

Deleting the build directory is a valid clean reset or troubleshooting step, but it must **not** be presented as the normal dependency-update mechanism:

```bash
rm -rf build
cmake -S . -B build -G Ninja
```

### 8.6 Explain why this is not a submodule

Include a concise conceptual comparison:

```text
Git submodule:
Git owns dependency checkout state in the source tree.

FetchContent:
CMake owns dependency population for the build tree.
```

Explain that this demo intentionally chooses the second model because LVGL is a build dependency and the goal is for a normal repository clone to be sufficient.

Do not claim that `FetchContent` is always superior to submodules.

### 8.7 Explain GitHub Actions

Describe what CI proves:

- clean checkout with no submodules;
- configure fetches LVGL;
- build links the demonstration executable against fetched LVGL;
- a second configure with a different tag updates the same `FetchContent` checkout.

---

## 9. Readability requirements

The project is intended to be read by humans, not merely executed.

Requirements:

- `CMakeLists.txt` is part of the documentation.
- Keep `FetchContent_Declare()` visible in the top-level file.
- Use blank lines and concise section comments.
- Do not create helper functions merely to hide a handful of straightforward CMake lines.
- A reader should be able to see `GIT_REPOSITORY`, `GIT_TAG`, and `FetchContent_MakeAvailable()` without navigating elsewhere.
- README commands should be copy/pasteable.
- GitHub Actions step names should describe exactly what is being proven.
- Avoid clever abstractions that make the dependency flow harder to inspect.

---

## 10. Acceptance criteria

The implementation is complete only when all of the following are true:

1. `.gitmodules` does not exist.
2. No LVGL source code is tracked by the main repository.
3. A fresh normal clone is sufficient.
4. `cmake -S . -B build` fetches LVGL automatically.
5. The fetched LVGL checkout appears under the CMake build dependency area, normally `build/_deps/lvgl-src`.
6. `cmake --build build` successfully compiles and links the C++ demo.
7. The application links through LVGL's upstream CMake target rather than manually compiling LVGL sources.
8. Running locally opens a small SDL/LVGL window.
9. The window displays one centered `Hello LVGL`-style label.
10. Changing `LVGL_GIT_TAG` and rerunning configure in the same build directory causes the LVGL checkout to change as requested.
11. No manual Git clone/fetch/checkout/update command is responsible for that dependency update.
12. GitHub Actions performs a clean configure and build.
13. GitHub Actions also proves a `FetchContent` revision change in the same build directory.
14. The README documents normal build and run commands.
15. The README documents the exact reconfigure command needed after changing the LVGL revision.
16. The README explains `-D` cache persistence and `-U LVGL_GIT_TAG`.
17. `CMakeLists.txt` contains concise comments explaining the `FetchContent` mechanism.
18. No large LVGL demos/examples are built unless technically required.
19. A developer can understand the core lesson by reading `README.md` and `CMakeLists.txt` in a few minutes.
20. Any extra complexity is justified by the core teaching goal.

---

## 11. Verification the coding agent must perform

Before considering the task complete, the coding agent must actually test the repository.

### Clean build

```bash
rm -rf build
cmake -S . -B build -G Ninja
cmake --build build
```

Verify that LVGL exists below:

```text
build/_deps/
```

### Revision update in the same build directory

Without deleting `build/`, run:

```bash
cmake -S . -B build -DLVGL_GIT_TAG=v9.4.0
```

Verify that `build/_deps/lvgl-src` now corresponds to `v9.4.0`.

Then restore the default release:

```bash
cmake -S . -B build -DLVGL_GIT_TAG=v9.5.0
cmake --build build
```

If the exact demonstration tags chosen for the implementation differ, use two valid, compatible release tags and document them consistently.

### Repository hygiene

Verify:

```bash
test ! -f .gitmodules
```

Also verify that:

- no LVGL source directory is tracked by the main repository;
- no CMake code manually invokes Git to clone/update LVGL;
- `build/` is ignored;
- GitHub Actions does not enable submodule checkout.

### Local visual test

On a machine with a desktop environment, run the built executable and confirm that it opens a window containing the single centered label.

---

## 12. Scope guardrails

Do not allow the implementation to drift into a larger sample application.

Avoid:

- multiple windows;
- multiple screens;
- complex widgets;
- images or assets;
- LVGL demo suites;
- elaborate themes or animations;
- embedded hardware support;
- cross-compilation;
- install/export packaging;
- unit-test frameworks;
- package managers;
- Docker unless explicitly requested later;
- custom dependency-management scripts.

Every line that is not needed to demonstrate **CMake FetchContent + LVGL + a minimal visible proof** should be questioned.

---

## 13. Definition of success

The finished repository succeeds when a reader can inspect `README.md` and `CMakeLists.txt` for a few minutes and confidently explain:

- where LVGL comes from;
- why there is no `.gitmodules` file;
- when CMake downloads/populates LVGL;
- where CMake stores it;
- how the application links to it;
- how to build and run the minimal LVGL window;
- how to change the LVGL tag;
- which CMake command reruns configuration;
- how a cached `-D` override behaves;
- how GitHub Actions proves the same workflow.

The final teaching message should be demonstrably true:

> Clone one normal GitHub repository, run CMake, and CMake obtains LVGL itself. Change the requested LVGL tag and rerun CMake; CMake updates the dependency checkout. No Git submodule is needed.
