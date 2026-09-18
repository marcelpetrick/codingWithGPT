"""Claude Code driven by a local Ollama model, as a Terminal-Bench agent.

Terminal-Bench ships a `claude-code` agent, but its `_env` passes only
ANTHROPIC_API_KEY and ANTHROPIC_MODEL -- there is no ANTHROPIC_BASE_URL. Run it
unmodified and every task talks to api.anthropic.com, which is not the thing we
are benchmarking. (It would not even fail loudly in a useful way: the harness
reports the resulting trials as `Accuracy: 0.00%`, indistinguishable from a model
that simply solved nothing. Harness §0.)

This subclass supplies the same environment contract the rest of v4 uses:

  * ANTHROPIC_BASE_URL -> the Ollama host, reached directly from the task
    container (verified: a default-bridge container resolves and reaches
    192.168.100.67:11434 through the host's USB-ethernet route).
  * all four model slots pinned to the same tag. Claude Code picks a "small fast
    model" for subagents and for its own background calls; if that slot names a
    tag the server does not have, those calls 404 and the failure surfaces as a
    mangled turn rather than an error (v3's finding).
  * CLAUDE_CODE_MAX_CONTEXT_TOKENS below the baked window, because Claude Code
    cannot send num_ctx and a model that silently truncates would otherwise do so
    unrecorded.
  * telemetry/autoupdater off, so a task container with internet cannot spend
    turns on a version check mid-benchmark.

Thinking: `<|think_off|>` is a Sharp-template token, so it only takes effect on
Tiel and CyberTiel. Asking for thinking=off in a mixed field silently disables
reasoning for those two and leaves it on for everyone else, which is how the
2026-09-18 round came to compare a handicapped subject against a thinking
control. `thinking=off` is therefore refused unless every model in the run
honours the marker; the default is `on`, which is the only setting this harness
can guarantee is symmetric.

Usage (note: --agent-import-path overrides --agent):

    tb run -d terminal-bench-core==0.1.1 \
      --agent-import-path terminalbench.official.ollama_claude_code_agent:OllamaClaudeCodeAgent \
      -m tiel-coder:35b-q5-ctx256k-agentic \
      -k thinking=off
"""

import os
import shlex
import tempfile
from pathlib import Path

import terminal_bench.agents.installed_agents.claude_code as _claude_code_pkg
from terminal_bench.agents.installed_agents.claude_code.claude_code_agent import (
    ClaudeCodeAgent,
)
from terminal_bench.terminal.models import TerminalCommand
from terminal_bench.utils.template_utils import render_setup_script

DEFAULT_HOST = os.environ.get("OLLAMA_HOST_URL", "http://192.168.100.67:11434")
# Under the smallest baked window in the field (262144), with headroom for the
# harness's own preamble. Same number as the shell aliases.
DEFAULT_MAX_CTX = "230000"
THINK_OFF_MARKER = "<|think_off|>"

# `<|think_off|>` is a SHARP-TEMPLATE convention. Appending it to a model whose
# template does not parse it leaves it as inert text in the system prompt and the
# model goes on reasoning normally.
#
# The 2026-09-18 round shipped it to every model and got exactly that: Tiel and
# CyberTiel emitted 0 reasoning blocks across 30 trials each, while qwen3.6 (287
# blocks), north-mini (373), ornith (95) and gemma4 (83) kept thinking. The two
# subject models were handicapped and every comparator was not — a difference the
# round then read as capability. Public Terminal-Bench numbers put Ornith-1.5
# (Tiel's base) ABOVE Qwen3.6-35B; this round found the reverse, which is the
# signature of a configuration error rather than a disagreement about models.
#
# So the marker is now allowed only when EVERY model in the run honours it, and
# the check is loud.
SHARP_TEMPLATE_MODELS = ("tiel-coder", "cyber-tiel")


def honours_think_off(model: str) -> bool:
    return any(k in model.split(":", 1)[0] for k in SHARP_TEMPLATE_MODELS)


class OllamaClaudeCodeAgent(ClaudeCodeAgent):
    """ClaudeCodeAgent pointed at a local Ollama server."""

    @staticmethod
    def name() -> str:
        return "ollama-claude-code"

    def __init__(self, *args, thinking: str = "on", host: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._thinking = str(thinking).lower()
        self._host = host or DEFAULT_HOST
        if not self._model_name:
            raise ValueError("pass the Ollama tag with -m, e.g. -m tiel-coder:35b-q5-ctx256k-agentic")

    @property
    def _env(self) -> dict[str, str]:
        tag = self._model_name.removeprefix("anthropic/").removeprefix("ollama/")
        return {
            "ANTHROPIC_BASE_URL": self._host,
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "ollama"),
            # All four slots on the same tag -- the box holds one model.
            "ANTHROPIC_MODEL": tag,
            "ANTHROPIC_SMALL_FAST_MODEL": tag,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": tag,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": tag,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": tag,
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": os.environ.get(
                "CLAUDE_CODE_MAX_CONTEXT_TOKENS", DEFAULT_MAX_CTX
            ),
            "DISABLE_TELEMETRY": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
            "DISABLE_AUTOUPDATER": "1",
            "FORCE_AUTO_BACKGROUND_TASKS": "1",
            "ENABLE_BACKGROUND_TASKS": "1",
        }

    @property
    def _install_agent_script_path(self) -> Path:
        """Render UPSTREAM's claude-code install template, not one of ours.

        The base class locates its template with `inspect.getfile(self.__class__)`,
        which for a subclass living in another directory resolves to *this*
        directory -- so it looked for `claude-code-setup.sh.j2` next to this file
        and raised "Template file not found". (The harness then reported that as
        `Accuracy: 0.00%`, which is the same silent shape as the missing
        docker-compose plugin. See OFFICIAL_TB_PLAN.md.)

        Pointing at the installed package keeps us on upstream's install script,
        so we do not drift from it as terminal-bench is upgraded.
        """
        template = Path(_claude_code_pkg.__file__).parent / "claude-code-setup.sh.j2"
        if not template.is_file():  # fail loudly rather than score it as 0%
            raise FileNotFoundError(f"upstream claude-code template missing: {template}")
        rendered = render_setup_script(template, self._get_template_variables())
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False)
        tf.write(rendered)
        tf.close()
        os.chmod(tf.name, 0o755)
        return Path(tf.name)

    def _run_agent_commands(self, instruction: str) -> list[TerminalCommand]:
        cmd = (
            "claude --verbose --output-format stream-json "
            f"-p {shlex.quote(instruction)} "
            f"--allowedTools {' '.join(self.ALLOWED_TOOLS)}"
        )
        if self._thinking == "off":
            if not honours_think_off(self._model_name):
                raise ValueError(
                    f"thinking=off was requested for {self._model_name!r}, which does "
                    f"not honour {THINK_OFF_MARKER} -- the marker would sit in its "
                    "system prompt as inert text while the model kept reasoning, and "
                    "any Sharp-template model in the same field WOULD be silenced. "
                    "That asymmetry invalidated the 2026-09-18 round. Run the whole "
                    "field with thinking=on, or restrict the field to "
                    f"{SHARP_TEMPLATE_MODELS}.")
            cmd += f" --append-system-prompt {shlex.quote(THINK_OFF_MARKER)}"
        return [
            TerminalCommand(
                command=cmd,
                min_timeout_sec=0.0,
                max_timeout_sec=float("inf"),
                block=True,
                append_enter=True,
            )
        ]
