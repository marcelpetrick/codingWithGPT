## Run notes

Source: Norbert Nagel / Wikimedia Commons, CC BY-SA 3.0, https://commons.wikimedia.org/wiki/File:Cathedral_Limburg_-_Limburger_Dom_-_October_26th_2013_-_06.jpg. The generated frames are adaptations and use the same license. See ../examples/README.md.

Claude Code runs the chain with `recreate-101/scripts/codex-chain.sh`. Each generation uses a fresh `codex exec` session with the unchanged prompt from `SKILL.md`. A refused frame is sent again after 60 s, at most three times in a row. The direct API path is not used.

The Codex host tool does not expose image tokens, charges or the subscription allowance. These values are unavailable, not zero. "Codex agent tokens" are the tokens of the `codex exec` session that called the tool.
