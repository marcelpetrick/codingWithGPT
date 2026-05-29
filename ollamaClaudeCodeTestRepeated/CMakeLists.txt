# CMakeLists.txt for Compile-Time Configuration Demo
# Requires CMake 3.28+

cmake_minimum_required(VERSION 3.28)

project(CompileTimeConfigDemo
    VERSION 1.0.0
    DESCRIPTION "CMake compile-time configuration demo"
    LANGUAGES C
)

# =============================================================================
# CMake Options - Compile-Time Configuration Controls
# =============================================================================

# Option 1: DEBUG vs RELEASE vs VERBOSE build modes
option(ENABLE_DEBUG "Enable debug output" OFF)
option(ENABLE_VERBOSE "Enable verbose logging" OFF)

# Option 2: Feature flags
option(ENABLE_FEATURE_A "Enable Feature A (alpha support)" ON)
option(ENABLE_FEATURE_B "Enable Feature B (beta support)" OFF)

# Option 3: Safety checks
option(ENABLE_BOUNDS_CHECKS "Enable bounds checking (slower but safer)" OFF)
option(ENABLE_ASSERTIONS "Compile with assert()" ON)

# =============================================================================
# Build Configurations - Derive from options
# =============================================================================

# Determine build mode
set(BUILD_MODE "RELEASE")
if(ENABLE_DEBUG)
    set(BUILD_MODE "DEBUG")
elseif(ENABLE_VERBOSE)
    set(BUILD_MODE "VERBOSE")
endif()
message(STATUS "Build mode: ${BUILD_MODE}")

# Determine feature set
set(FEATURE_A_ENABLED "")
set(FEATURE_B_ENABLED "")
if(ENABLE_FEATURE_A)
    set(FEATURE_A_ENABLED "A")
endif()
if(ENABLE_FEATURE_B)
    set(FEATURE_B_ENABLED "B")
endif()
set(FEATURE_SET "${FEATURE_A_ENABLED}${FEATURE_B_ENABLED}")

message(STATUS "Features enabled: ${FEATURE_SET}")

# Determine safety mode
set(SAFETY_MODE "NONE")
if(ENABLE_BOUNDS_CHECKS)
    set(SAFETY_MODE "SAFETY")
endif()

message(STATUS "Safety mode: ${SAFETY_MODE}")

# =============================================================================
# Compiler Definitions - Inject into target
# =============================================================================

add_executable(app src/main.c)

# Add compiler definitions based on options
target_compile_definitions(app PRIVATE
    # Build mode
    $<$<BOOL:${ENABLE_DEBUG}>:DEBUG_BUILD=1>
    $<$<BOOL:${ENABLE_VERBOSE}>:VERBOSE_BUILD=1>

    # Feature flags
    $<$<BOOL:${ENABLE_FEATURE_A}>:FEATURE_A=1>
    $<$<BOOL:${ENABLE_FEATURE_B}>:FEATURE_B=1>

    # Safety checks
    $<$<BOOL:${ENABLE_BOUNDS_CHECKS}>:BOUNDS_CHECKS=1>

    # Assertions
    $<$<BOOL:${ENABLE_ASSERTIONS}>:ENABLE_ASSERTIONS=1>

    # Version
    VERSION="${PROJECT_VERSION}"
)

# Add string definitions (these are always defined, not conditional)
target_compile_definitions(app PRIVATE
    BUILD_MODE_STRING="${BUILD_MODE}"
    FEATURE_SET_STRING="${FEATURE_SET}"
    SAFETY_MODE_STRING="${SAFETY_MODE}"
    FEATURE_A_STRING="A"
    FEATURE_B_STRING="B"
    VERSION_STRING="${PROJECT_VERSION}"
)

# =============================================================================
# Additional build configurations
# =============================================================================

# Set C standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Optimize based on build mode
if(BUILD_MODE STREQUAL "DEBUG")
    target_compile_options(app PRIVATE -g -O0)
    set(CMAKE_DEBUG_POSTFIX "d")
elseif(BUILD_MODE STREQUAL "VERBOSE")
    target_compile_options(app PRIVATE -O1)
endif()

# =============================================================================
# Print configuration summary
# =============================================================================
message(STATUS "")
message(STATUS "========================================")
message(STATUS "  CONFIGURATION SUMMARY")
message(STATUS "========================================")
message(STATUS "  Build Mode:    ${BUILD_MODE}")
message(STATUS "  Features:      ${FEATURE_SET}")
message(STATUS "  Safety Mode:   ${SAFETY_MODE}")
message(STATUS "  Assertions:    ${ENABLE_ASSERTIONS}")
message(STATUS "========================================")
message(STATUS "")
