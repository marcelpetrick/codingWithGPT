# syntax=docker/dockerfile:1
# LinkedIn Reply Assistant: the full app in a container.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Default command: `lra selftest` (offline: OCR + rules + demo backend, no display needed).
# The GUI needs the host's Wayland, D-Bus and PipeWire sockets; see README "Docker".

FROM python:3.14.10-slim-trixie AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc pkg-config libgirepository-2.0-dev libcairo2-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m venv /opt/lra && /opt/lra/bin/pip install --no-cache-dir .

FROM python:3.14.10-slim-trixie
LABEL org.opencontainers.image.title="linkedin-reply-assistant" \
      org.opencontainers.image.description="Capture a LinkedIn conversation, draft a reply with Ollama, insert it. Never sends." \
      org.opencontainers.image.source="https://github.com/marcelpetrick/codingWithGPT" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.authors="Marcel Petrick <mail@marcelpetrick.it>"
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu \
      gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-pipewire \
      gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 libgirepository-2.0-0 libcairo2 \
      libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 libglib2.0-0 fonts-dejavu-core \
      libwayland-client0 libwayland-cursor0 libwayland-egl1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 lra
COPY --from=build /opt/lra /opt/lra
ENV PATH=/opt/lra/bin:$PATH
USER lra
WORKDIR /home/lra
ENTRYPOINT ["lra"]
CMD ["selftest"]
