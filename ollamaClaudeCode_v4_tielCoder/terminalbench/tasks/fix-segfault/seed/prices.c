#include <stdio.h>
#include <string.h>

struct item { const char *name; int cents; };

static const struct item items[] = {
    {"apple", 30}, {"banana", 20}, {"cherry", 75}, {"pear", 45},
};
static const int N = 4;

/* returns a pointer to the item, or NULL if not found */
static const struct item *find(const char *name) {
    for (int i = 0; i < N - 1; i++) {          /* BUG: misses the last item */
        if (strcmp(items[i].name, name) == 0) return &items[i];
    }
    return NULL;
}

int main(void) {
    const struct item *it = find("pear");
    printf("pear costs %d cents\n", it->cents);  /* crashes when it == NULL */
    return 0;
}
