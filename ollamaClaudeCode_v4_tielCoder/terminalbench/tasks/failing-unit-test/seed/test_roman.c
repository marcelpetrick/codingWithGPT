#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "roman.h"
static void eq(int n, const char *want) {
    char b[16]; to_roman(n, b);
    if (strcmp(b, want) != 0) { printf("FAIL to_roman(%d)=%s want %s\n", n, b, want); exit(1); }
}
int main(void) {
    eq(1,"I"); eq(4,"IV"); eq(9,"IX"); eq(10,"X"); eq(40,"XL");
    eq(90,"XC"); eq(400,"CD"); eq(500,"D"); eq(1994,"MCMXCIV"); eq(3888,"MMMDCCCLXXXVIII");
    printf("ALL PASS\n"); return 0;
}
