# Open GitHub pull requests — 2026-10-21

## Verdict

All six open PRs authored by `marcelpetrick` have no replies from other accounts. Five target repositories owned by other accounts. One targets the user's repository.

## Plan and times

1. Find all open PRs by the authenticated user (completed; approximately 2 seconds).
2. Check discussion comments, reviews, and inline comments (completed; approximately 3 seconds).
3. Record and review the results (completed; less than 1 minute).

## Chronological status

| Step | Status | Time |
|---|---|---|
| Authenticate and search | Done | 2026-10-21 |
| Check replies and merge status | Done | 2026-10-21 |
| Review and record | Done | 2026-10-21 |

## Results

| PR | Title | Opened | State | Replies from others | Merge status |
|---|---|---|---|---|---|
| [terryyin/lizard#515](https://github.com/terryyin/lizard/pull/515) | fix(docs): correct typos found during code review | 2026-10-07 | Open | None | Conflicts |
| [zartis-digital/x-clone-starter#2](https://github.com/zartis-digital/x-clone-starter/pull/2) | workshop: results of the session | 2026-09-16 | Open | None | Mergeable |
| [ventoy/Ventoy#3721](https://github.com/ventoy/Ventoy/pull/3721) | fix(docs): correct typos found during code review | 2026-08-04 | Open | None | Mergeable |
| [CJCombrink/SpellChecker-Plugin#197](https://github.com/CJCombrink/SpellChecker-Plugin/pull/197) | feat(qml): add first-class spell checking for QML files | 2026-07-08 | Open | None | Mergeable |
| [CJCombrink/SpellChecker-Plugin#195](https://github.com/CJCombrink/SpellChecker-Plugin/pull/195) | Fix dark style contrast issues | 2026-07-08 | Open | None | Mergeable |
| [marcelpetrick/x-clone-starter#1](https://github.com/marcelpetrick/x-clone-starter/pull/1) | Workshop: Part 1 setup and Part 2 requirements skills (sections 2-8) | 2026-09-16 | Open | None | Mergeable |

## Method and review

Queried GitHub through the authenticated `gh` CLI. Search returned six open PRs with a limit of 1000. Checked discussion comments, reviews, and all pages of inline comments. Excluded comments and reviews authored by `marcelpetrick`. No other authors appeared. This check does not cover reactions, private messages, or deleted comments. Mergeable does not mean approved or passing CI. No remote changes were made.

## Resume here

State: complete. Repeat these commands to refresh the results:

```sh
gh search prs --author @me --state open --limit 1000 --json number,title,url,state,repository,createdAt
gh pr view https://github.com/terryyin/lizard/pull/515 --json state,reviewDecision,comments,reviews,mergeable,isDraft
gh api repos/terryyin/lizard/pulls/515/comments --paginate --slurp
```

Repeat the final two commands for each PR. Check both discussion comments and inline comments before concluding there were no replies.
