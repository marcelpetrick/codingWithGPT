"""Layer 3a — the deterministic lexicon classifier.

Handles the head of the distribution: topics whose vocabulary is stable enough
to recognise with patterns. Auditable, reproducible, fast. What it cannot do —
discover unanticipated categories, resolve paraphrase, spot contradictions — is
left to the optional semantic pass in ``llm.py``.

The taxonomy is data, kept here so it versions with the code. Every topic is a
group, an id, a human label, and the patterns that identify it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TAXONOMY_VERSION = "1"


@dataclass(frozen=True)
class Topic:
    id: str
    group: str
    label: str
    patterns: tuple[str, ...]
    excludes: tuple[str, ...] = ()


TOPICS: tuple[Topic, ...] = (
    # ---------------------------------------------------------------- commits
    Topic("commit.conventional", "Commits", "Conventional Commits", (
        r"conventional commit",
        r"\bfeat\(|\bfix\(|\bchore\(|\bdocs\(|\brefactor\(",
        r"\b(feat|fix|chore|docs|refactor|test|build|ci|perf|style)\s*(\([a-z0-9_-]+\))?\s*:",
        r"commit (message|subject) (format|convention|style)",
        r"type\(scope\)",
    )),
    Topic("commit.atomic", "Commits", "One concern per commit", (
        r"atomic commit", r"one concern per commit", r"single concern",
        r"one reason to change", r"one logical change", r"do not mix .* (in|into) (one|a single) commit",
        r"separate commits?", r"split .* into .* commits",
    )),
    Topic("commit.body", "Commits", "Commit body explains why", (
        r"commit body", r"body (of the commit|is the point)", r"explain why",
        r"why, not what", r"wrap (the )?(body|lines) at \d+", r"subject line",
        r"imperative mood",
    )),
    Topic("commit.no_agent_credit", "Commits", "No agent co-author or emoji in commits", (
        r"co-authored-by", r"generated with claude", r"do not (add|mention|credit)",
        r"no emoji in commit", r"emoji.*commit", r"commit.*emoji",
    )),
    Topic("commit.frequency", "Commits", "Commit early and often", (
        r"commit (early|often|after each|per step)", r"commit at (every|each)",
        r"do not batch .* commits?", r"every (change|task) (gets|ends in) a commit",
    )),
    # -------------------------------------------------------------------- vcs
    Topic("vcs.never_push", "Version control", "Never push without being asked", (
        r"never push", r"do not push", r"don't push", r"no(t)? .*push to (remote|origin)",
        r"push only (when|if|after)", r"pushing is (the user|manual|not)",
    )),
    Topic("vcs.no_history_rewrite", "Version control", "No force-push, amend or rebase", (
        r"force[- ]push", r"--force", r"rewrite (the )?history", r"do not amend",
        r"never amend", r"no rebase", r"do not rebase", r"reset --hard",
    )),
    Topic("vcs.branching", "Version control", "Branching policy", (
        r"branch nam", r"feature branch", r"work on a branch", r"do not commit (directly )?to (main|master)",
        r"branch off", r"create a branch",
    )),
    Topic("vcs.identity", "Version control", "Git identity / authorship", (
        r"git identity", r"user\.name", r"user\.email", r"author (name|identity)",
        r"commit as",
    )),
    Topic("vcs.clean_tree", "Version control", "Keep the working tree clean", (
        r"working tree (must be )?clean", r"git status", r"do not commit .*(artifact|generated|build output)",
        r"gitignore", r"untracked files",
    )),
    # --------------------------------------------------------------- versions
    Topic("version.bump", "Versioning", "Bump the version with the change", (
        r"bump the version", r"version bump", r"bumps? the (project )?version",
        r"increment the version", r"every commit .* version",
    )),
    Topic("version.semver", "Versioning", "Semantic versioning", (
        r"semantic version", r"semver", r"major\.minor\.patch", r"patch (level|version)",
    )),
    Topic("version.changelog", "Versioning", "Maintain a changelog", (
        r"changelog", r"release notes", r"keep a changelog",
    )),
    # ------------------------------------------------------------ quality gate
    Topic("gate.before_commit", "Quality gate", "Run the gate before committing", (
        r"before (every |each |any )?commit", r"quality gate", r"green pipeline",
        r"gate (must|has to) (be )?(green|pass)", r"do not commit (unless|until|without)",
        r"pre-?commit", r"definition of done",
    )),
    Topic("gate.tests", "Quality gate", "Tests must pass / write tests", (
        r"\btests? (must|have to|shall) pass", r"run the (unit )?tests", r"pytest|ctest|gtest|junit|jest|vitest",
        r"all tests? (are )?green", r"add (a )?tests?", r"unit test", r"test coverage",
        r"write tests",
    )),
    Topic("gate.coverage", "Quality gate", "Coverage threshold", (
        r"coverage (threshold|target|must|of \d+)", r"\d+\s?% (line )?coverage", r"gcov|lcov|coverage\.py",
    )),
    Topic("gate.lint_format", "Quality gate", "Formatting and linting", (
        r"clang-format|black|ruff|flake8|pylint|eslint|prettier|dartfmt|gofmt|rustfmt|cppcheck|shellcheck",
        r"\bformatting\b", r"\bformatter\b", r"(auto|code|source)[- ]format", r"format the (code|source)",
        r"\blint(er|ing)?\b", r"style check",
    )),
    Topic("gate.typecheck", "Quality gate", "Static typing", (
        r"mypy|pyright|type hints?|type annotation|strict typing|typing\.",
        r"static analysis", r"clang-tidy",
    )),
    Topic("gate.ci", "Quality gate", "CI must be green", (
        r"\bci\b", r"pipeline", r"github action", r"gitlab[- ]ci", r"workflow (must|run)",
        r"continuous integration",
    )),
    Topic("gate.build", "Quality gate", "The build must succeed", (
        r"build (must|has to) (succeed|pass|be clean)", r"no (compiler )?warnings",
        r"warnings? as errors", r"-werror",
    )),
    # ------------------------------------------------------------ dependencies
    Topic("deps.exact_pins", "Dependencies", "Pin dependencies exactly", (
        r"exact (version|pin)", r"pin(ned|s)? (to|the|every|all)", r"no (version )?ranges",
        r"do not use \^|caret|tilde range", r"==\s?\d+\.\d+",
    )),
    Topic("deps.update_policy", "Dependencies", "Dependency update policy", (
        r"update (the )?dependenc", r"upgrade (the )?dependenc", r"latest stable",
        r"do not add (a )?(new )?dependenc", r"minimi[sz]e dependenc", r"third[- ]party librar",
    )),
    Topic("deps.stdlib_first", "Dependencies", "Prefer the standard library", (
        r"standard library", r"stdlib", r"no external dependenc", r"zero dependenc",
        r"without (any )?(extra|third-party) (package|librar)",
    )),
    # ------------------------------------------------------------- language
    Topic("lang.english_only", "Language and voice", "English only", (
        r"english is mandatory", r"in english", r"english for (all|every)",
        r"do not use non-english", r"write .* in english",
    )),
    Topic("style.no_emoji", "Language and voice", "No emoji", (
        r"no emoji", r"without emoji", r"avoid emoji", r"emoji.*(not|never|forbidden)",
    )),
    Topic("style.tone", "Language and voice", "Plain, unhyped prose", (
        r"\btone\b", r"marketing (speak|language)", r"no hype", r"plain (english|language|prose)",
        r"do not (over)?sell", r"superlative", r"voice and naming", r"avoid adjectives",
    )),
    # ----------------------------------------------------------------- code
    Topic("code.style", "Code", "Code style and naming", (
        r"naming convention", r"snake_case|camelcase|pascalcase|kebab-case",
        r"line length|\d{2,3} characters", r"code style", r"indent",
    )),
    Topic("code.comments", "Code", "Comments and docstrings", (
        r"docstring", r"\bcomments?\b", r"doxygen", r"document (every|each|all) (public |)?(function|class|method)",
        r"self-documenting",
    )),
    Topic("code.simplicity", "Code", "Keep it small and simple", (
        r"keep it simple", r"smallest (change|diff)", r"minimal (change|diff)",
        r"do not over-?engineer", r"yagni", r"no premature", r"function .* (short|small)",
        r"single responsibility",
    )),
    Topic("code.no_dead_code", "Code", "No dead or commented-out code", (
        r"dead code", r"commented[- ]out", r"unused (code|import|variable)", r"leftover",
        r"todo comments?",
    )),
    Topic("arch.layering", "Code", "Architecture boundaries", (
        r"layer(ing|s)?\b", r"boundar(y|ies)", r"must not (import|depend on|know)",
        r"separation of concerns", r"decoupl", r"dependency direction",
    )),
    # ------------------------------------------------------------- process
    Topic("process.verify", "Working process", "Verify before claiming success", (
        r"before you claim", r"do not claim", r"verif(y|ication)", r"prove", r"evidence",
        r"actually (run|test)", r"never (say|report|assume) .* (works|passed|done)",
        r"do not (assume|guess)",
    )),
    Topic("process.ask_when_unsure", "Working process", "Ask or stop when unsure", (
        r"when (you are |you're )?unsure", r"if (you are |you're )?(unsure|uncertain|blocked)",
        r"\bask (the user|first|me|before)", r"do not guess", r"stop and (ask|report)",
        r"\bblocked\b",
    )),
    Topic("process.no_scope_creep", "Working process", "Stay inside the task", (
        r"scope creep", r"out of scope", r"stay (in|within) scope", r"do not (add|refactor|change) .* unrelated",
        r"only (change|touch) what", r"unrelated change", r"do not rewrite",
    )),
    Topic("process.read_first", "Working process", "Read context before acting", (
        r"read (this|the .*(file|doc)|first)", r"before (you )?(start|begin|edit|change)",
        r"understand the", r"look at the existing",
    )),
    Topic("process.loop", "Working process", "A defined per-task loop", (
        r"per-task loop", r"execution loop", r"work format", r"task loop",
        r"in this order", r"one task at a time", r"(follow|repeat) the (loop|cycle|sequence)",
    )),
    Topic("process.report_back", "Working process", "Report back in a fixed format", (
        r"report back", r"output format", r"summar(y|ise|ize) .* (after|at the end)",
        r"reporting", r"hand ?off", r"what to (tell|report)",
    )),
    Topic("agent.subagents", "Working process", "Subagents and parallelism", (
        r"sub-?agent", r"in parallel", r"fan out", r"orchestrat", r"worktree",
        r"parallel agents?",
    )),
    # --------------------------------------------------------------- docs
    Topic("docs.keep_true", "Documentation", "Keep documentation true", (
        r"keep .* (up to date|current|true)", r"update the readme", r"readme must",
        r"documentation (must|has to) (match|stay|be)", r"stale doc", r"docs? discipline",
    )),
    Topic("docs.where", "Documentation", "Where documentation lives", (
        r"documentation (lives|goes|belongs)", r"\bdocs?/\b", r"documents?/", r"vision\.md",
        r"architecture decision record|\badr\b",
    )),
    # ----------------------------------------------------------- safety
    Topic("safety.secrets", "Safety and privacy", "Never commit secrets", (
        r"\bsecrets?\b", r"api[- ]key", r"credential", r"token .* (commit|repo)",
        r"\.env\b", r"password",
    )),
    Topic("safety.privacy", "Safety and privacy", "Personal data handling", (
        r"privacy", r"personal data", r"\bpii\b", r"anonymi[sz]", r"real names?",
        r"do not (publish|upload|share) .* (data|log)", r"gdpr",
    )),
    Topic("safety.destructive", "Safety and privacy", "No destructive commands", (
        r"rm -rf", r"destructive", r"do not delete", r"never remove", r"irreversible",
        r"\bsudo\b",
    )),
    Topic("safety.network", "Safety and privacy", "Network and offline policy", (
        r"offline", r"no network", r"without internet", r"do not (call|hit) .* api",
        r"local (only|model)", r"air-?gap",
    )),
    Topic("safety.license", "Safety and privacy", "Licence and copyright", (
        r"licen[cs]e", r"copyright", r"gpl|mit licen|apache-2", r"spdx", r"licence header",
    )),
    # ------------------------------------------------------------ toolchain
    Topic("env.toolchain", "Toolchain", "Toolchain and environment", (
        r"virtual ?env|venv|\buv\b|poetry|conda", r"python 3\.\d+", r"\bcmake\b|\bninja\b|\bmakefile\b|\bmake -",
        r"docker", r"toolchain", r"node \d|npm|pnpm|yarn", r"requirements\.txt|pyproject",
    )),
    Topic("env.reproducible", "Toolchain", "Reproducible and scriptable", (
        r"reproducib", r"deterministic", r"scriptable", r"one command", r"idempotent",
        r"same (result|output) every",
    )),
    Topic("env.open_source", "Toolchain", "Open-source tooling only", (
        r"open[- ]source", r"foss", r"no proprietary", r"free software",
    )),
    # ------------------------------------------------------------ structure
    Topic("repo.layout", "Repository", "Repository layout", (
        r"repository layout", r"directory (structure|layout)", r"file layout",
        r"where .* (lives?|belongs?|goes)", r"folder structure", r"module layout",
    )),
    Topic("repo.hygiene", "Repository", "Repository hygiene", (
        r"housekeeping", r"hygiene", r"do not (leave|litter)", r"temporary files",
        r"clean up", r"scratch",
    )),
    Topic("i18n.localization", "Repository", "Localization", (
        r"localis|localiz|\bi18n\b", r"translation", r"language file", r"\blocale\b",
    )),
    Topic("ui.quality", "Repository", "UI and interaction quality", (
        r"\bui\b|\bgui\b|user interface", r"layout .* (quality|must)", r"accessib",
        r"responsive", r"widget",
    )),
)

_COMPILED: tuple[tuple[Topic, tuple[re.Pattern[str], ...], tuple[re.Pattern[str], ...]], ...] = tuple(
    (
        topic,
        tuple(re.compile(p, re.IGNORECASE) for p in topic.patterns),
        tuple(re.compile(p, re.IGNORECASE) for p in topic.excludes),
    )
    for topic in TOPICS
)

TOPIC_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}
GROUPS: tuple[str, ...] = tuple(dict.fromkeys(t.group for t in TOPICS))


def classify(normalized_text: str) -> list[str]:
    """Every topic whose lexicon matches. A directive may carry several."""
    hits: list[str] = []
    for topic, patterns, excludes in _COMPILED:
        if any(pattern.search(normalized_text) for pattern in patterns):
            if any(pattern.search(normalized_text) for pattern in excludes):
                continue
            hits.append(topic.id)
    return hits


def match_strength(topic_id: str, normalized_text: str) -> int:
    """How many of a topic's patterns the text hits.

    Used when a directive matches several topics and only one of them may
    quote it: the topic it states most explicitly wins.
    """
    for topic, patterns, _ in _COMPILED:
        if topic.id == topic_id:
            return sum(1 for pattern in patterns if pattern.search(normalized_text))
    return 0


def classify_all(directives) -> None:
    """Annotate directives in place. Also considers the heading path, because a
    bullet under 'Commit Messages' inherits that context."""
    for directive in directives:
        context = directive.normalized
        if directive.heading_path:
            context = f"{' '.join(directive.heading_path).lower()} :: {context}"
        own = classify(directive.normalized)
        inherited = [t for t in classify(context) if t not in own]
        # An inherited topic only counts when the directive itself is a rule,
        # otherwise a heading would tag its whole section indiscriminately.
        directive.topics = own + (inherited if own or directive.hardness != "neutral" else [])
