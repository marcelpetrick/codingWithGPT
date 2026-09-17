# Self-contained agent image for running an ABLITERATED model's Claude Code
# sessions with no host filesystem and no general network. Everything the
# session needs is baked in, because at runtime the container sits on a Docker
# --internal network with no route to anything but the inference relay.
#
# Every version here is pinned exactly and checked against its registry
# (2026-09-17). Two of them are pinned to match the HOST exactly, on purpose:
# review.md R4 found that comparing a sandboxed CyberTiel session against a
# host Tiel session confounds the model with its environment. Python 3.14.7 and
# pytest 9.1.1 are what the host runs, so the fixture now executes on the same
# interpreter and the same test framework in both harnesses.
FROM python:3.14.7-slim-trixie

# Node is here only to run the Claude Code CLI. 24.21.0 is the current LTS
# ("Krypton"); the newer 26.x line is not LTS and a benchmark harness has no
# reason to track it.
ARG NODE_VERSION=24.21.0
ARG CLAUDE_VERSION=2.1.274
ARG PYTEST_VERSION=9.1.1

# git for the fixture's repository, curl for the in-container health check,
# xz-utils only to unpack Node (removed again in the same layer).
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates curl xz-utils \
 && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      -o /tmp/node.tar.xz \
 && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
      --exclude=CHANGELOG.md --exclude=LICENSE --exclude=README.md \
 && rm /tmp/node.tar.xz \
 && apt-get purge -y xz-utils && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "pytest==${PYTEST_VERSION}" \
 && npm install -g "@anthropic-ai/claude-code@${CLAUDE_VERSION}" \
 && npm cache clean --force

# Non-root. python:*-slim ships no uid-1000 user, so create one; the workdir is
# a tmpfs mount created at run time and owned by it.
RUN useradd -m -u 1000 agent
USER agent
WORKDIR /work
ENV HOME=/home/agent \
    PYTHONDONTWRITEBYTECODE=1 \
    npm_config_update_notifier=false
ENTRYPOINT ["/bin/bash","-lc"]
