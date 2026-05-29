#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <stdint.h>

#include "chimera.h"

/* Mix time bits into a cheap non-crypto run ID */
static uint32_t make_run_id(time_t t) {
    uint32_t v = (uint32_t)t;
    v ^= v >> 16;
    v *= 0x45d9f3bU;
    v ^= v >> 16;
    return v;
}

int main(void) {
    chimera_ctx_t ctx = {
        .version   = CHIMERA_VERSION,
        .flavor    = CHIMERA_FLAVOR_NAME,
        .boot_time = time(NULL),
        .run_id    = 0,
    };

    if (ctx.boot_time == (time_t)-1) {
        fputs("chimera: clock unavailable\n", stderr);
        return EXIT_FAILURE;
    }

    ctx.run_id = make_run_id(ctx.boot_time);

    chimera_run(&ctx);
    return EXIT_SUCCESS;
}
