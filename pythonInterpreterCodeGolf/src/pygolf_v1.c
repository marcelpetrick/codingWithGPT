/*
 * pygolf v1.0 - a readable reference interpreter for a tiny Python subset.
 *
 * Author: Marcel Petrick <mail@marcelpetrick.it>
 * License: GPLv3 or later.
 *
 * Usage:  ./pygolf_v1 < program.py
 *
 * Design (see ../README.md for the five-minute tour):
 *
 *   1. LOAD      the whole program into one buffer.
 *   2. INDEX     it into a table of lines: text pointer + indentation depth.
 *                Blank lines and comments are dropped, so a block never
 *                gets cut in half by an empty line.
 *   3. EXECUTE   a half-open range of lines, run(lo, hi). Every compound
 *                statement owns the following lines that are indented
 *                deeper than itself; running its body is just a recursive
 *                run() over that sub-range. There is no AST: the line
 *                table *is* the tree, addressed by index ranges.
 *   4. EVALUATE  expressions with a three-level recursive descent parser
 *                working directly on a moving character cursor.
 *
 * The interpreter is a "re-reader": nothing is compiled ahead of time, a
 * loop body is simply re-scanned on every iteration. That is slow and
 * wonderfully small - which is the entire point of this exercise.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SRC    65536
#define MAX_LINES   2048
#define MAX_NAMES    256
#define NAME_LEN      32

static char  source[MAX_SRC];        /* the whole program                  */
static char *text[MAX_LINES];        /* first non-blank char of each line  */
static int   depth[MAX_LINES];       /* its indentation, counted in spaces */
static int   line_count;

static char  names[MAX_NAMES][NAME_LEN];
static long  values[MAX_NAMES];      /* value of a variable                */
static int   def_line[MAX_NAMES];    /* line of its 'def', or -1           */
static int   name_count;

static void die(const char *why, const char *where)
{
    fprintf(stderr, "pygolf: %s at: %s\n", why, where ? where : "<eof>");
    exit(1);
}

/* ---------------------------------------------------------------- names */

/* Return the slot of a name, creating it on first sight. */
static int intern(const char *start, int len)
{
    int i;

    if (len >= NAME_LEN)
        len = NAME_LEN - 1;
    for (i = 0; i < name_count; i++)
        if ((int)strlen(names[i]) == len && !strncmp(names[i], start, len))
            return i;
    if (name_count == MAX_NAMES)
        die("too many names", start);
    memcpy(names[name_count], start, len);
    names[name_count][len] = 0;
    def_line[name_count] = -1;
    return name_count++;
}

static void skip_spaces(const char **p);

static int is_name_char(char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
        || (c >= '0' && c <= '9') || c == '_';
}

/* Read an identifier at the cursor and return its slot. */
static int read_name(const char **p)
{
    const char *start;

    skip_spaces(p);
    start = *p;
    while (is_name_char(**p))
        (*p)++;
    if (*p == start)
        die("name expected", start);
    return intern(start, (int)(*p - start));
}

/* ----------------------------------------------------------- line table */

static void load(void)
{
    int used = (int)fread(source, 1, MAX_SRC - 1, stdin);
    char *p = source;

    source[used] = 0;
    while (*p) {
        char *line = p;
        int   indent = 0;
        char *cut;

        while (*p && *p != '\n')
            p++;
        if (*p)
            *p++ = 0;                       /* terminate this line */

        while (*line == ' ' || *line == '\t')
            line++, indent++;

        cut = line;                         /* drop a trailing comment, */
        {                                   /* but not a '#' inside a string */
            int quoted = 0;
            for (; *cut; cut++) {
                if (*cut == '"' || *cut == '\'')
                    quoted = !quoted;
                if (*cut == '#' && !quoted)
                    break;
            }
            *cut = 0;
        }
        while (cut > line && cut[-1] == ' ')
            *--cut = 0;

        if (!*line)                         /* blank: never enters the table */
            continue;
        if (line_count == MAX_LINES)
            die("program too long", line);
        text[line_count] = line;
        depth[line_count] = indent;
        line_count++;
    }
}

/* First line after i that is no longer part of i's body. */
static int body_end(int i, int limit)
{
    int j = i + 1;

    while (j < limit && depth[j] > depth[i])
        j++;
    return j;
}

/* ---------------------------------------------------------- expressions */

static long parse_cmp(const char **p);

static void skip_spaces(const char **p)
{
    while (**p == ' ' || **p == '\t')
        (*p)++;
}

/* Consume the literal 'word' if it is next; report whether it was. */
static int eat(const char **p, const char *word)
{
    size_t n = strlen(word);

    skip_spaces(p);
    if (strncmp(*p, word, n))
        return 0;
    if (is_name_char(word[n - 1]) && is_name_char((*p)[n]))
        return 0;                       /* 'iffy' is a name, not an 'if' */
    *p += n;
    return 1;
}

