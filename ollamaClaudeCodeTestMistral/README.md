# Compile-Time Configuration Demo

A complete, buildable C11 project using CMake 3.28 that demonstrates **compile-time configuration** through CMake options and compiler definitions.

## 🎯 Purpose

This project demonstrates how to:
- Use CMake `option()` to create boolean configuration options
- Inject compiler definitions via `target_compile_definitions()`
- Create build variants with visibly different runtime behavior
- Show how configuration options translate to preprocessor macros
- Teach junior developers about CMake build configuration patterns

## 📁 Project Structure

```
.
├── CMakeLists.txt          # Build configuration with options
├── README.md               # This file
└── src/
    └── main.c              # Source code using compile-time definitions
```

## 🛠️ Build Options

### Build Mode Options

| Option | Description | Effect |
|--------|-------------|--------|
| `ENABLE_DEBUG` | Enable debug mode | Adds `[DEBUG]` tags, disables optimizations, `-g` debug symbols |
| `ENABLE_VERBOSE` | Enable verbose logging | Prints detailed configuration info on startup |
| *(default)* | Standard release | Compact output, optimized builds |

### Feature Options

| Option | Description | Runtime Behavior |
|--------|-------------|------------------|
| `ENABLE_FEATURE_A` (default: ON) | Alpha feature set | Runs "Feature A" operations, prints counter-based logs |
| `ENABLE_FEATURE_B` (default: OFF) | Beta feature set | Runs "Feature B" ops, collects statistics, calculates averages |

### Safety Options

| Option | Description | Runtime Behavior |
|--------|-------------|------------------|
| `ENABLE_BOUNDS_CHECKS` (default: OFF) | Enable bounds checking | Validates input ranges, clamps out-of-bounds values |
| `ENABLE_ASSERTIONS` (default: ON) | Compile with assert() | Runtime check assertions, exits on failure |

## 🚀 Quick Start

### Prerequisites

- CMake 3.28+
- A C11-compatible compiler (gcc, clang, or clang-cl)
- Linux/macOS or Windows with MSVC

### Build Commands

#### 1. Create build directory

```bash
mkdir build && cd build
```

#### 2. Configure with cmake

```bash
cmake ..
```

#### 3. Build

```bash
make
```

#### 4. Run

```bash
./app
```

## 🧪 Build Variants & Examples

### Variant 1: Standard Release (Default)

```bash
mkdir build && cd build
cmake -DENABLE_DEBUG=OFF -DENABLE_VERBOSE=OFF ..
make
./app
```

**Expected output:**
```
===========================================
  COMPILE-TIME CONFIGURATION DEMO
===========================================

Build Configuration:
  Build Mode:   RELEASE
  Features:     A
  Safety Mode:  NONE
  Assertions:   ON

-------------------------------------------
  Runtime Feature Tests
-------------------------------------------

[FEATURE A] Running A-specific operations...
[FEATURE A] Operation A-0: counter=1
[FEATURE A] Operation A-1: counter=2
[FEATURE A] Operation A-2: counter=3

-------------------------------------------
  Bounds Check Test
-------------------------------------------

  Input:  -1 -> Output:  50 [NO CHECK]
  Input:  50 -> Output:  50 [NO CHECK]
  Input: 100 -> Output: 100 [NO CHECK]
  Input: 101 -> Output: 100 [NO CHECK]

===========================================
  Demo Complete!
===========================================
```

### Variant 2: Debug Mode

```bash
mkdir build && cd build
cmake -DENABLE_DEBUG=ON ..
make
./app
```

**Expected output:**
```
===========================================
  COMPILE-TIME CONFIGURATION DEMO
===========================================

[DEBUG] Debug mode enabled - detailed output

Build Configuration:
  Build Mode:   DEBUG
  Features:     A
  Safety Mode:  NONE
  Assertions:   ON

...
```

### Variant 3: Verbose Mode

```bash
mkdir build && cd build
cmake -DENABLE_VERBOSE=ON ..
make
./app
```

**Expected output:**
```
===========================================
  COMPILE-TIME CONFIGURATION DEMO
===========================================

[VERBOSE] Verbose mode enabled
        Project: CompileTimeConfigDemo v1.0.0
        Build:   VERBOSE
        Features: A
        Safety:   NONE
        Assertions: ON
...
```

### Variant 4: All Features Enabled

