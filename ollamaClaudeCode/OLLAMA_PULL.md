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

# 3. Pull models (progress appears locally, download lands on server)
ollama pull mistral-nemo:12b
ollama pull codestral:22b

# 4. Create larger-context variants for Claude Code
#    (all Ollama models default to 4096 tokens — too small for Claude Code's system prompt)
cat <<'EOF' | ollama create mistral-nemo:12b-ctx32k -f -
FROM mistral-nemo:12b
PARAMETER num_ctx 32768
EOF

# mistral-nemo supports 128k natively — push higher if needed:
cat <<'EOF' | ollama create mistral-nemo:12b-ctx128k -f -
FROM mistral-nemo:12b
PARAMETER num_ctx 131072
EOF

cat <<'EOF' | ollama create codestral:22b-ctx32k -f -
FROM codestral:22b
PARAMETER num_ctx 32768
EOF

# 5. Verify
ollama list

# 6. Return to local
unset OLLAMA_HOST
```

## Expected VRAM and speed (12 GB NVIDIA GPU)

| Model | Disk | VRAM | Speed est. | Fits? | Notes |
|---|---|---|---|---|---|
| `mistral-nemo:12b` | ~7.5 GB | ~7.5 GB | 40–50 tok/s | ✓ easily | 128k native ctx |
| `codestral:22b` | ~13 GB | ~12–13 GB | 15–20 tok/s | borderline | Coding-specific; likely small CPU spillover |

## Tool-use compatibility

Before using a new model with `claude-ol`, verify it returns proper `tool_use`
blocks via the Anthropic-compatible API:

```shell
curl -s --max-time 30 \
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
    print('  type:', b.get('type'), b.get('name',''), b.get('input',''))
"
```

Expected output for a working model:
```
stop_reason: tool_use
  type: tool_use write_file {'path': '/tmp/test.txt', 'content': 'hello world'}
```

If `stop_reason` is `end_turn` and the block type is `text`, the model does not
support Anthropic's tool-use protocol and will not work with Claude Code.

## Known compatibility

| Model | Tool use | Confirmed |
|---|---|---|
| `qwen3.5:9b-ctx64k` | ✓ | yes |
| `qwen3.5:4b-ctx32k` | ✓ | yes |
| `qwen2.5-coder:7b-ctx32k` | ✗ | yes — broken |
| `mistral-nemo:12b` | likely ✓ | pending test |
| `codestral:22b` | uncertain | pending test |
