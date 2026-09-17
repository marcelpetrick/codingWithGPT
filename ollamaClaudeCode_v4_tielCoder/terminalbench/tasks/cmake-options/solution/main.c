#include <stdio.h>
int main(void) {
    printf("BUILD OK\n");
#ifdef FEATURE_GREET
    printf("GREET: enabled\n");
#endif
#ifdef FEATURE_MATH
    printf("MATH: enabled\n");
#endif
#ifdef FEATURE_STATS
    printf("STATS: enabled\n");
#endif
    return 0;
}
