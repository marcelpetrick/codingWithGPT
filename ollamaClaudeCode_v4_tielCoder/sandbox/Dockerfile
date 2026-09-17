# Self-contained agent image for running an ABLITERATED model's Claude Code
# sessions with no host filesystem and no general network. Everything the
# session needs is baked in, because at runtime the container sits on a Docker
# --internal network with no route to anything but the inference relay.
FROM node:22-slim

# git+python+pytest for the fixtures; curl only for an in-container health check.
RUN apt-get update && apt-get install -y --no-install-recommends \
      git python3 python3-pytest ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# The exact Claude Code the host uses (pinned so the sandbox is reproducible).
ARG CLAUDE_VERSION=2.1.274
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_VERSION}" \
 && npm cache clean --force

# Non-root: reuse the base image's uid-1000 "node" user. The workdir is a
# tmpfs mount created at run time and chowned to it.
USER node
WORKDIR /work
ENV HOME=/home/node \
    PYTHONDONTWRITEBYTECODE=1 \
    npm_config_update_notifier=false
ENTRYPOINT ["/bin/bash","-lc"]
