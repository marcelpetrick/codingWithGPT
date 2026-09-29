# Allowing nvidia-smi and other tools

Claude Code runs Bash commands in a sandbox. Some tools need access the sandbox does not give them.

## nvidia-smi

**Symptom:** inside Claude Code, `nvidia-smi` prints

```
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.
```

although the driver works fine in a normal terminal.

**Cause:** the sandbox has its own minimal `/dev` without the `/dev/nvidia*` device nodes, so `nvidia-smi` cannot reach the driver.

**Fix:** let `nvidia-smi` run outside the sandbox. Add it to your user settings, `~/.claude/settings.json`
(or `$CLAUDE_CONFIG_DIR/settings.json` if you set that variable):

```json
{
  "sandbox": {
    "excludedCommands": ["nvidia-smi"]
  }
}
```

Alternatively run `/sandbox` in Claude Code and edit the settings there.
Commands in `excludedCommands` run with full access to your machine, so list only specific tools.

## Local Ollama (localhost:11434)

**Symptom:** `curl http://localhost:11434` fails with "Could not connect to server", although Ollama is running.

**Cause:** the sandbox has its own network. Its `localhost` is not your machine's, and `NO_PROXY`
makes curl skip the sandbox proxy, which is the only way out.

**Fix:** allow the address, then send the request through the proxy:

```json
{
  "sandbox": {
    "network": {
      "allowedDomains": ["127.0.0.1:11434", "localhost:11434"]
    }
  }
}
```

```sh
curl --noproxy '' -x "$HTTP_PROXY" http://127.0.0.1:11434/api/version
```

To use the `ollama` CLI itself, add `"ollama"` to `excludedCommands` instead.

## Other LAN hosts

Same as Ollama: add `host:port` to `sandbox.network.allowedDomains` and route the request through `$HTTP_PROXY`.

## If the managed settings prevent it

Managed settings take precedence over your own settings. If a fix above has no effect, or the setting is
locked (for example by `allowManagedDomainsOnly`), open a
[managed settings change request](Managed-Settings-Change-Requests).
