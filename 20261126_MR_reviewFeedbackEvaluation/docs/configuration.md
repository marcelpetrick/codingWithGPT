# Configuration

Settings come from three places. A later place wins:

1. the defaults in `src/mrreview/config.py`;
2. an optional TOML file (`mrreview --config my.toml …`);
3. environment variables (table below).

The GitLab token comes **only** from the environment. A token in the TOML file is refused.
Unknown keys in the file are refused, so a typo cannot pass silently.
Command-line flags (`--db`, `--focus-user`, `--focus-only`, `--max-minutes`, …) override all three for one run.

| Key | Default | Environment variable |
|---|---|---|
| `gitlab_url` | empty | `MRREVIEW_GITLAB_URL` |
| `gitlab_token` | empty (environment only) | `MRREVIEW_GITLAB_TOKEN` |
| `db_path` | `data/mrreview.sqlite3` | `MRREVIEW_DB` |
| `focus_username` | empty | `MRREVIEW_FOCUS_USER` |
| `focus_only` | `false` | — |
| `discover_membership_only` | `false` | — |
| `include_archived` | `false` | — |
| `window_months` | `12` | — |
| `min_window_mrs` | `1` | — |
| `per_page` | `100` | — |
| `http_timeout_s` | `30.0` | — |
| `max_retries` | `5` | — |
| `backoff_base_s` | `1.0` | — |
| `max_diff_bytes` | `200000` | — |
| `ollama_url` | `http://192.168.100.67:11434` | `MRREVIEW_OLLAMA_URL` |
| `ollama_model` | `qwen3.8-pi:27b-q4km-ctx200k-nothink` | `MRREVIEW_OLLAMA_MODEL` |
| `ollama_timeout_s` | `600.0` | — |
| `ollama_concurrency` | `1` | — |
| `ollama_keep_alive` | `15m` | — |
| `ollama_options` | `temperature = 0`, `num_ctx = 16384` | — |
| `max_note_graphemes` | `1500` | — |
| `max_thread_notes` | `30` | — |
| `timezone` | `Europe/Berlin` | — |
| `business_start_hour` / `business_end_hour` | `8` / `18` | — |
| `holidays` | none (owner decision D-022) | — |
| `censor_days` | `14` | — |

## Example `config.local.toml` (git-ignored)

```toml
gitlab_url = "https://gitlab.example.com"
db_path = "out/real/mrreview.sqlite3"
window_months = 12
focus_username = "your-username"
ollama_url = "http://localhost:11434"
ollama_model = "qwen3.8-pi:27b-q4km-ctx200k-nothink"
timezone = "Europe/Berlin"
holidays = ["2026-12-24", "2026-12-25", "2026-12-26"]

[ollama_options]
temperature = 0
num_ctx = 16384
```

Run with `MRREVIEW_GITLAB_TOKEN=<read_api token> uv run mrreview --config config.local.toml run`.
