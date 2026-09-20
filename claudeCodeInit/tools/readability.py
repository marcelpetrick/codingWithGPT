#!/usr/bin/env python3
"""Measure the paper against the clear-writing principles it claims to follow.

Not a proof that a reader understood something -- no formula can show that. It
measures the four mechanical properties the principles reduce to, so the claim
"this is written clearly" becomes falsifiable instead of a matter of taste:

    simple language   -> long-word share, Flesch reading ease
    active voice      -> passive constructions per 100 sentences
    short sentences   -> median length, share over 30 words
    logical order     -> claim-before-evidence, checked per section

Usage:  python3 tools/readability.py paper.tex [--verbose]
Exit code 1 if any target is missed, so it can gate a build.
"""
import re, sys, statistics

TARGETS = {                      # chosen for a technical reader, not a general one
    "flesch_min":        35.0,   # academic prose typically lands 15-30
    "median_sentence":   20.0,   # words
    "long_sentence_pct": 12.0,   # share of sentences over 30 words
    "passive_per_100":   12.0,   # passive constructions per 100 sentences
    "longword_pct":      22.0,   # share of words with 3+ syllables
}

# ---------------------------------------------------------------- LaTeX -> prose
DROP_ENVS = ("table", "tabular", "figure", "thebibliography")   # minipage holds
#                                              the abstract and the principle box -- both are prose the reader reads

def strip_latex(src: str) -> str:
    if "\\begin{document}" in src:
        src = src.split("\\begin{document}", 1)[1]
    src = src.split("\\end{document}", 1)[0]
    src = re.sub(r"(?<!\\)%.*", "", src)                       # comments
    for env in DROP_ENVS:                                       # floats and tables
        src = re.sub(r"\\begin\{%s\*?\}.*?\\end\{%s\*?\}" % (env, env),
                     " ", src, flags=re.S)
    src = re.sub(r"\\(cite|ref|label|includegraphics|caption|bibitem)\s*(\[[^\]]*\])?\{[^}]*\}",
                 " ", src)
    src = re.sub(r"\\(fcolorbox|colorbox|definecolor)\{[^}]*\}\{[^}]*\}", " ", src)
    src = src.replace("\\$", "\x01")                             # escaped currency, not math
    src = re.sub(r"\$[^$]*\$", "N", src)                        # math -> one token
    src = src.replace("\x01", "$")
    src = re.sub(r"\\(section|subsection|subsection\*|paragraph)\*?\{([^}]*)\}",
                 r"\n\n@@\2@@\n\n", src)                        # keep headings, tagged
    src = re.sub(r"\\(emph|textbf|textit|texttt|underline|textsc)\{([^{}]*)\}", r"\2", src)
    src = re.sub(r"\\(emph|textbf|textit|texttt)\{([^{}]*)\}", r"\2", src)   # one nesting level
    # environment boundaries are block boundaries, not mid-sentence text
    src = re.sub(r"\\begin\{[a-zA-Z*]+\}(?:\[[^\]]*\]|\{[^{}]*\})*", ". ", src)
    src = re.sub(r"\\end\{[a-zA-Z*]+\}", ". ", src)
    src = re.sub(r"\\[a-zA-Z@]+\s*(\[[^\]]*\])?", " ", src)     # remaining commands
    src = src.replace("---", "—").replace("--", "–")
    src = re.sub(r"[{}~]", " ", src)
    src = src.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_")
    return re.sub(r"[ \t]+", " ", src)

