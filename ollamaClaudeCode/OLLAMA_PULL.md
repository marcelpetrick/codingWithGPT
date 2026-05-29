# Pulling models onto a remote Ollama server

The `ollama` CLI respects `OLLAMA_HOST`. When set, every command (pull, list,
create, ps) targets the remote server instead of localhost. The download happens
on the server; the data never touches your machine.

## One-time pull procedure

```shell
# 1. Point the CLI at the server
export OLLAMA_HOST=http://192.168.100.37:11434

# 2. Verify — should show the server's model list, not local
ollama list

# 3. Pull models
ollama pull mistral-nemo:12b
ollama pull codestral:22b

# 4. Create larger-context variants for Claude Code
cat > /tmp/Modelfile-nemo-ctx32k <<'EOF'
FROM mistral-nemo:12b
PARAMETER num_ctx 32768
EOF
ollama create mistral-nemo:12b-ctx32k -f /tmp/Modelfile-nemo-ctx32k

cat > /tmp/Modelfile-codestral-ctx32k <<'EOF'
FROM codestral:22b
PARAMETER num_ctx 32768
EOF
ollama create codestral:22b-ctx32k -f /tmp/Modelfile-codestral-ctx32k

# mistral-nemo supports 128k natively — optionally push higher:
cat > /tmp/Modelfile-nemo-ctx128k <<'EOF'
FROM mistral-nemo:12b
PARAMETER num_ctx 131072
EOF
ollama create mistral-nemo:12b-ctx128k -f /tmp/Modelfile-nemo-ctx128k

# 5. Verify
ollama list

# 6. Return to local
unset OLLAMA_HOST
```

Note: `ollama create` does NOT support stdin (`-f -`) when targeting a remote
server via `OLLAMA_HOST`. Write the Modelfile to disk first.

## Status (2026-05-29)

| Model | Pulled | ctx32k created | Inference tested | Tool use tested |
|---|---|---|---|---|
| `mistral-nemo:12b` | ✓ | ✓ | pending | pending |
| `codestral:22b` | ✓ | ✓ | pending | pending |

Both models pulled successfully. Inference testing blocked by a server-side
keepalive issue — see "Model-swap lockout" below.

## Model-swap lockout — known server issue

After the benchmark run on 2026-05-29, `qwen3.5:9b-ctx64k` was left loaded in
VRAM (11.48 GB). Subsequent requests for the new models timed out even with
240-second timeouts because Ollama did not unload qwen3.5 to make room.

`keep_alive: 0` requests to force-unload qwen3.5 also timed out, indicating the
inference queue itself was blocked. This is a server-side Ollama state issue, not
a problem with the pulled models.

**To recover:** restart the Ollama service on the server.

```shell
# On the server machine:
sudo systemctl restart ollama
# or if installed manually:
pkill ollama && ollama serve &
```

After restart, test in isolation (one model at a time, no benchmark chain):

```shell
export OLLAMA_HOST=http://192.168.100.37:11434

# Test mistral-nemo first
curl -s --max-time 120 \
  -X POST http://192.168.100.37:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-nemo:12b", "prompt": "hi", "stream": false, "options": {"num_predict": 5}}' | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(f'tps={round(d[\"eval_count\"]*1e9/d[\"eval_duration\"],1)}  load={round(d[\"load_duration\"]/1e9,1)}s')"

# Check VRAM
curl -s http://192.168.100.37:11434/api/ps | python3 -c \
  "import json,sys; [print(m['name'], round(m['size_vram']/1e9,2), 'GB VRAM') for m in json.load(sys.stdin)['models']]"
```

## Expected VRAM and speed (12 GB NVIDIA GPU)

| Model | Weights | KV cache est (ctx32k) | Total est | Speed est | Fits? |
|---|---|---|---|---|---|
| `mistral-nemo:12b-ctx32k` | 7.1 GB | ~2.5 GB | ~9.6 GB | 35–45 tok/s | ✓ |
| `codestral:22b-ctx32k` | 12.0 GB | ~3.5 GB | ~15.5 GB | — | ✗ overflow |
| `codestral:22b` (ctx4096) | 12.0 GB | ~0.3 GB | ~12.3 GB | ~15 tok/s | borderline |

`codestral:22b` at default 4096-token context might barely fit (~12.3 GB). With
ctx32k it would not. If it fits at 4096, it still cannot be used with Claude Code
as-is (context too small) — a Modelfile with `num_ctx 16384` might give a workable
middle ground.

## Tool-use compatibility test

After confirming inference works, test for proper `tool_use` API blocks:

```shell
curl -s --max-time 60 \
  -X POST http://192.168.100.37:11434/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: ollama" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "mistral-nemo:12b-ctx32k",
    "max_tokens": 200,
    "tools": [{
      "name": "write_file",
      "description": "Write content to a file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"},
          "content": {"type": "string"}
        },
        "required": ["path", "content"]
      }
    }],
    "messages": [{"role": "user", "content": "Write hello world to /tmp/test.txt"}]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('stop_reason:', d.get('stop_reason'))
for b in d.get('content', []):
    t = b.get('type')
    if t == 'tool_use':
        print('  TOOL_USE:', b.get('name'), b.get('input'))
    elif t == 'text':
        print('  TEXT:', repr(b.get('text','')[:150]))
"
```

Expected for a working model: `stop_reason: tool_use` + `TOOL_USE` block.
If `stop_reason: end_turn` + `TEXT` with raw JSON: model does not support
Anthropic's tool-use protocol (same failure mode as `qwen2.5-coder`).

## Known tool-use compatibility

| Model | Tool use | Confirmed |
|---|---|---|
| `qwen3.5:9b-ctx64k` | ✓ | yes |
| `qwen3.5:4b-ctx32k` | ✓ | yes |
| `qwen2.5-coder:7b-ctx32k` | ✗ | yes — broken |
| `mistral-nemo:12b` | likely ✓ | pending |
| `codestral:22b` | uncertain | pending |
