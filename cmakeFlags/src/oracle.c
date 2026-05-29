#include <stdio.h>
#include <time.h>
#include <stdint.h>

#include "chimera.h"

/* ORACLE: verbose, mystical, time-aware — compiled with -O2 -DDEBUG_VERBOSE */

static void print_banner(void) {
    puts("╔══════════════════════════════════════════════╗");
    puts("║          C H I M E R A  ::  O R A C L E      ║");
    puts("╚══════════════════════════════════════════════╝");
}

static void print_timestamp(time_t t) {
    char buf[64];
    struct tm *tm_info = localtime(&t);
    if (!tm_info) {
        puts("  [time] — indeterminate");
        return;
    }
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S %Z", tm_info);
    printf("  Timestamp : %s\n", buf);
}

static void print_prophecy(uint32_t run_id) {
    /* A deterministic "prophecy" derived from the run ID.
       Pure flavour — shows how compile-time defines can gate runtime paths. */
    static const char *const prophecies[] = {
        "The mountain does not move; it waits for the river.",
        "That which is compiled with wisdom runs without regret.",
        "Optimization is the art of doing less to achieve more.",
        "Every flag you pass is a vow to the compiler.",
        "Silence the warnings; they are the voice of future bugs.",
    };
    const size_t n = sizeof(prophecies) / sizeof(prophecies[0]);
    printf("  Prophecy  : \"%s\"\n", prophecies[run_id % n]);
}

void chimera_run(const chimera_ctx_t *ctx) {
    print_banner();
    putchar('\n');

    printf("  Version   : %s\n", ctx->version);
    printf("  Flavor    : %s\n", ctx->flavor);
    printf("  Run ID    : 0x%08X\n", ctx->run_id);
    print_timestamp(ctx->boot_time);
    putchar('\n');

#if DEBUG_VERBOSE
    puts("  ── Verbose diagnostics (DEBUG_VERBOSE=1) ───────────────");
    printf("  sizeof(time_t)        = %zu bytes\n", sizeof(time_t));
    printf("  sizeof(chimera_ctx_t) = %zu bytes\n", sizeof(chimera_ctx_t));
    printf("  Compiler C standard   : C%ld\n", __STDC_VERSION__ / 100 % 100);
    puts("  ────────────────────────────────────────────────────────");
    putchar('\n');
#endif

    print_prophecy(ctx->run_id);
    putchar('\n');
    puts("  [ORACLE] The vision is clear. All systems nominal.");
    putchar('\n');
}
