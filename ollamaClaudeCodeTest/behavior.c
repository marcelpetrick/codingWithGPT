#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * behavior.c - Demonstrates configurable application behavior
 * via CMake cache variables and compiler flags
 */

/* Application build configuration */
#define APP_NAME "BehaviorDemo"
#define VERSION_STRING "1.0.0"

/* Feature flags compiled based on CMake definitions */
#ifdef DEBUG_BUILD
#define DEBUG_ENABLED 1
#else
#define DEBUG_ENABLED 0
#endif

#ifdef ENABLE_LOGGING
#define LOG_ENABLED 1
#else
#define LOG_ENABLED 0
#endif

#ifdef ENABLE_PERFORMANCE
#define PERF_ENABLED 1
#else
#define PERF_ENABLED 0
#endif

#ifdef ENABLE_SECURITY
#define SEC_ENABLED 1
#define APP_NAME_SEC "SecureDemo"
#else
#define SEC_ENABLED 0
#endif

/* Logging macro (condition compiled) */
#ifdef LOG_ENABLED
#define LOG(msg, ...) printf("[LOG] " msg "\n", ##__VA_ARGS__)
#else
#define LOG(msg, ...) do {} while(0)
#endif

/* Debug output macro (condition compiled) */
#ifdef DEBUG_ENABLED
#define DEBUG(msg, ...) printf("[DEBUG] " msg "\n", ##__VA_ARGS__)
#else
#define DEBUG(msg, ...) do {} while(0)
#endif

/* Performance tracking (conditionally compiled) */
#ifdef PERF_ENABLED
#include <time.h>
typedef struct {
    clock_t start;
    clock_t end;
    char name[256];
} perf_t;

#define PERF_START(name) perf_start(name, __func__)
#define PERF_END(name) perf_end(name, __func__)
#define PERF_REPORT() perf_report()

static void perf_start(const char *name, const char *func) {
    perf_t *p = malloc(sizeof(perf_t));
    if (p) {
        p->start = clock();
        strncpy(p->name, name, 255);
        p->name[255] = '\0';
        DEBUG("Performance tracking started: %s (func: %s)", p->name, func);
    }
}

static void perf_end(const char *name, const char *func) {
    perf_t *p = NULL;
    if (PERF_ENABLED && name) {
        p = (perf_t*)malloc(sizeof(perf_t));
        if (p) {
            p->end = clock();
            p->name[255] = '\0';
            printf("[PERF] %s: %fms (func: %s)", p->name,
                   ((double)(p->end - p->start)) / CLOCKS_PER_SEC * 1000.0,
                   func);
            free(p);
        }
    }
}

static void perf_report(void) {
    printf("[PERF] All performance tracking complete.\n");
}

#else
#define perf_start(name, func)
#define perf_end(name, func)
#define PERF_REPORT()
#endif

/* Security feature (conditionally compiled) */
#ifdef SEC_ENABLED
#include <stdbool.h>

static bool sec_validate_input(const char *input, int max_len) {
    if (!input) {
        return false;
    }
    /* Length validation */
    int len = strlen(input);
    if (len >= max_len) {
        return false;
    }
    /* Buffer overflow prevention */
    if (len + 1 < max_len) {
        return true;
    }
    return false;
}
#else
#define sec_validate_input(input, max_len) (true)
#endif

/* Main function demonstrating behavior based on build configuration */
int main(int argc, char *argv[]) {
    int result = 0;

    const char *app_name = PERF_ENABLED ? "PerformanceDemo" : APP_NAME;
    LOG("Application started: %s v%s", app_name, VERSION_STRING);
    DEBUG("Debug mode enabled");
    DEBUG("Performance tracking enabled");

    if (SEC_ENABLED) {
        LOG("Security features enabled");
    }
    DEBUG("Security features disabled");

    if (PERF_ENABLED) {
        LOG("Initializing performance tracking");
        perf_start("init", "main");
    }

    /* Demonstrate conditional logging */
    LOG("This is informational log message");
    DEBUG("This is a debug message (visible only in debug builds)");

    /* Demo input validation */
    const char *test_input = "safe input";
    if (sec_validate_input(test_input, 64)) {
        LOG("Input validation passed");
    } else {
        LOG("Input validation failed");
        result = 1;
    }

    /* Demo memory operation with bounds checking */
    char buffer[64];
    strcpy(buffer, test_input);
    LOG("Buffer copied successfully");
    DEBUG("Buffer contents: [%s]", buffer);

    if (PERF_ENABLED) {
        perf_end("init", "main");
    }

    DEBUG("Application completed with result: %d", result);

    PERF_REPORT();

    LOG("Application finished");

    return result;
}
