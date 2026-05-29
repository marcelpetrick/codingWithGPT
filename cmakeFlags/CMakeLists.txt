cmake_minimum_required(VERSION 3.28)

project(Chimera
    VERSION 1.0.0
    DESCRIPTION "A shapeshifting diagnostic reporter"
    LANGUAGES C
)

# ── Language standard ────────────────────────────────────────────────────────
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# ── Flavor selection ─────────────────────────────────────────────────────────
set(CHIMERA_FLAVOR "ORACLE" CACHE STRING
    "Build flavor — controls runtime personality and compiler flags. \
Choose: ORACLE | GHOST | TITAN")
set_property(CACHE CHIMERA_FLAVOR PROPERTY STRINGS ORACLE GHOST TITAN)

# ── Validate and map flavor → source file ────────────────────────────────────
if(CHIMERA_FLAVOR STREQUAL "ORACLE")
    set(FLAVOR_SRC src/oracle.c)
    set(FLAVOR_CFLAGS -O2)
    set(FLAVOR_DEFS FLAVOR_ORACLE DEBUG_VERBOSE=1)

elseif(CHIMERA_FLAVOR STREQUAL "GHOST")
    set(FLAVOR_SRC src/ghost.c)
    set(FLAVOR_CFLAGS -Os -DNDEBUG)
    set(FLAVOR_DEFS FLAVOR_GHOST)

elseif(CHIMERA_FLAVOR STREQUAL "TITAN")
    set(FLAVOR_SRC src/titan.c)
    set(FLAVOR_CFLAGS -O3)
    set(FLAVOR_DEFS FLAVOR_TITAN PERFORMANCE_MODE=1)

else()
    message(FATAL_ERROR
        "Unknown CHIMERA_FLAVOR '${CHIMERA_FLAVOR}'. "
        "Valid choices: ORACLE | GHOST | TITAN"
    )
endif()

# ── Executable ───────────────────────────────────────────────────────────────
add_executable(chimera
    src/main.c
    ${FLAVOR_SRC}
)

# Public version string baked in at compile time
target_compile_definitions(chimera PRIVATE
    ${FLAVOR_DEFS}
    CHIMERA_VERSION="${PROJECT_VERSION}"
    CHIMERA_FLAVOR_NAME="${CHIMERA_FLAVOR}"
)

# Flavor-specific optimisation flags
target_compile_options(chimera PRIVATE
    ${FLAVOR_CFLAGS}
    -Wall
    -Wextra
    -Wpedantic
    -Werror
)

target_include_directories(chimera PRIVATE src)

# ── Status report ────────────────────────────────────────────────────────────
message(STATUS "")
message(STATUS "┌─ Chimera build configuration ──────────────┐")
message(STATUS "│  Flavor   : ${CHIMERA_FLAVOR}")
message(STATUS "│  Opt flags: ${FLAVOR_CFLAGS}")
message(STATUS "│  Defines  : ${FLAVOR_DEFS}")
message(STATUS "│  Version  : ${PROJECT_VERSION}")
message(STATUS "└────────────────────────────────────────────┘")
message(STATUS "")
