# Local Ollama and claude-dmo GPU access

How two workstation problems were diagnosed and fixed on 2026-09-29, with the commands to repeat
the fixes. Host: `precision5570` (Manjaro, RTX A2000 8 GB Laptop GPU, Ollama 0.34.4).

## 1. Local Ollama crash-looped after the USB-ethernet adapter was unplugged

### Symptom

```
$ ollama list
Error: could not connect to ollama server, run 'ollama serve' to start it
$ systemctl is-active ollama
activating
```

### Diagnosis

```
systemctl status ollama --no-pager            # "activating (auto-restart) (Result: exit-code)"
journalctl -u ollama -n 20 --no-pager         # the actual error
cat /etc/systemd/system/ollama.service.d/override.conf
ip -br addr                                   # which addresses exist right now
journalctl -k --since -6h | grep -i 'usb.*disconnect'
```

The journal showed, every 3 s:

```
Error: listen tcp 192.168.100.54:11434: bind: cannot assign requested address
```

### Cause

The systemd override set `OLLAMA_HOST=192.168.100.54:11434`. That address belongs to the
USB-ethernet adapter, which disconnected at 08:28 (`usb 3-9: USB disconnect`). Without the address
the server cannot bind, exits with status 1, and systemd restarts it forever.

A second, older catch: the shell has no `OLLAMA_HOST`, so the `ollama` client always asks
`127.0.0.1:11434`. Even while the service ran on `.54`, a plain `ollama list` could not reach it.

### Fix

Bind the service to localhost (needs sudo):

```
sudo sed -i 's/192.168.100.54:11434/127.0.0.1:11434/' /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Resulting override:

```
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
```

Why localhost and not `0.0.0.0`: `0.0.0.0` would also expose Ollama's unauthenticated API on the
Wi-Fi network. Localhost starts regardless of the adapter and matches the client's default. If
machines on `192.168.100.x` must reach this Ollama again, bind to `0.0.0.0:11434` and accept that
exposure, or put back `192.168.100.54:11434` while the adapter is plugged in.

### Verification

```
systemctl is-active ollama                    # active
ollama list                                   # lists the local models
curl -s http://127.0.0.1:11434/api/version    # {"version":"0.34.4"}
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen3.5:4b","prompt":"Say OK.","stream":false,"think":false}'
curl -s http://127.0.0.1:11434/api/ps         # size_vram == size means fully on the GPU
```

The first generate call after a restart includes the model load and can take longer than a short
client timeout; the second answered in 0.15 s.

## 2. claude-dmo could not run nvidia-smi

`claude-dmo` is the zsh function in `~/.zshrc` that starts Claude Code with the company account,
using `CLAUDE_CONFIG_DIR=~/.claude-dmo`. Its settings file is therefore `~/.claude-dmo/settings.json`,
not `~/.claude/settings.json`.

### Cause

The Claude Code sandbox gives commands only a minimal `/dev`, so `/dev/nvidia0`, `/dev/nvidiactl`
and `/dev/nvidia-uvm` are invisible and `nvidia-smi` fails. The driver itself is fine: outside the
sandbox `nvidia-smi` works.

### Fix

Two keys in `~/.claude-dmo/settings.json`, merged into the existing file (backup first):

```
f=~/.claude-dmo/settings.json
cp "$f" "$f.bak-20260929"
jq '.sandbox.excludedCommands = ((.sandbox.excludedCommands // []) + ["nvidia-smi *"] | unique)
  | .permissions.allow   = ((.permissions.allow   // []) + ["Bash(nvidia-smi *)"] | unique)' \
  "$f" > "$f.new" && mv "$f.new" "$f"
```

- `sandbox.excludedCommands: ["nvidia-smi *"]` runs `nvidia-smi` (with or without arguments)
  outside the sandbox, so it sees the GPU device files.
- `permissions.allow: ["Bash(nvidia-smi *)"]` skips the permission prompt; excluded commands are
  otherwise still prompted. `nvidia-smi` only reads GPU state.

No managed settings exist (`/etc/claude-code/` is absent) that could override these user settings.

### Limits

- Takes effect in new claude-dmo sessions; restart a running one.
- The patterns match whole commands. `nvidia-smi | head` or `cd x && nvidia-smi` may still run
  inside the sandbox and fail.

### Verification

A headless claude-dmo session, same environment as the `claude-dmo` function:

```
echo "Run exactly: nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv" | \
  CLAUDE_CONFIG_DIR="$HOME/.claude-dmo" env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
    -u ANTHROPIC_BASE_URL -u CLAUDE_CODE_OAUTH_TOKEN -u CLAUDE_CODE_USE_BEDROCK \
    -u CLAUDE_CODE_USE_VERTEX -u CLAUDE_CODE_USE_FOUNDRY \
  claude -p --model haiku --allowedTools "Bash(nvidia-smi *)"
```

The prompt goes in on stdin because `--allowedTools` takes several values and would swallow a
trailing prompt argument. Result on 2026-09-29:

```
name, memory.used [MiB], memory.total [MiB]
NVIDIA RTX A2000 8GB Laptop GPU, 3900 MiB, 8192 MiB
```

## Quick checks

```
systemctl is-active ollama && ollama list
cat /etc/systemd/system/ollama.service.d/override.conf
jq '{permissions, sandbox}' ~/.claude-dmo/settings.json
```
