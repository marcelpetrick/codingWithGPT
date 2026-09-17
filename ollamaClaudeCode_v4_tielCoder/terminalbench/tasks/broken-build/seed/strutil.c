#include "strutil.h"
int count_vowels(const char *s) {
    int n = 0;
    for (const char *p = s; *p; p++) {
        char c = *p;
        if (c=='a'||c=='e'||c=='i'||c=='o'||c=='u') n++;
    }
    return n;
}
