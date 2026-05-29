# Chimera

A shapeshifting C11 diagnostic reporter. One binary, three personalities — controlled entirely at **build time** via CMake flavor flags.

Chimera demonstrates how to use CMake's `CACHE` variables, `target_compile_definitions`, and `target_compile_options` to produce binaries with radically different runtime behavior from the same source tree.

---

## Flavors

| Flavor | Personality | Compiler flags | Use case |
|--------|-------------|---------------|----------|
| `ORACLE` | Verbose, mystical, timestamped | `-O2 -DDEBUG_VERBOSE=1` | Development / debugging |
| `GHOST` | Minimal — one line, nothing more | `-Os -DNDEBUG` | Embedded / CI pipelines |
| `TITAN` | Loud ASCII banner, maximum bravado | `-O3 -DPERFORMANCE_MODE=1` | Release / showoff builds |

---

## Requirements

- CMake ≥ 3.28
- A C11-capable compiler (`gcc` ≥ 5 or `clang` ≥ 3.6)
- Standard POSIX environment (Linux / macOS)

---

## Building

All builds follow the same pattern: configure → build → run. Only the `-DCHIMERA_FLAVOR=` argument changes.

```bash
# Create an out-of-source build directory (once)
mkdir -p build && cd build

# Build the ORACLE flavor (default)
cmake .. -DCHIMERA_FLAVOR=ORACLE
cmake --build .
./chimera

# Switch to GHOST — reconfigure in the same build dir
cmake .. -DCHIMERA_FLAVOR=GHOST
cmake --build .
./chimera

# Switch to TITAN
cmake .. -DCHIMERA_FLAVOR=TITAN
cmake --build .
./chimera
```

Or use separate build directories to keep all three around simultaneously:

```bash
cmake -B build-oracle -DCHIMERA_FLAVOR=ORACLE && cmake --build build-oracle
cmake -B build-ghost  -DCHIMERA_FLAVOR=GHOST  && cmake --build build-ghost
cmake -B build-titan  -DCHIMERA_FLAVOR=TITAN  && cmake --build build-titan

./build-oracle/chimera
./build-ghost/chimera
./build-titan/chimera
```

---

## Example output

### ORACLE
```
╔══════════════════════════════════════════════╗
║          C H I M E R A  ::  O R A C L E      ║
╚══════════════════════════════════════════════╝

  Version   : 1.0.0
  Flavor    : ORACLE
  Run ID    : 0xA3F12C8B
  Timestamp : 2026-05-29 14:22:01 CEST

  ── Verbose diagnostics (DEBUG_VERBOSE=1) ───────────────
  sizeof(time_t)        = 8 bytes
  sizeof(chimera_ctx_t) = 32 bytes
  Compiler C standard   : C11
  ────────────────────────────────────────────────────────

  Prophecy  : "Every flag you pass is a vow to the compiler."

  [ORACLE] The vision is clear. All systems nominal.
```

### GHOST
```
chimera/GHOST v1.0.0 run=0xA3F12C8B
```

### TITAN
```
  ████████╗██╗████████╗ █████╗ ███╗   ██╗
  ...

  ╔══════════════════════════════════════════╗
  ║     *** TITAN FORCE ENGAGED ***           ║
  ╠══════════════════════════════════════════╣
  ║  Flavor      : TITAN                     ║
  ...
  [!!] The Titan rises. Resistance is futile.
```

---

## How the CMake flags work

### 1. Flavor as a cached CMake variable

```cmake
set(CHIMERA_FLAVOR "ORACLE" CACHE STRING "Build flavor ...")
set_property(CACHE CHIMERA_FLAVOR PROPERTY STRINGS ORACLE GHOST TITAN)
```

`CACHE STRING` stores the value between CMake runs and makes it visible in `cmake-gui` / `ccmake` as a drop-down. `set_property … STRINGS` restricts it to valid choices.

### 2. Mapping the flavor to a source file

```cmake
if(CHIMERA_FLAVOR STREQUAL "ORACLE")
    set(FLAVOR_SRC src/oracle.c)
    set(FLAVOR_CFLAGS -O2)
    set(FLAVOR_DEFS FLAVOR_ORACLE DEBUG_VERBOSE=1)
elseif(...)
    ...
endif()

add_executable(chimera src/main.c ${FLAVOR_SRC})
```

CMake links only the chosen `.c` file. Each flavor implements the same `chimera_run()` function declared in `chimera.h` — this is **C's equivalent of a compile-time strategy pattern**.

### 3. Baking defines into the binary

```cmake
target_compile_definitions(chimera PRIVATE
    ${FLAVOR_DEFS}
    CHIMERA_VERSION="${PROJECT_VERSION}"
    CHIMERA_FLAVOR_NAME="${CHIMERA_FLAVOR}"
)
```

`target_compile_definitions` passes `-D` flags to the compiler **scoped to this target only** (`PRIVATE`). The C source reads them as ordinary preprocessor macros:

```c
#if DEBUG_VERBOSE
    printf("sizeof(time_t) = %zu\n", sizeof(time_t));
#endif
```

### 4. Per-flavor compiler optimisation flags

```cmake
target_compile_options(chimera PRIVATE ${FLAVOR_CFLAGS} -Wall -Wextra -Wpedantic -Werror)
```

`target_compile_options` appends flags to the compile command for this target. ORACLE gets `-O2`, GHOST gets `-Os` (size-optimised), TITAN gets `-O3`.

### 5. Compile-time guard in the header

```c
#if !defined(FLAVOR_ORACLE) && !defined(FLAVOR_GHOST) && !defined(FLAVOR_TITAN)
#  error "No build flavor defined."
#endif
```

If someone tries to compile a source file by hand without going through CMake, they get an immediate, readable error rather than a mystery linker failure.

---

## Project structure

```
chimera/
├── CMakeLists.txt      — build system; all flag logic lives here
└── src/
    ├── chimera.h       — shared interface + compile-time guards
    ├── main.c          — entry point; flavor-agnostic
    ├── oracle.c        — ORACLE personality
    ├── ghost.c         — GHOST personality
    └── titan.c         — TITAN personality
```