def strip_markdown(src: str) -> str:
    src = re.sub(r"```.*?```", " ", src, flags=re.S)
    src = re.sub(r"^\|.*$", "", src, flags=re.M)                # tables
    # blockquotes carry quoted source material -- tag them before the marker is
    # stripped, so drop_quotes can separate them from the author's own prose
    src = re.sub(r"^\\s*>\\s?(.*)$", "\u201c\\1\u201d", src, flags=re.M)
    src = re.sub(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", ". ", src, flags=re.M)   # rules are breaks
    src = re.sub(r"^#{1,6}\s*(.+)$", r"\n\n@@\1@@\n\n", src, flags=re.M)
    src = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", src)           # links
    src = re.sub(r"[*_`>]", "", src)
    return src

QUOTE_RE = re.compile(r"``[^`]{2,600}?''" + "|" + "\u201c[^\u201d]{2,600}\u201d" + "|" + r'"[^"\n]{2,400}"')

def drop_quotes(text: str) -> str:
    """Remove quoted source material.

    Quotations are evidence, not prose choices: we cannot shorten someone else's
    sentence or move it out of the passive without misquoting them. They still
    count toward what the reader reads, so the report gives both figures --
    but the targets apply to the prose the author actually controls.
    """
    return QUOTE_RE.sub(" quoted ", text)   # a placeholder that adds no punctuation

# ---------------------------------------------------------------- tokenising
ABBREV = r"(?:e\.g|i\.e|cf|vs|et al|Fig|Tab|Sec|Dr|Prof|approx|no|No|pp|Mr|Ms)"

def sentences(text: str):
    text = re.sub(r"@@[^@]*@@", " ", text)                       # headings are not sentences
    # a list item is its own unit, whether or not it ends in a full stop
    text = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", ". ", text, flags=re.M)
    text = re.sub(r"\b%s\." % ABBREV, lambda m: m.group(0).replace(".", "\x00"), text)
    text = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)              # 2.8, v2.1.278
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z(\u201c/\d])", text)
    out = []
    for p in parts:
        p = p.replace("\x00", ".").strip()
        if len(re.findall(r"[A-Za-z]{2,}", p)) >= 3:             # ignore stubs
            out.append(p)
    return out

def words(s: str):
    return re.findall(r"[A-Za-z][A-Za-z'\-]*", s)

VOWELS = "aeiouy"
def syllables(w: str) -> int:
    w = w.lower().strip("'-")
    if not w:
        return 1
    n, prev = 0, False
    for ch in w:
        v = ch in VOWELS
        if v and not prev:
            n += 1
        prev = v
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    if w.endswith(("ed",)) and n > 1 and not re.search(r"[td]ed$", w):
        n -= 1
    return max(1, n)

# ---------------------------------------------------------------- passive voice
BE = r"(?:is|are|was|were|be|been|being|am)"
PARTICIPLE = (r"(?:[a-z]+ed|shown|known|given|taken|seen|done|made|found|held|"
              r"written|built|drawn|kept|left|put|read|set|sent|told|thought|"
              r"understood|driven|chosen|proven|borne)")
PASSIVE = re.compile(r"\b%s\b(?:\s+(?:not|also|already|never|only|still|often|"
                     r"then|thus|now|clearly|explicitly|entirely|largely))?\s+%s\b"
                     % (BE, PARTICIPLE))

def passives(s: str):
    return PASSIVE.findall(s.lower()), [m.group(0) for m in PASSIVE.finditer(s.lower())]

# ---------------------------------------------------------------- metrics
def analyse(text: str):
    sents = sentences(text)
    lens = [len(words(s)) for s in sents]
    allw = [w for s in sents for w in words(s)]
    syl = [syllables(w) for w in allw]
    nlong = sum(1 for k in syl if k >= 3)
    npass, examples = 0, []
    for s in sents:
        _, hits = passives(s)
        if hits:
            npass += len(hits)
            examples.append((hits[0], s))
    W, S, Y = len(allw), len(sents), sum(syl)
    flesch = 206.835 - 1.015 * (W / S) - 84.6 * (Y / W) if S and W else 0.0
    fk = 0.39 * (W / S) + 11.8 * (Y / W) - 15.59 if S and W else 0.0
    return {
        "sentences": S, "words": W,
        "median_sentence": statistics.median(lens) if lens else 0,
        "mean_sentence": W / S if S else 0,
        "max_sentence": max(lens) if lens else 0,
        "long_sentence_pct": 100 * sum(1 for l in lens if l > 30) / S if S else 0,
        "longword_pct": 100 * nlong / W if W else 0,
        "flesch": flesch, "fk_grade": fk,
        "passive_per_100": 100 * npass / S if S else 0,
        "passive_n": npass,
        "passive_examples": examples,
        "longest": max(sents, key=lambda s: len(words(s))) if sents else "",
    }

