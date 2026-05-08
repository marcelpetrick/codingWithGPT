cmake_minimum_required(VERSION 3.20)
project(lvgl_demo C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(SDL2 REQUIRED)

include(FetchContent)
FetchContent_Declare(
    lvgl
    GIT_REPOSITORY https://github.com/lvgl/lvgl.git
    GIT_TAG v9.2.2
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(lvgl)

# Expose our lv_conf.h and SDL2 headers to LVGL's own compilation units
target_compile_definitions(lvgl PUBLIC LV_CONF_INCLUDE_SIMPLE=1)
target_include_directories(lvgl PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${SDL2_INCLUDE_DIRS}
)

add_executable(lvgl_demo main.c)
target_include_directories(lvgl_demo PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(lvgl_demo PRIVATE
    lvgl
    ${SDL2_LIBRARIES}
    m
    pthread
)
