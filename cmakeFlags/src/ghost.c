#include <stdio.h>

#include "chimera.h"

/* GHOST: minimal, silent, zero waste — compiled with -Os -DNDEBUG */

void chimera_run(const chimera_ctx_t *ctx) {
    /* One line. Nothing more. */
    printf("chimera/%s v%s run=0x%08X\n",
           ctx->flavor, ctx->version, ctx->run_id);
}
