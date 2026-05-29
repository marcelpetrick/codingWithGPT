#include <stdio.h>
#include <time.h>

#include "chimera.h"

/* TITAN: loud, proud, maximum output — compiled with -O3 */

static void print_banner(void) {
    puts("");
    puts("  ████████╗██╗████████╗ █████╗ ███╗   ██╗");
    puts("     ██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║");
    puts("     ██║   ██║   ██║   ███████║██╔██╗ ██║");
    puts("     ██║   ██║   ██║   ██╔══██║██║╚██╗██║");
    puts("     ██║   ██║   ██║   ██║  ██║██║ ╚████║");
    puts("     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝");
    puts("");
}

static void print_uptime_since(time_t t) {
    char buf[64];
    struct tm *tm_info = localtime(&t);
    if (tm_info) {
        strftime(buf, sizeof(buf), "%H:%M:%S", tm_info);
        printf("  Launched    : %s\n", buf);
    }
}

void chimera_run(const chimera_ctx_t *ctx) {
    print_banner();

    puts("  ╔══════════════════════════════════════════╗");
    puts("  ║     *** TITAN FORCE ENGAGED ***           ║");
    puts("  ╠══════════════════════════════════════════╣");
    printf("  ║  Flavor      : %-25s║\n", ctx->flavor);
    printf("  ║  Version     : %-25s║\n", ctx->version);
    printf("  ║  Run ID      : 0x%08X%-17s║\n", ctx->run_id, "");
    puts("  ║  Opt level   : -O3  [MAXIMUM PERFORMANCE] ║");

#if PERFORMANCE_MODE
    puts("  ║  Perf mode   : ENABLED                    ║");
#endif

    puts("  ╠══════════════════════════════════════════╣");
    print_uptime_since(ctx->boot_time);
    puts("  ╚══════════════════════════════════════════╝");
    puts("");
    puts("  [!!] The Titan rises. Resistance is futile.");
    puts("  [!!] sizeof(void*) is a privilege, not a right.");
    puts("");
}
