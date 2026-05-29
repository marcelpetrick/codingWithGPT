# behavior_project

A C project demonstrating CMake configuration with feature flags and conditional compilation.

## Overview

This project shows how to use CMake to control application behavior at build time through:

- **CMake options**: Enable/disable features like logging, debugging, performance tracking
- **CMake flavors**: Pre-configured build profiles (performance, security, debug)
- **C11 standard**: Modern C standard with required and extensions enabled
- **CMake 3.28+**: Modern CMake version with improved conditional logic

## Building

### Prerequisites

- CMake 3.28 or later
- A C11 compatible compiler (GCC 5+, Clang 3.9+, or MSVC 2015+)

### Quick Start

```bash
# Create build directory
mkdir -p build
cd build

# Configure with default settings
cmake ..
make
```

### Build with CMake Options

```bash
cd build

# Enable logging and performance tracking
cmake -DENABLE_LOGGING=ON -DENABLE_PERFORMANCE=ON ..
make

# Enable security features
cmake -DENABLE_SECURITY=ON -DENABLE_LOGGING=ON ..
make

# Enable debug build
cmake -DENABLE_DEBUG=ON ..
make
```

### Using Build Flavors

```bash
cd build

# Performance flavor (optimized, with performance tracking)
cmake -DFLAVOR_PERFORMANCE=ON ..
make

# Security flavor (with security validation)
cmake -DFLAVOR_SECURITY=ON ..
make

# Debug flavor (with debug symbols and verbose logging)
cmake -DFLAVOR_DEBUG=ON ..
make
```

### Release Build

```bash
cd build

# Release build with optimization
cmake -DCMAKE_BUILD_TYPE=Release ..
make
```

### Sanitizers

Enable AddressSanitizer and UndefinedBehaviorSanitizer:

```bash
cd build
cmake -DENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug ..
make
```

## CMake Options

| Option | Default | Description |
|--------|---------|-------------|
| `ENABLE_LOGGING` | ON | Enable logging output |
| `ENABLE_DEBUG` | OFF | Build with debugging symbols and verbose output |
| `ENABLE_PERFORMANCE` | OFF | Enable performance tracking |
| `ENABLE_SECURITY` | OFF | Enable security validation |
| `ENABLE_SANITIZERS` | OFF | Enable compiler sanitizers |

## CMake Flavors

| Flavor | Features |
|--------|----------|
| `FLAVOR_PERFORMANCE` | Performance tracking, security validation, optimized builds |
| `FLAVOR_SECURITY` | Security validation, logging enabled |
| `FLAVOR_DEBUG` | Debug output, logging enabled, debug symbols |

## Compiler Flags

The project sets the following default compiler flags:

```bash
# Default flags (all builds)
-Wall -Wextra

# Debug build
-g3 -O0

# Release build
-O3 -DNDEBUG

# Release with debug info
-O2 -g -DNDEBUG
```

## Features

### Logging

Conditionally compiled logging macros that output to stdout:

```c
LOG("Message with arguments: %d", value);
```

Only compiled when `ENABLE_LOGGING=ON`.

### Debug Output

Debug messages only appear when `ENABLE_DEBUG=ON` or `FLAVOR_DEBUG=ON`:

```c
DEBUG("Debug information here");
```

### Performance Tracking

Tracks function execution time when `ENABLE_PERFORMANCE=ON`:

```c
PERF_START("my_function", "main");
// ... code ...
PERF_END("my_function", "main");
PERF_REPORT();
```

### Security Validation

Input validation and buffer overflow prevention when `ENABLE_SECURITY=ON`:

```c
if (sec_validate_input(input, max_len)) {
    // safe to use
}
```

## Usage

After building:

```bash
./bin/behavior
```

## Output

### Default build (logging enabled, no performance/security)

```
[LOG] Application started: BehaviorDemo v1.0.0
[LOG] This is informational log message
[LOG] Input validation passed
[LOG] Buffer copied successfully
[LOG] Application finished
```

### With performance and security features

```
[LOG] Application started: PerformanceDemo v1.0.0
[LOG] Security features enabled
[PERF] init: 0.01ms (func: main)
[PERF] All performance tracking complete.
```

### Debug build

```
[LOG] Application started: BehaviorDemo v1.0.0
[DEBUG] Debug mode enabled
[DEBUG] Performance tracking enabled
[DEBUG] Security features disabled
...
[DEBUG] Application completed with result: 0
```

## CMake Cache Variables

The following CMake cache variables are also available for advanced users:

- `CMAKE_C_STANDARD`: Set to 11
- `CMAKE_C_STANDARD_REQUIRED`: Ensures strict C11 compliance
- `CMAKE_C_EXTENSIONS`: Enables C11 extensions
- `CMAKE_C_FLAGS`: Default compiler flags
- `CMAKE_C_FLAGS_DEBUG`: Debug build flags
- `CMAKE_C_FLAGS_RELEASE`: Release build flags

## Cleaning

```bash
# Clean build directory
cd build
make clean

# Or start fresh
rm -rf ../build/*
```

## License

This project is provided as-is for educational purposes.
