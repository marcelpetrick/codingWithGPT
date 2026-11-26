# Changelog

Semantic Versioning. Newest first.

- 0.1.16: fix(analyze): build context in main thread, book truncation as invalid
- 0.1.15: feat(evaluate): verify outcomes against code and time them
- 0.1.14: feat(analyze): classify substantive threads via Ollama
- 0.1.13: feat(demo): add fake Ollama with a rule-based stub classifier
- 0.1.12: feat(llm): add codebook prompt, output schema and validator
- 0.1.11: feat(diffs): parse new-side lines of unified diffs
- 0.1.10: fix(demo): apply fixture code changes in time order
- 0.1.9: feat(normalize): build review threads with roles
- 0.1.8: feat(collect): discover projects and collect full MR history
- 0.1.7: feat(demo): add synthetic GitLab fixture and fake REST server
- 0.1.6: feat(gitlab): add GET-only client with retry and backoff
- 0.1.5: feat(config): load TOML and environment settings
- 0.1.4: feat(identity): classify bots and assign stable pseudonyms
- 0.1.3: feat(db): add SQLite schema, migrations and work states
- 0.1.2: feat(time): add business-hours calendar with DST handling
- 0.1.1: feat(text): add grapheme-safe text helpers and routine check