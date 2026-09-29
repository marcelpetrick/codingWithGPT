#!/bin/sh
# Re-fetch install.sh and the amd64 archive listing (streams ~1.4 GB, writes only the listing), then rebuild.
set -eu
cd "$(dirname "$0")"
tag=$(curl -fsSI https://github.com/ollama/ollama/releases/latest | tr -d '\r' | sed -n 's#^[Ll]ocation: .*/tag/##p')
curl -fsSL https://ollama.com/install.sh -o install.sh.new && mv install.sh.new install.sh
curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -tvf - > contents.new
mv contents.new ollama-linux-amd64.contents.txt
echo "$(date -u +%Y-%m-%d) (release $tag)" > FETCHED
python3 build.py
