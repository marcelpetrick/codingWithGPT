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
(eval):1: command not found: f.name
(eval):1: command not found: v
(eval):1: command not found:  + env[f.name] + 
   Building mrreview @ file:///home/mpetrick/repos/codingWithGPT/20261126_MR_reviewFeedbackEvaluation
      Built mrreview @ file:///home/mpetrick/repos/codingWithGPT/20261126_MR_reviewFeedbackEvaluation
Uninstalled 1 package in 0.18ms
Installed 1 package in 1ms
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |

## Example `config.local.toml` (git-ignored)

```toml
gitlab_url = "https://gitlab.example.com"
db_path = "out/real/mrreview.sqlite3"
window_months = 12
focus_username = "your-username"
ollama_url = "http://localhost:11434"
ollama_model = "qwen3.6:35b-a3b-q4_K_M-agentic"
timezone = "Europe/Berlin"
holidays = ["2026-12-24", "2026-12-25", "2026-12-26"]

[ollama_options]
temperature = 0
num_ctx = 16384
```

Run with `MRREVIEW_GITLAB_TOKEN=<read_api token> uv run mrreview --config config.local.toml run`.
