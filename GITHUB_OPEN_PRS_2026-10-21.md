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


## Reminder task — 2026-10-21

### Plan and status

1. Identify past merge authors and approvers (done; approximately 1 minute).
2. Check current PR discussions and prepare four comments (done; approximately 2 minutes).
3. Review each comment before posting (done; approximately 1 minute).
4. Post each comment once and verify its text and URL (done; less than 1 minute).

Both x-clone-starter repositories are excluded. The user explicitly authorized four public reminders with maintainer mentions.

### Maintainer evidence

Examined 12 merged PRs per repository, ordered by latest update. Each repository had one merge author across that sample.

| Repository | Mention | Evidence |
|---|---|---|
| terryyin/lizard | @terryyin | Merged all 12 sampled PRs; approved [#501](https://github.com/terryyin/lizard/pull/501) and [#500](https://github.com/terryyin/lizard/pull/500) |
| ventoy/Ventoy | @ventoy | Merged all 12 sampled PRs, including documentation change [#3725](https://github.com/ventoy/Ventoy/pull/3725) |
| CJCombrink/SpellChecker-Plugin | @CJCombrink | Merged all 12 sampled PRs, including [#194](https://github.com/CJCombrink/SpellChecker-Plugin/pull/194); approved [#186](https://github.com/CJCombrink/SpellChecker-Plugin/pull/186) |

### Review before posting

- Rechecked all four PRs: each is open and has no reviews or replies from other accounts.
- Previous follow-ups exist on Ventoy and both SpellChecker PRs. Their latest dates are August 24, 2026.
- Lizard has an existing maintainer mention and one thumbs-up reaction. A reaction is not a written reply.
- Lizard has a merge conflict. Its reminder acknowledges the conflict.
- Ventoy changes many files and bundled components. Its reminder offers a smaller scope.
- QML test details come from the existing PR description. They describe the original local check, not a new test run.
- Other local-check statements reflect the user's account of checks before submission. No new tests were run for these reminders.
- No comment claims that CI passed, that approval is owed, or that the change needs no review.
- Each comment mentions only the maintainer supported by past merge activity.
- Each comment offers help without a deadline or repeated-ping promise.

### Exact reviewed comments

#### terryyin/lizard#515

Hi @terryyin, a friendly follow-up on this typo cleanup. Thank you for maintaining Lizard; I have found it very useful.

I checked the changes locally before opening the PR. My aim is to improve the project while keeping the review effort small. GitHub currently reports a merge conflict. I am happy to update the branch if the changes are useful to you.

Whenever you have time, could you let me know whether this fits the project? If you prefer a smaller scope, I am happy to adjust it. Thanks!

#### ventoy/Ventoy#3721

Hi @ventoy, a friendly follow-up on this typo cleanup. Thank you for maintaining Ventoy; it has been very useful to me.

I checked the changes locally before opening the PR. My aim is to improve the project while keeping the review effort small. I realize the changes cover many files, including bundled components. I am happy to narrow the scope if that makes review easier.

Whenever you have time, could you let me know whether these changes would be useful? I understand that maintenance time is limited. Thanks!

#### CJCombrink/SpellChecker-Plugin#197

Hi @CJCombrink, a friendly follow-up on the QML spell-checking support for #196. Thank you for your work on this plugin.

I tested this locally with Qt Creator 19.0.2 before opening the PR. The QML parser tests passed with ctest, as noted in the description. This adds a substantial feature, so I understand that review takes time. My aim is to improve the plugin while keeping the maintenance effort manageable.

Whenever you have time, could you let me know whether this approach fits the project? I am happy to revise or split the changes to make review easier. Thanks!

#### CJCombrink/SpellChecker-Plugin#195

Hi @CJCombrink, a friendly follow-up on the dark-style contrast fix for #77. Thank you for maintaining this plugin.

I checked the changes locally before opening the PR. The screenshot linked above shows the result. My aim is to improve readability while keeping the review effort small.

Whenever you have time, could you let me know whether this fix fits the project? I am happy to adjust it if you prefer another approach. Thanks!

- terryyin/lizard#515: https://github.com/terryyin/lizard/pull/515#issuecomment-6314512927 (posted and verified 2026-10-21T11:12:11Z).

- ventoy/Ventoy#3721: https://github.com/ventoy/Ventoy/pull/3721#issuecomment-6314513792 (posted and verified 2026-10-21T11:12:14Z).

- CJCombrink/SpellChecker-Plugin#197: https://github.com/CJCombrink/SpellChecker-Plugin/pull/197#issuecomment-6314514507 (posted and verified 2026-10-21T11:12:17Z).

- CJCombrink/SpellChecker-Plugin#195: https://github.com/CJCombrink/SpellChecker-Plugin/pull/195#issuecomment-6314515176 (posted and verified 2026-10-21T11:12:19Z).

### Final verification

All four comments were posted as `marcelpetrick`. Read back each comment through its GitHub API endpoint. Each published body matches the reviewed draft exactly. Neither x-clone-starter PR received a comment. No PR code, branch, review, or merge state was changed.

Resume here: reminders complete. Use the four comment URLs above to inspect replies. Do not repeat the reminders automatically.
