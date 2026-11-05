# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ARG APP_VERSION
LABEL org.opencontainers.image.source="https://github.com/marcelpetrick/codingWithGPT" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.licenses="GPL-3.0-or-later"
WORKDIR /site
COPY ollamaClaudeCode_v5_kolibri_tests/dashboard.html /site/dashboard.html
COPY ollamaClaudeCode_v5_kolibri_tests/KOLIBRI_Q3_RUN.md /site/KOLIBRI_Q3_RUN.md
COPY ollamaClaudeCode_v5_kolibri_tests/measurements /site/measurements
COPY ollamaClaudeCode_v4_tielCoder/dashboard.html /site/ollamaClaudeCode_v4_tielCoder/dashboard.html
USER 65534:65534
EXPOSE 8080
CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "/site"]
