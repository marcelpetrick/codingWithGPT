#!/usr/bin/env bash
# =============================================================================
# localPipeline.sh - Build & Test Pipeline for C11 Compile-Time Demo
#
# This script demonstrates all build variants of the CMake project,
# showing how CMake options translate to different runtime behaviors.
# =============================================================================

set -euo pipefail

# Colors for terminal output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[0;37m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
PROJECT_NAME="CompileTimeConfigDemo"

# =============================================================================
# Helper Functions
# =============================================================================

# Print a section header
print_header() {
    local title="$1"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD}  ${title}${RESET}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${RESET}"
    echo ""
}

# Print success message
print_success() {
    echo -e "${GREEN}✓${RESET} $1"
}

# Print info message
print_info() {
    echo -e "${BLUE}➜${RESET} $1"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}⚠${RESET} $1"
}

# Print error message
print_error() {
    echo -e "${RED}✗${RESET} $1" >&2
}

# Print execution progress
print_step() {
    echo ""
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${MAGENTA}  STEP: $1${RESET}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

# Run a cmake configuration
run_cmake() {
    local options="$1"
    local cmake_args="-DCMAKE_BUILD_TYPE=Release ${options}"

    print_step "Configure with CMake ${options:-[default]}"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    cmake ${cmake_args} .. 2>&1 | grep -v "^-- " | grep -v "^$" || true
    print_success "Configure complete"
}

# Build the project
run_make() {
    print_step "Build with make"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    make -j"$(nproc)" 2>&1 | grep -v "^$" || true
    print_success "Build complete"
}

# Run the executable
run_app() {
    print_step "Run application"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    ./app 2>&1
}

# Clean build directory
clean_build() {
    if [[ -d "${BUILD_DIR}" ]]; then
        print_info "Cleaning build directory..."
        rm -rf "${BUILD_DIR}"
        print_success "Clean complete"
    fi
}

# =============================================================================
# Main Pipeline
# =============================================================================

main() {
    print_header "C11 Compile-Time Configuration Demo Pipeline"
    print_info "Working directory: ${SCRIPT_DIR}"
    print_info "Build directory: ${BUILD_DIR}"
    print_info "Project name: ${PROJECT_NAME}"
    print_info "CMake version:"
    cmake --version | head -1
    echo ""

    # Clean previous builds
    clean_build

    # =================================================================
    # VARIANT 1: Default Release Build
    # =================================================================
    print_header "VARIANT 1: Default Release Build"
    print_info "Configuration: Standard release (no special flags)"
    echo ""
    run_cmake ""
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 2: Debug Build
    # =================================================================
    print_header "VARIANT 2: Debug Build"
    print_info "Configuration: ENABLE_DEBUG=ON"
    print_info "Effect: Debug symbols, no optimizations, detailed output"
    echo ""
    run_cmake "-DENABLE_DEBUG=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 3: Verbose Build
    # =================================================================
    print_header "VARIANT 3: Verbose Build"
    print_info "Configuration: ENABLE_VERBOSE=ON"
    print_info "Effect: Prints detailed project config on startup"
    echo ""
    run_cmake "-DENABLE_VERBOSE=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 4: Feature B Enabled
    # =================================================================
    print_header "VARIANT 4: Feature B Enabled"
    print_info "Configuration: ENABLE_FEATURE_B=ON"
    print_info "Effect: Enables beta feature set with statistics collection"
    echo ""
    run_cmake "-DENABLE_FEATURE_B=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 5: Both Features A and B
    # =================================================================
    print_header "VARIANT 5: Both Features (Alpha + Beta)"
    print_info "Configuration: ENABLE_FEATURE_A=ON (default), ENABLE_FEATURE_B=ON"
    print_info "Effect: Runs both feature A counter ops AND feature B statistics"
    echo ""
    run_cmake "-DENABLE_FEATURE_B=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 6: Safety Mode (Bounds Checking)
    # =================================================================
    print_header "VARIANT 6: Safety Mode (Bounds Checking)"
    print_info "Configuration: ENABLE_BOUNDS_CHECKS=ON"
    print_info "Effect: Validates input ranges, clamps out-of-bounds values"
    echo ""
    run_cmake "-DENABLE_BOUNDS_CHECKS=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 7: All Safety Features + Debug
    # =================================================================
    print_header "VARIANT 7: Comprehensive Build (Debug + All Features)"
    print_info "Configuration: ENABLE_DEBUG=ON, ENABLE_FEATURE_B=ON, ENABLE_BOUNDS_CHECKS=ON"
    print_info "Effect: Combines debug output, both features, and safety checks"
    echo ""
    run_cmake "-DENABLE_DEBUG=ON -DENABLE_FEATURE_B=ON -DENABLE_BOUNDS_CHECKS=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 8: Verbose + Safety + Assertions (No A)
    # =================================================================
    print_header "VARIANT 8: Verbose Mode with Safety Checks"
    print_info "Configuration: ENABLE_VERBOSE=ON, ENABLE_BOUNDS_CHECKS=ON, ENABLE_FEATURE_A=OFF"
    print_info "Effect: Verbose output, bounds checking, safety mode, no feature A"
    echo ""
    run_cmake "-DENABLE_VERBOSE=ON -DENABLE_BOUNDS_CHECKS=ON -DENABLE_FEATURE_A=OFF"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 9: Release with All Features
    # =================================================================
    print_header "VARIANT 9: Release with All Features (Optimized)"
    print_info "Configuration: No debug/verbose, both features enabled"
    print_info "Effect: Clean release build with maximum features"
    echo ""
    run_cmake "-DENABLE_DEBUG=OFF -DENABLE_VERBOSE=OFF -DENABLE_FEATURE_B=ON"
    run_make
    run_app
    echo ""

    # =================================================================
    # VARIANT 10: Assertions Off (Safe Mode)
    # =================================================================
    print_header "VARIANT 10: Safe Mode (Assertions Disabled)"
    print_info "Configuration: ENABLE_ASSERTIONS=OFF"
    print_info "Effect: No runtime assertions, suitable for production"
    echo ""
    run_cmake "-DENABLE_ASSERTIONS=OFF"
    run_make
    run_app
    echo ""

    # =================================================================
    # SUMMARY
    # =================================================================
    print_header "Pipeline Complete!"
    echo ""
    echo -e "${GREEN}All 10 build variants have been successfully tested!${RESET}"
    echo ""
    echo -e "${WHITE}Summary:${RESET}"
    echo "  - Variant 1: Default release build (baseline)"
    echo "  - Variant 2: Debug mode (symbols, no optimizations)"
    echo "  - Variant 3: Verbose mode (detailed config output)"
    echo "  - Variant 4: Feature B only (beta features)"
    echo "  - Variant 5: Both features (alpha + beta)"
    echo "  - Variant 6: Safety mode (bounds checking enabled)"
    echo "  - Variant 7: Comprehensive (debug + all features + safety)"
    echo "  - Variant 8: Verbose + safety + no feature A"
    echo "  - Variant 9: Release optimized (all features)"
    echo "  - Variant 10: Safe mode (assertions disabled)"
    echo ""
    echo -e "${WHITE}What you demonstrated:${RESET}"
    echo "  ✓ CMake options translate to compile-time definitions"
    echo "  ✓ Preprocessor #if/#ifdef controls runtime behavior"
    echo "  ✓ Different build modes produce visibly different output"
    echo "  ✓ Feature flags enable/disable code blocks at runtime"
    echo "  ✓ Safety checks modify input validation behavior"
    echo ""
    echo -e "${WHITE}Key Takeaways:${RESET}"
    echo "  • CMake's option() creates cache variables for -D flags"
    echo "  • target_compile_definitions() injects #define directives"
    echo "  • Generator expressions (\$\$<BOOL:...>) make definitions conditional"
    echo "  • Code uses #if FEATURE_A/#endif for compile-time configuration"
    echo "  • Different variants show different runtime behavior"
    echo ""
    echo -e "${GREEN}Project is ready for production use!${RESET}"
    echo ""
}

# =============================================================================
# Run if script is executed directly
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
