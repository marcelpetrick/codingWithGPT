Create a small, buildable C11 project in this directory using CMake (>= 3.20) that
demonstrates compile-time configuration through CMake options and compiler definitions.

Requirements:
* Provide a CMakeLists.txt and the C source. The executable target must be named `app`.
* Define exactly three boolean options, each OFF by default:
  FEATURE_GREET, FEATURE_MATH, FEATURE_STATS.
* Use option() and target_compile_definitions() to turn each option into a -D macro.
* The program always prints a first line exactly: BUILD OK
* Then, for each feature that was compiled in as ON, it prints exactly one line:
    GREET: enabled
    MATH: enabled
    STATS: enabled
  A feature that is OFF must print nothing for itself.
* It must configure and build cleanly from a fresh build directory with any
  combination of the options.

Build it once yourself to confirm it compiles and runs.
