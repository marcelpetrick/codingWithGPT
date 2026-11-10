# Host-tool run

Status: ready.

Completed generations: 39 / 100. Refusals recorded: 0. Codex agent tokens: 2144728 in (1725696 cached), 6482 out, 39 calls.

Provider: Codex host image tool. Model, image settings, tokens, request charges, and account balance: unavailable unless the host exposes them. API cost: not applicable; no direct API calls were made. Agent session overhead: the Codex agent tokens above, where recorded.

Original SHA-256: b1a6dc513137d92ead11e5c293ff094728d6e599dbb9edf63111ea039281c898. See manifest.json and usage.jsonl for frame lineage.

## Run notes

Source: Norbert Nagel / Wikimedia Commons, CC BY-SA 3.0, https://commons.wikimedia.org/wiki/File:Cathedral_Limburg_-_Limburger_Dom_-_October_26th_2013_-_06.jpg. The generated frames are adaptations and use the same license. See ../examples/README.md.

Claude Code runs the chain with `recreate-101/scripts/codex-chain.sh`. Each generation uses a fresh `codex exec` session with the unchanged prompt from `SKILL.md`. A refused frame is sent again after 60 s, at most three times in a row. The direct API path is not used.

The Codex host tool does not expose image tokens, charges or the subscription allowance. These values are unavailable, not zero. "Codex agent tokens" are the tokens of the `codex exec` session that called the tool.
