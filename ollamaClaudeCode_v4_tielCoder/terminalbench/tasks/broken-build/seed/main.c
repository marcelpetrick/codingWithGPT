#include <stdio.h>
#include "strutil.h"
int main(void) {
    const char *msg = "terminal benchmark";
    printf("vowels=%d len=%zu\n", count_vowels(msg), strlen(msg));  /* strlen: no <string.h> */
    return 0;
}
