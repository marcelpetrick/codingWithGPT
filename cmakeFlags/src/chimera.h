#ifndef CHIMERA_H
#define CHIMERA_H

#include <time.h>
#include <stdint.h>

/* Require a flavor to be selected at build time */
#if !defined(FLAVOR_ORACLE) && !defined(FLAVOR_GHOST) && !defined(FLAVOR_TITAN)
#  error "No build flavor defined. Pass -DCHIMERA_FLAVOR=ORACLE|GHOST|TITAN to CMake."
#endif

/* Resolve human-readable flavor name from the CMake-injected define.
   CHIMERA_FLAVOR_NAME is also injected by CMake as a string literal,
   but this macro approach shows how the C side can inspect its own build. */
#if defined(FLAVOR_ORACLE)
#  define ACTIVE_FLAVOR "ORACLE"
#elif defined(FLAVOR_GHOST)
#  define ACTIVE_FLAVOR "GHOST"
#elif defined(FLAVOR_TITAN)
#  define ACTIVE_FLAVOR "TITAN"
#endif

_Static_assert(
    sizeof(time_t) >= 4,
    "time_t must be at least 32 bits wide"
);

typedef struct {
    const char *version;   /* injected by CMake as CHIMERA_VERSION */
    const char *flavor;    /* injected by CMake as CHIMERA_FLAVOR_NAME */
    time_t      boot_time; /* set at startup */
    uint32_t    run_id;    /* pseudo-random run identifier */
} chimera_ctx_t;

/* Each flavor implements exactly this one function */
void chimera_run(const chimera_ctx_t *ctx);

#endif /* CHIMERA_H */