```bash
mkdir build && cd build
cmake -DENABLE_DEBUG=OFF \
      -DENABLE_FEATURE_A=ON \
      -DENABLE_FEATURE_B=ON \
      -DENABLE_BOUNDS_CHECKS=ON \
      -DENABLE_ASSERTIONS=ON \
      ..
make
./app
```

**Expected output:**
```
[FEATURE A] Running A-specific operations...
[FEATURE A] Operation A-0: counter=1
[FEATURE A] Operation A-1: counter=2
[FEATURE A] Operation A-2: counter=3
[FEATURE B] Running B-specific operations...
[FEATURE B] Stats update complete for operation 0
[FEATURE B] Stats update complete for operation 1
...
```

### Variant 5: Debug with All Safety Features

```bash
mkdir build && cd build
cmake -DENABLE_DEBUG=ON \
      -DENABLE_FEATURE_A=ON \
      -DENABLE_FEATURE_B=ON \
      -DENABLE_BOUNDS_CHECKS=ON \
      -DENABLE_ASSERTIONS=ON \
      ..
make
./app
```

**Expected output:**
```
[DEBUG] Debug mode enabled - detailed output
...
[FEATURE A] Running A-specific operations...
...
[FEATURE B] Running B-specific operations...
...
Warning: Value -1 below minimum (0)
Warning: Value 101 exceeds maximum (100)
...
  test_array[0] = 10: OK
  test_array[1] = 20: OK
...
  All assertions passed!
```

## 📝 How It Works

### 1. CMake Options

```cmake
option(ENABLE_DEBUG "Enable debug output" OFF)
```

Creates a cache variable `ENABLE_DEBUG` that can be set via:
- CMake GUI
- `cmake -DENABLE_DEBUG=ON ..` command line
- `CMakeCache.txt`

### 2. Conditional Compiler Definitions

```cmake
target_compile_definitions(app PRIVATE
    $<$<BOOL:${ENABLE_DEBUG}>:DEBUG_BUILD=1>
    $<$<BOOL:${ENABLE_FEATURE_A}>:FEATURE_A=1>
    $<$<BOOL:${ENABLE_BOUNDS_CHECKS}>:BOUNDS_CHECKS=1>
)
```

Generates `#define DEBUG_BUILD 1` (or not) during compilation.

### 3. Preprocessor Conditionals in Code

```c
#if DEBUG_BUILD
    printf("[DEBUG] Debug output...\n");
#endif
```

The preprocessor includes/excludes code based on compile-time definitions.

### 4. Generator Expressions

```cmake
$<$<BOOL:${ENABLE_DEBUG}>:DEBUG_BUILD=1>
```

Only generates `DEBUG_BUILD=1` if `ENABLE_DEBUG` is ON.

## 🎓 Learning Outcomes

By studying this project, you'll learn:

### CMake Concepts

- ✅ `option()` - Create boolean configuration options
- ✅ `target_compile_definitions()` - Add `#define` directives
- ✅ Generator expressions - Conditional definition generation
- ✅ Cache variables vs. Options
- ✅ Private vs. Public definitions

### C Concepts

- ✅ Preprocessor conditionals (`#if`, `#ifdef`, `#endif`)
- ✅ Static inline functions
- ✅ Runtime vs. Compile-time configuration
- ✅ Assertions and bounds checking

### Best Practices

- ✅ Keep configuration separated from implementation
- ✅ Use PRIVATE for internal-only definitions
- ✅ Default options sensibly (ON for features, OFF for verbose)
- ✅ Document options in README

## 🔧 Advanced Usage

### Custom Cache Values

Edit `CMakeCache.txt` (not recommended for production):
```
ENABLE_FEATURE_A:BOOL=ON
ENABLE_FEATURE_B:BOOL=OFF
```

### Using Preset (CMake 3.24+)

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

### Cleaning Build

```bash
rm -rf build
```

## 🐛 Troubleshooting

### "CMake 3.28+ required"

Upgrade CMake:
```bash
# Ubuntu/Debian
sudo apt-get install cmake

# macOS
brew install cmake

# Or download from https://cmake.org/download/
```

### Build fails with assertion failure

Either disable assertions or fix the issue:
```bash
cmake -DENABLE_ASSERTIONS=OFF ..
```

## 📜 License

This project is provided as-is for educational purposes.

---

**Happy Building! 🚀**
