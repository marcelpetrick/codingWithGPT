"""Aggregation and findings.

Every number in the report is produced here, deterministically. The optional
semantic pass may add labels and prose; it never touches these counts.

The guiding rule: when the question is "what is my house style", count *scopes*,
not directives. One verbose repository repeating itself must never outvote three
repositories quietly agreeing.
"""

from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from .discovery import InstructionFile, RepoInfo
from .parse import Directive, ParsedDocument
from .taxonomy import TAXONOMY_VERSION, TOPIC_BY_ID

# Rough conversion; good enough to state a context budget in the report.
BYTES_PER_TOKEN = 4

# A repository with no commit in this many days is dormant: its lack of agent
# instructions costs nothing, so it must not drag the coverage figure down.
ACTIVE_DAYS = 182

# A CLAUDE.md this short next to a longer AGENTS.md is a redirect, not content.
STUB_LINES = 12

# Heading overlap above which two scopes are working from the same template.
TEMPLATE_SIMILARITY = 0.45

# A rule in at least this many scopes is house style rather than local colour.
UNIVERSAL_MIN_SCOPES = 4


@dataclass
class Finding:
    """One statement the survey is prepared to make, with its evidence."""

    id: str
    severity: str  # insight | inconsistency | risk
    title: str
    detail: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ScopeSummary:
    scope: str
    repo: str
    files: list[str]
    kinds: list[str]
    bytes: int
    tokens: int
    directives: int
    hard: int
    soft: int
    topics: list[str]
    last_commit_date: str
    role_mix: dict[str, int]


