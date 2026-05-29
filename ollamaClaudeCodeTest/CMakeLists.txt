cmake_minimum_required(VERSION 3.28)

# Project definition
project(
    behavior_project
    VERSION 1.0.0
    DESCRIPTION "C project demonstrating CMake flags and conditional compilation"
    LANGUAGES C
)

# Require C11 standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Set default compiler flags
set(CMAKE_C_FLAGS "-Wall -Wextra" CACHE STRING "Default C flags")
set(CMAKE_C_FLAGS_DEBUG "-g3 -O0" CACHE STRING "Debug C flags")
set(CMAKE_C_FLAGS_RELEASE "-O3 -DNDEBUG" CACHE STRING "Release C flags")
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-O2 -g -DNDEBUG" CACHE STRING "Release with debug info flags")

# Feature flags - configure behavior at build time
# These flags control compilation of specific features
option(ENABLE_LOGGING "Enable logging output" ON)
option(ENABLE_DEBUG "Build with debugging symbols and verbose output" OFF)
option(ENABLE_PERFORMANCE "Enable performance tracking" OFF)
option(ENABLE_SECURITY "Enable security validation" OFF)
option(ENABLE_SANITIZERS "Enable compiler sanitizers (UB, null, etc)" OFF)

# Flavor option - select different build profiles
option(FLAVOR_PERFORMANCE "Build optimized performance flavor" OFF)
option(FLAVOR_SECURITY "Build secure flavor with validation" OFF)
option(FLAVOR_DEBUG "Build debug flavor with maximum symbols" OFF)

# Apply flavor configurations
if(FLAVOR_PERFORMANCE)
    set(ENABLE_PERFORMANCE ON)
    set(ENABLE_SECURITY ON)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DFLAVOR_PERFORMANCE=1")
elseif(FLAVOR_SECURITY)
    set(ENABLE_SECURITY ON)
    set(ENABLE_LOGGING ON)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DFLAVOR_SECURITY=1")
elseif(FLAVOR_DEBUG)
    set(ENABLE_DEBUG ON)
    set(ENABLE_LOGGING ON)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DFLAVOR_DEBUG=1")
endif()

# Apply individual feature flags
if(ENABLE_DEBUG)
    add_definitions(-DDEBUG_BUILD)
    set(ENABLE_LOGGING ON)
endif()

if(ENABLE_LOGGING)
    add_definitions(-DENABLE_LOGGING)
endif()

if(ENABLE_PERFORMANCE)
    add_definitions(-DENABLE_PERFORMANCE)
endif()

if(ENABLE_SECURITY)
    add_definitions(-DENABLE_SECURITY)
endif()

# Sanitizers (if enabled)
if(ENABLE_SANITIZERS)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address,undefined -fno-omit-frame-pointer")
endif()

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)

# Executable
add_executable(behavior behavior.c)

# Link libraries (none required for this demo)
# target_link_libraries(behavior PRIVATE ...)

# Set executable properties
set_target_properties(behavior PROPERTIES
    OUTPUT_NAME "behavior"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Install rules
install(TARGETS behavior
    RUNTIME DESTINATION bin
)

# Print configuration summary
message(STATUS "")
message(STATUS "========================================")
message(STATUS "Build Configuration for ${PROJECT_NAME}")
message(STATUS "========================================")
message(STATUS "Version:            ${PROJECT_VERSION}")
message(STATUS "C Standard:         ${CMAKE_C_STANDARD}")
message(STATUS "Compiler:           ${CMAKE_C_COMPILER_ID} ${CMAKE_C_COMPILER_VERSION}")
message(STATUS "========================================")
message(STATUS "Features:")
message(STATUS "  Logging:          ${ENABLE_LOGGING}")
message(STATUS "  Debug:            ${ENABLE_DEBUG}")
message(STATUS "  Performance:      ${ENABLE_PERFORMANCE}")
message(STATUS "  Security:         ${ENABLE_SECURITY}")
message(STATUS "  Sanitizers:       ${ENABLE_SANITIZERS}")
message(STATUS "========================================")
message(STATUS "Flavors:")
message(STATUS "  Performance:      ${FLAVOR_PERFORMANCE}")
message(STATUS "  Security:         ${FLAVOR_SECURITY}")
message(STATUS "  Debug:            ${FLAVOR_DEBUG}")
message(STATUS "========================================")
message(STATUS "")
