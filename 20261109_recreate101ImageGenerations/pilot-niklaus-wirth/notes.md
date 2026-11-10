## Run notes

Source: Tyomitch, https://commons.wikimedia.org/wiki/File:Niklaus_Wirth,_UrGU.jpg. See ../examples/README.md for the source terms.

The first call used the original JPEG. Every later call used the preceding generated PNG. The ledger for calls 1–10 was reconstructed after those calls. Their per-call times are unavailable.

Generations 1–12 ran in one Codex session on 2026-11-09. Generation 13 was refused (`moderation_blocked`, output stage, request ID `744cf41e-1625-417c-abcf-87edc5f6b27b`). From 2026-11-10, Claude Code runs the chain with `recreate-101/scripts/codex-chain.sh`. Each generation uses a fresh `codex exec` session with the unchanged prompt. A refused frame is sent again, at most three times in a row.

The Codex host tool does not expose image tokens, charges or the subscription allowance. These values are unavailable, not zero. "Codex agent tokens" are the tokens of the `codex exec` session that called the tool. No direct API calls were made. The GIF is a color-quantized viewing copy. The PNGs are the source frames.
