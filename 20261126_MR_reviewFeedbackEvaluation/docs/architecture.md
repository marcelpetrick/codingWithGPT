# Architecture (C4)

Every diagram below is editable Mermaid. GitHub renders it. Check the rendering after each change.

## Level 1: system context

Purpose: show who uses mrreview and which external systems it touches. Scope: the whole system.

```mermaid
flowchart LR
  analyst["Analyst<br/>(engineering lead, approved recipient)"]
  subgraph boundary["mrreview (runs on an approved local machine)"]
    sys["mrreview<br/>CLI + SQLite + HTML report"]
  end
  gitlab[("GitLab<br/>REST API v4")]
  ollama[("Ollama server<br/>REST API, existing")]
  browser["Web browser<br/>(opens the HTML file offline)"]
  analyst -- "runs commands, configures token via environment" --> sys
  sys -- "reads projects, MRs, discussions, versions, diffs, compare (GET only)" --> gitlab
  sys -- "sends minimised thread text, receives JSON classification" --> ollama
  sys -- "writes one self-contained dashboard file" --> browser
  analyst -- "reads dashboard, follows links" --> browser
  browser -- "source links open threads (needs GitLab access)" --> gitlab
```

## Level 2: containers

Purpose: show the parts of mrreview and the data each part owns. Scope: inside the system boundary.

```mermaid
flowchart TB
  cli["CLI (mrreview.cli)<br/>stages: collect · normalize · evidence · analyze · evaluate · report"]
  db[("SQLite database<br/>raw data, threads, classifications, findings, work state")]
  html["dashboard.html<br/>inline CSS + JS + JSON, CSP blocks network"]
  gitlab[("GitLab REST API")]
  ollama[("Ollama REST API")]
  cli -- "GET with retry, backoff, Retry-After" --> gitlab
  cli -- "POST /api/chat with JSON schema" --> ollama
  cli -- "transactional writes, one MR or one thread per transaction" --> db
  cli -- "reads aggregates, writes atomically" --> html
```

## Level 3: components of the pipeline

Purpose: answer "which module owns which decision". Scope: the Python package `src/mrreview`.

```mermaid
flowchart LR
  http["http.py<br/>transport, retry"] --> gl["gitlab.py<br/>GET-only client"]
  gl --> collect["collect.py<br/>discover, select, collect, gaps"]
  collect --> norm["normalize.py<br/>threads, roles, substantive check"]
  norm --> analyze["analyze.py<br/>context, cache by hash, concurrency, time budget"]
  gl --> evid["evidence.py<br/>compare API per diff comment"]
  evid --> evaluate
  llm["llm.py<br/>codebook prompt, schema, validator"] --> analyze
  analyze --> evaluate["evaluate.py<br/>code evidence, outcome, censoring, timings"]
  diffs["diffs.py"] --> evaluate
  biz["bizhours.py"] --> evaluate
  evaluate --> dataset["dataset.py<br/>export, name tokens, coverage"]
  ident["identity.py<br/>bots, pseudonyms, masking"] --> dataset
  dataset --> report["report.py<br/>safe JSON embedding"]
  assets["assets/dashboard.*<br/>charts, filters, tooltips, clues, reaction profile"] --> report
  evaluate --> placebo["scripts/placebo_check.py<br/>chance check of direct evidence"]
  dataset --> final["scripts/final_report.py<br/>aggregate-only HTML report"]
```

## Decisions that shape the design

| Topic | Decision | Requirement |
|---|---|---|
| Unit of analysis | The review thread. The LLM splits it into findings. | REQ-UNIT-1 |
| Determinism | Counting, timing, roles and code evidence are plain Python. The LLM only classifies text. | REQ-LLM-1 |
| Evidence | The GitLab compare API from the comment's head_sha to the final version decides direct or indirect; stored version diffs are the fallback (GitLab drops old version diffs). | REQ-OUT-1 |
| Portability | Numbered migrations with pinned checksums, a backup before each migration, and a JSON-lines export that imports into the current layout. | REQ-DB-1 |
| Resumption | A work table per MR and per thread; content hashes decide what is stale. | REQ-DB-2 |
| Privacy | Names never reach the LLM (role labels). The HTML holds name tokens; the toggle swaps them. People, bots and projects get pseudonyms. | REQ-UI-5, REQ-UI-6 |
| Safety | Model output is validated data. Nothing in it is executed. The client has no write method. | REQ-LLM-2, REQ-SEC-1 |
