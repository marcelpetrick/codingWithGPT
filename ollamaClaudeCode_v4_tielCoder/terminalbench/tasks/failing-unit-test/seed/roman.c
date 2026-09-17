#include "roman.h"
#include <string.h>
/* convert 1..3999 to a Roman numeral into out (caller-provided, >=16 bytes) */
void to_roman(int n, char *out) {
    struct { int v; const char *s; } t[] = {
        {1000,"M"},{900,"CM"},{500,"D"},{400,"CD"},{100,"C"},{90,"XC"},
        {50,"L"},{40,"XL"},{10,"X"},{9,"IX"},{5,"V"},{4,"IV"},{1,"I"}
    };
    out[0] = '\0';
    for (int i = 0; i < 13; i++) {
        while (n > t[i].v) {              /* BUG: should be >=, drops exact hits */
            strcat(out, t[i].s);
            n -= t[i].v;
        }
    }
}
