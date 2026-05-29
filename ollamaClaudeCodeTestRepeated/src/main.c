/**
 * main.c - Compile-Time Configuration Demo
 *
 * This program demonstrates how CMake options translate to compile-time
 * definitions that affect runtime behavior.
 *
 * Compile-time definitions available:
 *   DEBUG_BUILD   - When ENABLE_DEBUG is ON
 *   VERBOSE_BUILD - When ENABLE_VERBOSE is ON
 *   FEATURE_A     - When ENABLE_FEATURE_A is ON
 *   FEATURE_B     - When ENABLE_FEATURE_B is ON
 *   BOUNDS_CHECKS - When ENABLE_BOUNDS_CHECKS is ON
 *   ENABLE_ASSERTIONS - When ENABLE_ASSERTIONS is ON
 *   PROJECT_VERSION - Project version
 *   BUILD_MODE_STRING - Build mode name
 *   FEATURE_SET_STRING - Comma-separated feature list
 *   SAFETY_MODE_STRING - Safety mode name
 */

#include <stdio.h>
#include <stdlib.h>

// Feature A: Simple counter with feature A-specific behavior
int feature_a_counter = 0;

// Feature B: Additional statistics structure
typedef struct {
    unsigned int ops_count[4];
    double avg_latency;
} FeatureBStats;

static FeatureBStats feature_b_stats = {0};

// Feature B implementation
void feature_b_operation(int index) {
    if (index >= 0 && index < 4) {
        feature_b_stats.ops_count[index]++;
        // Simulate some work
        volatile int temp = index + 1;
        for (int i = 0; i < temp * temp; i++) {
            temp = i + (index * index);
        }
        feature_b_stats.avg_latency = (feature_b_stats.ops_count[0] + feature_b_stats.ops_count[1] +
                                        feature_b_stats.ops_count[2] + feature_b_stats.ops_count[3]) / 4.0;
    }
}

// Bounds check function (only used when BOUNDS_CHECKS=1)
static int process_with_check(int value) {
#if BOUNDS_CHECKS
    const int MIN_VALUE = 0;
    const int MAX_VALUE = 100;

    if (value < MIN_VALUE) {
        fprintf(stderr, "Warning: Value %d below minimum (%d)\n", value, MIN_VALUE);
        return MIN_VALUE;
    }
    if (value > MAX_VALUE) {
        fprintf(stderr, "Warning: Value %d exceeds maximum (%d)\n", value, MAX_VALUE);
        return MAX_VALUE;
    }
#endif
    return value;
}

// Feature-specific operations based on compile-time flags
void run_feature_operations(void) {
#if FEATURE_A
    printf("[FEATURE A] Running A-specific operations...\n");
    for (int i = 0; i < 3; i++) {
        feature_a_counter++;
        printf("[FEATURE A] Operation A-%d: counter=%d\n", i, feature_a_counter);
    }
#endif

#if FEATURE_B
    printf("[FEATURE B] Running B-specific operations...\n");
    for (int i = 0; i < 4; i++) {
        feature_b_operation(i);
        printf("[FEATURE B] Stats update complete for operation %d\n", i);
    }
#endif
}

#if ENABLE_ASSERTIONS
/**
 * Assert macro wrapper that works with ENABLE_ASSERTIONS
 */
#define SAFE_ASSERT(expr, msg)                          \
    do {                                                 \
        if (!(expr)) {                                   \
            fprintf(stderr, "Assert failed at %s:%d: %s\n", \
                    __FILE__, __LINE__, msg);             \
            exit(1);                                      \
        }                                                 \
    } while (0)
#endif

int main(void) {
    printf("===========================================\n");
    printf("  COMPILE-TIME CONFIGURATION DEMO\n");
    printf("===========================================\n\n");

    // Print build configuration
#if DEBUG_BUILD
    printf("[DEBUG] Debug mode enabled - detailed output\n\n");
#endif

#if VERBOSE_BUILD
    printf("[VERBOSE] Verbose mode enabled\n");
    printf("        Project: %s v%s\n", "CompileTimeConfigDemo", VERSION_STRING);
    printf("        Build:   %s\n", BUILD_MODE_STRING);
    printf("        Features: %s\n", FEATURE_SET_STRING);
    printf("        Safety:   %s\n", SAFETY_MODE_STRING);
    printf("        Assertions: %s\n\n", ENABLE_ASSERTIONS ? "ON" : "OFF");
#else
    printf("Build Configuration:\n");
    printf("  Build Mode:   %s\n", BUILD_MODE_STRING);
    printf("  Features:     %s\n", FEATURE_SET_STRING);
    printf("  Safety Mode:  %s\n", SAFETY_MODE_STRING);
    printf("  Assertions:   %s\n\n", ENABLE_ASSERTIONS ? "ON" : "OFF");
#endif

    printf("-------------------------------------------\n");
    printf("  Runtime Feature Tests\n");
    printf("-------------------------------------------\n\n");

    // Test Feature A operations
    run_feature_operations();

    printf("\n");
    printf("-------------------------------------------\n");
    printf("  Bounds Check Test\n");
    printf("-------------------------------------------\n\n");

    // Test bounds checking
    int test_values[] = {-1, 50, 100, 101};
    for (int i = 0; i < 4; i++) {
        int original = test_values[i];
        int processed = process_with_check(original);
        printf("  Input: %3d -> Output: %3d", original, processed);
#if BOUNDS_CHECKS
        printf(" [CHECKED]");
#else
        printf(" [NO CHECK]");
#endif
        printf("\n");
    }

    // Test Feature B statistics
#if FEATURE_B
    printf("\n-------------------------------------------\n");
    printf("  Feature B Statistics\n");
    printf("-------------------------------------------\n");
    printf("  Total operations: %u\n",
           feature_b_stats.ops_count[0] + feature_b_stats.ops_count[1] +
           feature_b_stats.ops_count[2] + feature_b_stats.ops_count[3]);
    printf("  Average latency:  %f\n", feature_b_stats.avg_latency);
#endif

    // Test assertions
#if ENABLE_ASSERTIONS
    printf("\n-------------------------------------------\n");
    printf("  Assertion Test\n");
    printf("-------------------------------------------\n");
    printf("  Testing safe assertions...\n");
    int test_array[] = {10, 20, 30};
    int size = sizeof(test_array) / sizeof(test_array[0]);

    for (int i = 0; i < size; i++) {
        SAFE_ASSERT(test_array[i] > 0, "Negative value");
        printf("  test_array[%d] = %d: OK\n", i, test_array[i]);
    }
    printf("  All assertions passed!\n");
#else
    printf("\n-------------------------------------------\n");
    printf("  Assertion Test\n");
    printf("-------------------------------------------\n");
    printf("  Assertions disabled - runtime checks skipped\n\n");
#endif

    printf("===========================================\n");
    printf("  Demo Complete!\n");
    printf("===========================================\n");

    return 0;
}
