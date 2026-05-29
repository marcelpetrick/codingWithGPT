# behavior_project

A C project demonstrating how to use CMake to configure application behavior at build time.

## Getting Started

### Prerequisites

Install these tools first:

```bash
# Check if CMake is installed
cmake --version

# If not installed on Ubuntu/Debian:
sudo apt install cmake build-essential
```

### Build and Run (5 minutes)

```bash
# 1. Create a build directory
mkdir -p build
cd build

# 2. Configure the project (answer CMake questions)
cmake ..

# 3. Build the project
make

# 4. Run the executable
./bin/behavior
```

You should see output like:
```
[LOG] Application started: BehaviorDemo v1.0.0
[LOG] This is informational log message
[LOG] Application finished
```

## What Does This Project Show?

This project demonstrates how to control what features are compiled into your program
by using **CMake options**. Each time you run `cmake`, you can choose what to include.

Think of it like choosing features when installing software:
- Want logging? Enable it.
- Want security checks? Enable it.
- Want debug info? Enable it.

## CMake Options Explained

### `ENABLE_LOGGING` (default: ON)
Enables `[LOG]` messages in the output.

### `ENABLE_DEBUG` (default: OFF)
Adds debugging symbols and shows `[DEBUG]` messages. Use when:
- Your code isn't working and you need to find the problem
- You want to see what functions are being called
- You're developing the application

### `ENABLE_PERFORMANCE` (default: OFF)
Measures how long functions take to run. Shows `[PERF]` results.

### `ENABLE_SECURITY` (default: OFF)
Adds input validation to prevent buffer overflows. Use for:
- Production code that handles user input
- Code that works over a network

### `ENABLE_SANITIZERS` (default: OFF)
Enables compiler tools that detect bugs like:
- Memory leaks
- Buffer overflows
- Invalid memory access

## Build Flavors (Pre-configured Sets)

Instead of setting many options, you can choose a "flavor":

```bash
# Performance flavor: Fast code + performance tracking + security
cmake -DFLAVOR_PERFORMANCE=ON ..

# Security flavor: Security checks + logging
cmake -DFLAVOR_SECURITY=ON ..

# Debug flavor: Lots of debug info + logging
cmake -DFLAVOR_DEBUG=ON ..
```

## Common Build Scenarios

### Development Build (with lots of debug info)
```bash
cd build
cmake -DENABLE_DEBUG=ON -DENABLE_LOGGING=ON ..
make
./bin/behavior
```

### Production Build (optimized, no debug info)
```bash
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
./bin/behavior
```

### Debug with Security
```bash
cd build
cmake -DENABLE_DEBUG=ON -DENABLE_SECURITY=ON ..
make
./bin/behavior
```

## How It Works (For Beginners)

### 1. The Source File (`behavior.c`)

Contains C code with special markers like:
```c
LOG("message");       // Only shows when ENABLE_LOGGING is ON
DEBUG("message");     // Only shows when ENABLE_DEBUG is ON
PERF_START("func");   // Only tracks when ENABLE_PERFORMANCE is ON
```

### 2. CMake Configuration (`CMakeLists.txt`)

This file tells CMake:
- What source files to compile
- What compiler flags to use
- Which options to enable

When you run `cmake ..`, CMake:
1. Reads your options from the command line
2. Sets compiler defines like `-DENABLE_LOGGING`
3. Generates a `Makefile` to build the project

### 3. Makefile (`build/Makefile`)

The Makefile tells `make` which files to compile and in what order.

### 4. Compiled Executable (`build/bin/behavior`)

The final program you run. Only the features you enabled are included.

## Compiler Flags

The project uses these standard flags:

| Flag | Purpose |
|------|---------|
| `-Wall -Wextra` | Show warnings about potential problems |
| `-g3 -O0` | Debug: lots of symbols, no optimization |
| `-O3 -DNDEBUG` | Release: maximum optimization, no debug symbols |
| `-fsanitize=...` | Enable bug detection tools |

## Clean Start

```bash
# Remove all build files
rm -rf build/*
# Or just the build directory
rm -rf build
```

## Questions

### Q: Why use CMake instead of just `gcc`?
A: CMake helps manage complex projects. It generates Makefiles and handles
compiler-specific differences automatically.

### Q: Can I change the C standard?
A: Yes, in `CMakeLists.txt` find `CMAKE_C_STANDARD` and change `11` to `99` for C17.

### Q: Where is the executable?
A: By default, it's at `build/bin/behavior`. You can change this in CMake.

### Q: What does `cmake ..` mean?
A: It runs CMake in the parent directory to find `CMakeLists.txt`.

### Q: Can I build with Visual Studio?
A: Yes! On Windows, use the GUI: "Generate Visual Studio project files" then open
the `.sln` file in Visual Studio.

## Troubleshooting

### "CMake Error: CMAKE_C_COMPILER not set"
Solution: Install a C compiler:
```bash
sudo apt install build-essential
```

### "make: *** No rule to make target"
Solution: Run `cmake ..` first to generate the Makefile.

### "Permission denied when running ./bin/behavior"
Solution:
```bash
chmod +x bin/behavior
```

## Next Steps

1. Try building with different options
2. Read the source code `behavior.c` to see the conditional compilation
3. Modify `behavior.c` to add your own features
4. Experiment with compiler flags

## Summary

- Use `cmake -DENABLE_XXX=ON` to enable features
- Use `-DENABLE_DEBUG=ON` for development
- Use `-DCMAKE_BUILD_TYPE=Release` for production
- All builds use C11 standard
- See `behavior.c` to learn about conditional compilation
