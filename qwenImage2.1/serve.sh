#!/usr/bin/env bash
# Start ComfyUI for Qwen-Image-2.1 on the 8 GB A2000, if it is not already up.
set -euo pipefail

comfy_dir="/home/mpetrick/repos/ComfyUI"
server_url="http://127.0.0.1:8188"

if curl --fail --silent "$server_url/system_stats" >/dev/null 2>&1; then
    echo "ComfyUI already running at $server_url"
    exit 0
fi

echo "Starting ComfyUI (--lowvram) ..." >&2
nohup "$comfy_dir/venv/bin/python" "$comfy_dir/main.py" \
    --lowvram \
    --preview-method none \
    --disable-api-nodes \
    --listen 127.0.0.1 \
    >"$comfy_dir/user/comfyui.log" 2>&1 &

for _ in {1..180}; do
    if curl --fail --silent "$server_url/system_stats" >/dev/null 2>&1; then
        echo "ready at $server_url"
        exit 0
    fi
    sleep 1
done

echo "ComfyUI did not become ready; see $comfy_dir/user/comfyui.log" >&2
exit 1
