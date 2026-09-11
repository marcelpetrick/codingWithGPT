# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

# -----------------------------------------------------------------------------
# Project setup
# -----------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.28)
project(cmake_fetchcontent_lvgl_demo LANGUAGES C CXX)

# -----------------------------------------------------------------------------
# Host dependency: SDL2
# -----------------------------------------------------------------------------
# SDL2 only provides the desktop window. It comes from the system package, not
# from FetchContent, so LVGL stays the only fetched dependency.
find_package(SDL2 REQUIRED)

# -----------------------------------------------------------------------------
# Dependency: LVGL via CMake FetchContent
# -----------------------------------------------------------------------------
# No Git submodule is used. CMake owns the checkout under build/_deps.
# Change LVGL_GIT_TAG and rerun configure to switch the dependency revision.
include(FetchContent)

if(NOT DEFINED LVGL_GIT_TAG)
    set(LVGL_GIT_TAG "v9.5.0")
endif()

FetchContent_Declare(
    lvgl
    GIT_REPOSITORY https://github.com/lvgl/lvgl.git
    GIT_TAG        ${LVGL_GIT_TAG}
    GIT_PROGRESS   TRUE
)

# LVGL's own CMake reads these as cache options. They are cache entries here
# too: LVGL runs under an older policy level, where a plain variable of the
# same name would be discarded on the very first configure.
set(LV_BUILD_CONF_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h"
    CACHE PATH "lv_conf.h used to configure LVGL")
set(CONFIG_LV_BUILD_EXAMPLES OFF CACHE BOOL "Build the LVGL examples")
set(CONFIG_LV_BUILD_DEMOS OFF CACHE BOOL "Build the LVGL demos")
set(CONFIG_LV_USE_THORVG_INTERNAL OFF CACHE BOOL "Build LVGL's bundled ThorVG")

message(STATUS "LVGL FetchContent revision: ${LVGL_GIT_TAG}")
FetchContent_MakeAvailable(lvgl)

# LVGL's SDL driver is compiled inside the lvgl target, so SDL2 belongs to it.
target_link_libraries(lvgl PRIVATE SDL2::SDL2)

# -----------------------------------------------------------------------------
# Application target
# -----------------------------------------------------------------------------
add_executable(hello_lvgl src/main.cpp)
target_compile_features(hello_lvgl PRIVATE cxx_std_17)
target_link_libraries(hello_lvgl PRIVATE lvgl::lvgl)