def sections(text: str):
    parts = re.split(r"@@([^@]*)@@", text)
    out, i = [], 1
    while i < len(parts):
        out.append((parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ""))
        i += 2
    return out

# ---------------------------------------------------------------- report
def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "paper.tex"
    verbose = "--verbose" in sys.argv
    raw = open(path, encoding="utf-8").read()
    full = strip_latex(raw) if path.endswith(".tex") else strip_markdown(raw)
    text = drop_quotes(full)          # targets apply to the author's own prose
    m = analyse(text)
    m_all = analyse(full)

    print("clear-writing report for %s" % path)
    print("=" * 64)
    print("targets apply to authored prose; quoted source material is reported "
          "separately\nbecause rewriting a quotation would misquote it.\n")
    rows = [
        ("Flesch reading ease",      m["flesch"],             TARGETS["flesch_min"],        "ge", "%.1f"),
        ("Flesch-Kincaid grade",     m["fk_grade"],           None,                          None, "%.1f"),
        ("Median sentence (words)",  m["median_sentence"],    TARGETS["median_sentence"],   "le", "%.0f"),
        ("Mean sentence (words)",    m["mean_sentence"],      None,                          None, "%.1f"),
        ("Longest sentence (words)", m["max_sentence"],       None,                          None, "%.0f"),
        ("Sentences over 30 words",  m["long_sentence_pct"],  TARGETS["long_sentence_pct"], "le", "%.1f%%"),
        ("Words of 3+ syllables",    m["longword_pct"],       TARGETS["longword_pct"],      "le", "%.1f%%"),
        ("Passives per 100 sents",   m["passive_per_100"],    TARGETS["passive_per_100"],   "le", "%.1f"),
    ]
    failed = 0
    for name, val, target, cmp_, fmt in rows:
        mark = "     "
        if target is not None:
            ok = val >= target if cmp_ == "ge" else val <= target
            failed += (not ok)
            mark = " PASS" if ok else " FAIL"
        tgt = "" if target is None else ("  (target %s %g)" % ("\u2265" if cmp_ == "ge" else "\u2264", target))
        print("%-26s %10s%s%s" % (name, fmt % val, mark, tgt))
    print("-" * 64)
    print("%d sentences, %d words of authored prose" % (m["sentences"], m["words"]))
    print("including quotations: flesch %.1f, median %.0f w, %.1f%% over 30 w, "
          "%.1f passives/100"
          % (m_all["flesch"], m_all["median_sentence"],
             m_all["long_sentence_pct"], m_all["passive_per_100"]))

    secs = sections(text)
    if secs:
        print("\nper section (median sentence / passives / longest)")
        for name, body in secs:
            sm = analyse(drop_quotes(body))
            if sm["sentences"] < 2:
                continue
            print("  %-34s %3.0f w  %4.1f/100  %3.0f w"
                  % (name[:34], sm["median_sentence"], sm["passive_per_100"], sm["max_sentence"]))

    if verbose:
        print("\nlongest sentence (%d words):\n  %s" % (m["max_sentence"], m["longest"]))
        if m["passive_examples"]:
            print("\npassive constructions (%d):" % m["passive_n"])
            for hit, s in m["passive_examples"][:25]:
                print("  [%s]  %s" % (hit, s[:110] + ("..." if len(s) > 110 else "")))
    print("\n%s" % ("all targets met" if not failed else "%d target(s) missed" % failed))
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
