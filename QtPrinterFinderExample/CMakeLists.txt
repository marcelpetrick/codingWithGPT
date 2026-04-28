cmake_minimum_required(VERSION 3.16)

project(QtPrinterFinderExample
    VERSION 1.0.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt5 5.15 REQUIRED COMPONENTS
    Concurrent
    Network
    PrintSupport
    Widgets
)

add_executable(QtPrinterFinderExample
    src/main.cpp
    src/PrinterFinderWidget.cpp
    src/PrinterFinderWidget.h
)

target_link_libraries(QtPrinterFinderExample PRIVATE
    Qt5::Concurrent
    Qt5::Network
    Qt5::PrintSupport
    Qt5::Widgets
)
