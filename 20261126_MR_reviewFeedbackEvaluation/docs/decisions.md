# Decisions and owner inputs

Git holds the timestamp of each entry. Each entry links to its requirement.

| ID | Date | Input or decision | Reason | Requirement |
|---|---|---|---|---|
| D-001 | 2026-11-26 | Owner: "get the work done", build the whole system from `VISION.md`. | Task start. | all |
| D-002 | 2026-11-26 | Owner: use the Ollama box from `ollamaClaudeCode_v4_tielCoder/` (`192.168.100.67:11434`, Ollama 0.40.11). Default model `qwen3.6:35b-a3b-q4_K_M-agentic`, configurable. | It is the fast general model of the standing field (131 tok/s) and supports structured output. | REQ-LLM-1 |
| D-003 | 2026-11-26 | Owner: the dashboard must be pretty and have tooltips for all elements. | Owner input. | REQ-UI-3 |
| D-004 | 2026-11-26 | Owner: the dashboard must "give clues". Add an insight panel with sample-size guards. | Owner input. | REQ-UI-3 |
| D-005 | 2026-11-26 | Owner: build an MVP first, then iterate. | Owner input. | all |
| D-006 | 2026-11-26 | Live GitLab analysis stays blocked. No token and no organisational authorization exist (VISION section 8). The MVP runs on a synthetic GitLab fixture. | A token is not authorization for employee analytics. | REQ-OPS-1 |
| D-007 | 2026-11-26 | Ollama live tests use synthetic review threads only. | No real review text leaves GitLab without authorization. | REQ-LLM-1 |
| D-008 | 2026-11-26 | Runtime uses only the standard library plus `regex` (grapheme clusters) and `tzdata`. HTTP uses `urllib`. Charts are hand-written SVG. | Few dependencies, no CDN, simple offline HTML. | REQ-UI-1, REQ-ENG-1 |
| D-009 | 2026-11-26 | Ruff lints, Black formats. Ruff format is not used. | AGENTS.md: one formatter per language. | REQ-ENG-1 |
| D-010 | 2026-11-26 | Owner: write a README and push to GitHub. The push goes to `origin master` of the monorepo. | Owner approval to publish. The synthetic demo holds no real data. | REQ-ENG-1 |
| D-012 | 2026-11-26 | Owner: run on the real active projects, especially those that involve the owner as reviewer and as recipient. Added `--focus-user` and `--focus-only`. The owner gave the go for the live run; the owner carries the organisational authorization of VISION.md section 8. Data stays on the laptop and the LAN Ollama box. | Owner input. | REQ-FOC-1, REQ-OPS-1 |
| D-011 | 2026-11-26 | No Markdown file contains a double curly brace or a curly-percent pair. | The monorepo Pages build runs Liquid on every .md file and fails on them. | REQ-ENG-1 |
