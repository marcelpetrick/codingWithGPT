cmake_minimum_required(VERSION 3.16)
project(MarkdownUnicodeConverter LANGUAGES CXX)

# Find Qt6 modules
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

# Add executable target
add_executable(markdown_unicode src/main.cpp)

# Link Qt6 libraries
target_link_libraries(markdown_unicode PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets)

# Set output name and directory
set_target_properties(markdown_unicode PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)