static long parse_atom(const char **p)
{
    long v = 0;

    skip_spaces(p);
    if (**p == '(') {
        (*p)++;
        v = parse_cmp(p);
        if (!eat(p, ")"))
            die("')' expected", *p);
        return v;
    }
    if (**p == '-') {
        (*p)++;
        return -parse_atom(p);
    }
    if (**p >= '0' && **p <= '9') {
        while (**p >= '0' && **p <= '9')
            v = v * 10 + *(*p)++ - '0';
        return v;
    }
    return values[read_name(p)];
}

static long parse_product(const char **p)
{
    long v = parse_atom(p);

    for (;;) {
        skip_spaces(p);
        if (**p == '*')      { (*p)++; v *= parse_atom(p); }
        else if (**p == '/') { (*p)++; if (**p == '/') (*p)++;
                               v /= parse_atom(p); }   /* '/' and '//' both truncate */
        else if (**p == '%') { (*p)++; v %= parse_atom(p); }
        else return v;
    }
}

static long parse_sum(const char **p)
{
    long v = parse_product(p);

    for (;;) {
        skip_spaces(p);
        if (**p == '+')      { (*p)++; v += parse_product(p); }
        else if (**p == '-') { (*p)++; v -= parse_product(p); }
        else return v;
    }
}

static long parse_cmp(const char **p)
{
    long v = parse_sum(p);

    for (;;) {
        skip_spaces(p);
        if (eat(p, "=="))      v = (v == parse_sum(p));
        else if (eat(p, "!=")) v = (v != parse_sum(p));
        else if (eat(p, "<=")) v = (v <= parse_sum(p));
        else if (eat(p, ">=")) v = (v >= parse_sum(p));
        else if (**p == '<')   { (*p)++; v = (v < parse_sum(p)); }
        else if (**p == '>')   { (*p)++; v = (v > parse_sum(p)); }
        else return v;
    }
}

/* ----------------------------------------------------------- statements */

static void run(int lo, int hi);

/* Run the body of the function stored in slot 'id'. */
static void call(int id, const char *where)
{
    int def = def_line[id];

    if (def < 0)
        die("unknown function", where);
    run(def + 1, body_end(def, line_count));
}

static void do_print(const char *p)
{
    skip_spaces(&p);
    if (*p == '"' || *p == '\'') {
        char quote = *p++;
        while (*p && *p != quote) {
            if (*p == '\\' && p[1] == 'n')  /* the one escape we bother with */
                putchar('\n'), p += 2;
            else
                putchar(*p++);
        }
    } else if (*p != ')') {
        printf("%ld", parse_cmp(&p));
    }
    putchar('\n');
}

static void run(int lo, int hi)
{
    int i = lo;

    while (i < hi) {
        const char *s = text[i];
        int body = i + 1;
        int end  = body_end(i, hi);

        if (eat(&s, "def")) {                       /* def name(): */
            def_line[read_name(&s)] = i;
            i = end;
        } else if (eat(&s, "if")) {                 /* if cond: [else:] */
            int taken = parse_cmp(&s) != 0;
            int after = end;
            const char *next = end < hi ? text[end] : "";

            if (!strncmp(next, "else", 4))
                after = body_end(end, hi);
            if (taken)
                run(body, end);
            else if (after > end)
                run(end + 1, after);
            i = after;
        } else if (eat(&s, "while")) {              /* while cond: */
            const char *cond = s;

            while (parse_cmp(&s)) {
                run(body, end);
                s = cond;
            }
            i = end;
        } else if (eat(&s, "for")) {                /* for v in range(a[,b[,c]]): */
            int  id = read_name(&s);
            long from = 0, to, step = 1, k;

            if (!eat(&s, "in") || !eat(&s, "range") || !eat(&s, "("))
                die("only 'for v in range(...)' is supported", text[i]);
            to = parse_cmp(&s);
            if (eat(&s, ",")) { from = to; to = parse_cmp(&s); }
            if (eat(&s, ",")) step = parse_cmp(&s);
            for (k = from; step > 0 ? k < to : k > to; k += step) {
                values[id] = k;
                run(body, end);
            }
            i = end;
        } else if (eat(&s, "print")) {              /* print(x) */
            if (!eat(&s, "("))
                die("'(' expected", s);
            do_print(s);
            i++;
        } else {                                    /* name(...) or name = expr */
            int id = read_name(&s);

            skip_spaces(&s);
            if (*s == '(')
                call(id, text[i]);
            else if (*s == '=' && s[1] != '=')
                s++, values[id] = parse_cmp(&s);
            else
                die("statement not understood", text[i]);
            i++;
        }
    }
}

int main(void)
{
    load();
    run(0, line_count);
    return 0;
}