def _days_between(earlier: str, later: str) -> int | None:
    if not earlier or not later:
        return None
    try:
        a = dt.date.fromisoformat(earlier)
        b = dt.date.fromisoformat(later)
    except ValueError:
        return None
    return (b - a).days


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Survey:
    """The full deterministic result set."""

    def __init__(
        self,
        root: str,
        files: list[InstructionFile],
        repos: list[RepoInfo],
        parsed: dict[str, ParsedDocument],
        duplicate_groups: dict[str, list[InstructionFile]],
    ) -> None:
        self.root = root
        self.files = files
        self.repos = repos
        self.parsed = parsed
        self.duplicate_groups = duplicate_groups
        self.first_party = [f for f in files if not f.vendored and not f.generated]
        self.excluded = [f for f in files if f.vendored or f.generated]
        self.findings: list[Finding] = []
        self._directives: list[tuple[InstructionFile, Directive]] | None = None
        # Coverage is measured against the repositories a person actually
        # maintains, not against every .git directory on disk.
        self.surveyable_repos = [r for r in repos if r.surveyable]
        today = dt.date.today().isoformat()
        self.active_repos = [
            r
            for r in self.surveyable_repos
            if (_days_between(r.last_commit_date, today) or 10**6) <= ACTIVE_DAYS
        ]

    # ------------------------------------------------------------- directives
    def directives(self) -> list[tuple[InstructionFile, Directive]]:
        """Every first-party directive with the file it came from.

        Memoised: a dozen callers walk this list, and the enrichment pass
        annotates the directive objects in place, so they must be the same
        objects every time.
        """
        if self._directives is not None:
            return self._directives
        out: list[tuple[InstructionFile, Directive]] = []
        for item in self.first_party:
            doc = self.parsed.get(item.path)
            if doc is None:
                continue
            out.extend((item, directive) for directive in doc.directives)
        self._directives = out
        return out

    def scopes(self) -> list[str]:
        return sorted({f.scope for f in self.first_party})

    def scope_summaries(self) -> list[ScopeSummary]:
        by_scope: dict[str, list[InstructionFile]] = defaultdict(list)
        for item in self.first_party:
            by_scope[item.scope].append(item)

        summaries: list[ScopeSummary] = []
        for scope, items in sorted(by_scope.items()):
            directives: list[Directive] = []
            roles: Counter[str] = Counter()
            for item in items:
                doc = self.parsed.get(item.path)
                if doc is None:
                    continue
                directives.extend(doc.directives)
                for section in doc.sections:
                    roles[section.role] += 1
            topics = sorted({t for d in directives for t in d.topics})
            total_bytes = sum(i.size_bytes for i in items)
            summaries.append(
                ScopeSummary(
                    scope=scope,
                    repo=items[0].repo_root or "",
                    files=[i.rel_path for i in items],
                    kinds=sorted({i.kind for i in items}),
                    bytes=total_bytes,
                    tokens=total_bytes // BYTES_PER_TOKEN,
                    directives=len(directives),
                    hard=sum(1 for d in directives if d.hardness == "hard"),
                    soft=sum(1 for d in directives if d.hardness == "soft"),
                    topics=topics,
                    last_commit_date=max((i.last_commit_date for i in items), default=""),
                    role_mix=dict(roles),
                )
            )
        return summaries

    # ----------------------------------------------------------------- topics
    def topic_scopes(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for item, directive in self.directives():
            for topic in directive.topics:
                out[topic].add(item.scope)
        return out

    def topic_directive_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for _, directive in self.directives():
            counts.update(directive.topics)
        return counts

    def topic_table(self) -> list[dict[str, Any]]:
        scopes = self.topic_scopes()
        counts = self.topic_directive_counts()
        total_scopes = len(self.scopes()) or 1
        rows: list[dict[str, Any]] = []
        for topic_id, scope_set in scopes.items():
            topic = TOPIC_BY_ID.get(topic_id)
            if topic is None:
                continue
            rows.append(
                {
                    "id": topic_id,
                    "label": topic.label,
                    "group": topic.group,
                    "scopes": len(scope_set),
                    "share": len(scope_set) / total_scopes,
                    "directives": counts[topic_id],
                    "scope_names": sorted(scope_set),
                }
            )
        rows.sort(key=lambda r: (-r["scopes"], -r["directives"], r["label"]))
        return rows

    def repeated_directives(self, min_scopes: int = 2) -> list[dict[str, Any]]:
        """Directives whose normalized form recurs across scopes verbatim.

        The strongest available evidence of a house style: the same sentence
        was carried by hand from one repository to the next.
        """
        by_print: dict[str, dict[str, Any]] = {}
        for item, directive in self.directives():
            entry = by_print.setdefault(
                directive.fingerprint,
                {"text": directive.text, "normalized": directive.normalized, "scopes": set(), "topics": directive.topics},
            )
            entry["scopes"].add(item.scope)
        rows = [
            {"text": e["text"], "normalized": e["normalized"], "scopes": sorted(e["scopes"]), "topics": e["topics"]}
            for e in by_print.values()
            if len(e["scopes"]) >= min_scopes
        ]
        rows.sort(key=lambda r: (-len(r["scopes"]), r["normalized"]))
        return rows

    def instructed_repos(self, kind: str | None = None) -> set[str]:
        """Repositories holding at least one first-party instruction file.

        With ``kind`` given, only files of that kind count — the difference
        between "has any agent instructions" and "has an AGENTS.md" is a
        question people actually ask.
        """
        return {
            f.repo_root
            for f in self.first_party
            if f.repo_root and (kind is None or f.kind == kind)
        }

    def coverage(self) -> dict[str, Any]:
        """Coverage over all repositories and over the actively maintained ones."""
        any_kind = self.instructed_repos()
        agents_md = self.instructed_repos("agents_md")
        active = {r.path for r in self.active_repos}
        return {
            "repos": len(self.surveyable_repos),
            "repos_instructed": len(any_kind),
            "repos_with_agents_md": len(agents_md),
            "active_days": ACTIVE_DAYS,
            "active_repos": len(active),
            "active_instructed": len(any_kind & active),
            "active_with_agents_md": len(agents_md & active),
            "active_share": (len(any_kind & active) / len(active)) if active else 0.0,
            "active_agents_md_share": (len(agents_md & active) / len(active)) if active else 0.0,
            "dormant_repos": len(self.surveyable_repos) - len(active),
        }

    # --------------------------------------------------------------- headline
    def headline(self) -> dict[str, Any]:
        summaries = self.scope_summaries()
        repos_with = {f.repo_root for f in self.first_party if f.repo_root}
        directives = self.directives()
        classified = sum(1 for _, d in directives if d.topics)
        sizes = [s.bytes for s in summaries] or [0]
        return {
            "root": self.root,
            "taxonomy_version": TAXONOMY_VERSION,
            "generated": dt.datetime.now().replace(microsecond=0).isoformat(),
            "repos_scanned": len(self.surveyable_repos),
            "repos_seen": len(self.repos),
            "repos_with_instructions": len(repos_with),
            "coverage": len(repos_with) / len(self.surveyable_repos) if self.surveyable_repos else 0.0,
            **{f"cov_{k}": v for k, v in self.coverage().items()},
            "files_found": len(self.files),
            "files_first_party": len(self.first_party),
            "files_excluded": len(self.excluded),
            "scopes": len(summaries),
            "directives": len(directives),
            "directives_classified": classified,
            "classified_share": classified / len(directives) if directives else 0.0,
            "total_bytes": sum(s.bytes for s in summaries),
            "total_tokens": sum(s.tokens for s in summaries),
            "median_bytes": int(statistics.median(sizes)),
            "max_bytes": max(sizes),
            "hard_directives": sum(s.hard for s in summaries),
            "soft_directives": sum(s.soft for s in summaries),
        }

    # --------------------------------------------------------------- findings
    def compute_findings(self) -> list[Finding]:
        self.findings = []
        self._finding_coverage()
        self._finding_active_coverage()
        self._finding_naming()
        self._finding_placement()
        self._finding_stub_pointer()
        self._finding_duplicates()
        self._finding_template()
        self._finding_staleness()
        self._finding_budget()
        self._finding_universality()
        self._finding_contradictions()
        self._finding_document_mix()
        self._finding_vendored()
        return self.findings

    def _add(self, **kwargs: Any) -> None:
        self.findings.append(Finding(**kwargs))

    def _finding_coverage(self) -> None:
        repos_with = {f.repo_root for f in self.first_party if f.repo_root}
        without = [r for r in self.surveyable_repos if r.path not in repos_with]
        without.sort(key=lambda r: (r.last_commit_date or "", r.commit_count), reverse=True)
        active = [r for r in without if r.last_commit_date]
        self._add(
            id="coverage",
            severity="insight",
            title=f"{len(repos_with)} of {len(self.surveyable_repos)} repositories carry agent instructions",
            detail=(
                f"{len(without)} have none, and {len(self.repos) - len(self.surveyable_repos)} further "
                f"git checkouts (submodules, worktrees, vendored clones, build artefacts and generated "
                f"fixtures) were seen but left out of the denominator. Ranked by last commit, the most active "
                f"uninstructed repositories are the coverage backlog: every agent session there "
                f"starts from zero context."
            ),
            evidence=[f"{r.name} — last commit {r.last_commit_date or 'unknown'}, {r.commit_count} commits" for r in active[:12]],
        )

    def _finding_active_coverage(self) -> None:
        """Coverage among repositories that are actually being worked on."""
        cov = self.coverage()
        if not cov["active_repos"]:
            return
        active = {r.path for r in self.active_repos}
        instructed = self.instructed_repos() & active
        missing = [r for r in self.active_repos if r.path not in instructed]
        missing.sort(key=lambda r: (r.last_commit_date, r.commit_count), reverse=True)
        self._add(
            id="active_coverage",
            severity="insight",
            title=(
                f"{cov['active_instructed']} of {cov['active_repos']} actively maintained "
                f"repositories are instructed ({cov['active_share']:.0%})"
            ),
            detail=(
                f"Counting only repositories with a commit in the last {ACTIVE_DAYS} days, which is "
                f"the population where a missing AGENTS.md actually costs something. "
                f"{cov['dormant_repos']} of the {cov['repos']} repositories are dormant and are "
                f"excluded here. Narrowed to an AGENTS.md specifically — not a CLAUDE.md, a skill "
                f"or a harness config — the figure is {cov['active_with_agents_md']} of "
                f"{cov['active_repos']} ({cov['active_agents_md_share']:.0%}). The uninstructed "
                f"active repositories, most recently touched first:"
            ),
            evidence=[
                f"{r.name} — last commit {r.last_commit_date}, {r.commit_count} commits"
                for r in missing[:15]
            ],
        )

    def _finding_naming(self) -> None:
        names = Counter(f.name for f in self.first_party if f.kind == "agents_md")
        if len(names) > 1:
            self._add(
                id="naming",
                severity="inconsistency",
                title=f"The agents file is spelled {len(names)} different ways",
                detail=(
                    "Filename casing is significant on this filesystem and some harnesses match "
                    "exactly. One spelling has to win; the rest are a coin flip on whether the file "
                    "is read at all."
                ),
                evidence=[f"{name} — {count} scopes" for name, count in names.most_common()],
            )

    def _finding_placement(self) -> None:
        places = Counter(f.location for f in self.first_party if f.kind == "agents_md")
        dirs = Counter(
            f.rel_path.split("/")[-2]
            for f in self.first_party
            if f.kind == "agents_md" and f.location == "docs"
        )
        if len(places) > 1:
            self._add(
                id="placement",
                severity="inconsistency",
                title="Instructions live in the repository root and in three different documentation folders",
                detail=(
                    "Harnesses look in the working directory and walk upward. A file parked in "
                    "docs/ or documents/ is only found when the agent happens to be started there "
                    "or the harness is configured for it."
                ),
                evidence=[f"{place}: {count}" for place, count in places.most_common()]
                + [f"docs folder named {name}/: {count}" for name, count in dirs.most_common()],
            )

    def _finding_stub_pointer(self) -> None:
        by_scope: dict[str, list[InstructionFile]] = defaultdict(list)
        for item in self.first_party:
            by_scope[item.scope].append(item)
        stubs, both, only_claude = [], [], []
        for scope, items in by_scope.items():
            kinds = {i.kind for i in items}
            if {"claude_md", "agents_md"} <= kinds:
                both.append(scope)
                claude = [i for i in items if i.kind == "claude_md"]
                if all(i.line_count <= STUB_LINES for i in claude):
                    stubs.append(f"{scope} — CLAUDE.md is {claude[0].line_count} lines")
            elif "claude_md" in kinds and "agents_md" not in kinds:
                only_claude.append(scope)
        if both:
            self._add(
                id="stub_pointer",
                severity="insight",
                title=f"{len(stubs)} of {len(both)} scopes use CLAUDE.md as a pointer to AGENTS.md",
                detail=(
                    "One canonical file plus a short redirect is a real convention here, and it is "
                    "the right one: it keeps a single source of truth while satisfying both "
                    "harnesses. It is applied consistently where both files exist."
                    + (
                        f" {len(only_claude)} scopes still have a standalone CLAUDE.md with no AGENTS.md."
                        if only_claude
                        else ""
                    )
                ),
                evidence=stubs + [f"{s} — CLAUDE.md only" for s in only_claude],
            )

    def _finding_duplicates(self) -> None:
        if not self.duplicate_groups:
            return
        evidence = []
        for group in self.duplicate_groups.values():
            paths = sorted(f.rel_path for f in group)
            evidence.append(" = ".join(paths))
        self._add(
            id="duplicates",
            severity="risk",
            title=f"{len(self.duplicate_groups)} sets of byte-identical instruction files",
            detail=(
                "The same file exists in more than one place. Copies under build/ are stale the "
                "moment the source changes; copies across repositories drift silently and nothing "
                "reports it."
            ),
            evidence=evidence,
        )

    def _finding_template(self) -> None:
        headings: dict[str, set[str]] = {}
        for item in self.first_party:
            doc = self.parsed.get(item.path)
            if doc is None or len(doc.sections) < 3:
                continue
            headings.setdefault(item.scope, set()).update(
                s.title.lower() for s in doc.sections if s.level <= 2
            )
        pairs = []
        names = sorted(headings)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                score = _jaccard(headings[a], headings[b])
                if score >= TEMPLATE_SIMILARITY:
                    shared = sorted(headings[a] & headings[b])
                    pairs.append((score, a, b, shared))
        pairs.sort(reverse=True)
        if pairs:
            self._add(
                id="implicit_template",
                severity="insight",
                title=f"{len(pairs)} pairs of scopes share most of their section structure",
                detail=(
                    "An unacknowledged template already exists: these files were written by copying "
                    "a predecessor. Naming it and checking it in turns an accident into a standard."
                ),
                evidence=[
                    f"{a} ↔ {b} — {score:.0%} heading overlap: {', '.join(shared[:6])}"
                    for score, a, b, shared in pairs[:10]
                ],
            )

    def _finding_staleness(self) -> None:
        repo_last = {r.path: r.last_commit_date for r in self.repos}
        stale = []
        for item in self.first_party:
            if not item.last_commit_date or not item.repo_root:
                continue
            gap = _days_between(item.last_commit_date, repo_last.get(item.repo_root, ""))
            if gap is not None and gap >= 90:
                stale.append((gap, item))
        stale.sort(key=lambda pair: -pair[0])
        if stale:
            self._add(
                id="staleness",
                severity="risk",
                title=f"{len(stale)} instruction files have not moved in 90+ days of repository activity",
                detail=(
                    "The repository kept changing; the file describing how to work in it did not. "
                    "These are the files most likely to be describing a project that no longer exists."
                ),
                evidence=[
                    f"{item.rel_path} — last touched {item.last_commit_date}, repo active {gap} days since"
                    for gap, item in stale[:12]
                ],
            )

    def _finding_budget(self) -> None:
        summaries = sorted(self.scope_summaries(), key=lambda s: -s.tokens)
        total = sum(s.tokens for s in summaries)
        if not summaries:
            return
        top = summaries[:5]
        share = sum(s.tokens for s in top) / total if total else 0
        self._add(
            id="context_budget",
            severity="insight",
            title=f"Instructions cost roughly {total:,} tokens across {len(summaries)} scopes",
            detail=(
                f"Every session in a scope pays its instruction file before doing any work. The five "
                f"heaviest scopes account for {share:.0%} of the whole corpus. The median scope costs "
                f"{int(statistics.median([s.tokens for s in summaries])):,} tokens; the heaviest costs "
                f"{top[0].tokens:,}."
            ),
            evidence=[f"{s.scope} — ~{s.tokens:,} tokens, {s.directives} directives" for s in top],
        )

    def _finding_universality(self) -> None:
        rows = self.topic_table()
        total = len(self.scopes()) or 1
        universal = [r for r in rows if r["scopes"] >= UNIVERSAL_MIN_SCOPES]
        singleton = [r for r in rows if r["scopes"] == 1]
        self._add(
            id="universality",
            severity="insight",
            title=f"{len(universal)} topics recur across {UNIVERSAL_MIN_SCOPES}+ scopes; {len(singleton)} appear exactly once",
            detail=(
                "The recurring topics are the house style and belong in a shared canonical file. "
                "The single-occurrence topics are project-specific and must stay local — folding "
                "them into a template is how templates become unreadable."
            ),
            evidence=[f"{r['label']} — {r['scopes']}/{total} scopes ({r['share']:.0%})" for r in universal[:15]],
        )

    def _finding_contradictions(self) -> None:
        """Topics where scopes disagree in polarity — candidate decisions."""
        polarity: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"positive": set(), "negative": set()})
        for item, directive in self.directives():
            if directive.hardness != "hard":
                continue
            for topic in directive.topics:
                polarity[topic]["negative" if directive.negative else "positive"].add(item.scope)
        rows = []
        for topic, sides in polarity.items():
            only_pos = sides["positive"] - sides["negative"]
            only_neg = sides["negative"] - sides["positive"]
            if only_pos and only_neg:
                rows.append((topic, sorted(only_pos), sorted(only_neg)))
        rows.sort(key=lambda r: -(len(r[1]) + len(r[2])))
        if rows:
            self._add(
                id="contradictions",
                severity="inconsistency",
                title=f"{len(rows)} topics are phrased with opposite polarity across scopes",
                detail=(
                    "This is the weakest signal in the report and it is kept honest deliberately. "
                    "Negation is usually how a rule is *stated* — 'never push', 'never commit "
                    "without a green pipeline' — not how it is contradicted, so most rows here are "
                    "false positives of the lexical layer. Real contradictions need semantics; this "
                    "list is the shortlist to feed the semantic pass, nothing more."
                ),
                evidence=[
                    f"{TOPIC_BY_ID[t].label}: asserted in {', '.join(p[:3])} — negated in {', '.join(n[:3])}"
                    for t, p, n in rows[:8]
                ],
            )

    def _finding_document_mix(self) -> None:
        roles: Counter[str] = Counter()
        for item in self.first_party:
            doc = self.parsed.get(item.path)
            if doc is None:
                continue
            for section in doc.sections:
                roles[section.role] += 1
        total = sum(roles.values()) or 1
        self._add(
            id="document_mix",
            severity="insight",
            title="Instruction files are three documents wearing one filename",
            detail=(
                f"Of {total} sections across the corpus, {roles.get('rules', 0)/total:.0%} are rules, "
                f"{roles.get('description', 0)/total:.0%} describe the project and "
                f"{roles.get('commands', 0)/total:.0%} are command cheat-sheets. Only the rules "
                "generalise; the description and the commands are why these files cannot simply be "
                "shared between repositories."
            ),
            evidence=[f"{role}: {count} sections ({count/total:.0%})" for role, count in roles.most_common()],
        )

    def _finding_vendored(self) -> None:
        vendored = [f for f in self.files if f.vendored]
        if not vendored:
            return
        by_project: Counter[str] = Counter(f.project for f in vendored)
        total_tokens = sum(f.size_bytes for f in vendored) // BYTES_PER_TOKEN
        self._add(
            id="vendored",
            severity="risk",
            title=f"{len(vendored)} instruction files in the tree were written by somebody else",
            detail=(
                f"Vendored clones and dependency checkouts carry their own AGENTS.md, GEMINI.md and "
                f"skills — roughly {total_tokens:,} tokens of other people's rules. They are excluded "
                f"from every statistic here, but an agent started inside one of those directories "
                f"will still read them."
            ),
            evidence=[f"{project} — {count} files" for project, count in by_project.most_common(8)],
        )

    # ------------------------------------------------------------------ export
    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline(),
            "findings": [asdict(f) for f in self.findings],
            "topics": self.topic_table(),
            "scopes": [asdict(s) for s in self.scope_summaries()],
            "repeated_directives": self.repeated_directives(),
            "files": [
                {k: v for k, v in asdict(f).items() if k != "text"}
                for f in self.files
            ],
            "repos": [asdict(r) for r in self.repos],
            "directives": [
                {
                    "scope": item.scope,
                    "file": item.rel_path,
                    "line": d.line,
                    "text": d.text,
                    "normalized": d.normalized,
                    "fingerprint": d.fingerprint,
                    "heading_path": d.heading_path,
                    "hardness": d.hardness,
                    "negative": d.negative,
                    "form": d.form,
                    "topics": d.topics,
                    "cluster": d.cluster,
                }
                for item, d in self.directives()
            ],
        }
