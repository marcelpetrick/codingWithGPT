python3 main.py --v --directory=.                                                                            ✔ 
[git] Found git at: /usr/bin/git
[git] git version 2.52.0
[init] Start directory: /home/mpetrick/repos/codingWithGPT/ownCodeReview
[git] git -C /home/mpetrick/repos/codingWithGPT/ownCodeReview rev-parse --show-toplevel
[init] Repo root: /home/mpetrick/repos/codingWithGPT
[init] Directory filter (repo-relative): 'ownCodeReview'
[git] git -C /home/mpetrick/repos/codingWithGPT rev-parse HEAD
[git] git -C /home/mpetrick/repos/codingWithGPT log -1 --pretty=%s
[git] git -C /home/mpetrick/repos/codingWithGPT log -1 --pretty=%cI
[git] git -C /home/mpetrick/repos/codingWithGPT show --name-only --pretty= HEAD
[git] HEAD: fda7c84736f43da7fed182cf907d3a56cbd9186c
[git] Files touched in HEAD (all): 1
[git] Files after --directory filter: 1
[http] GET http://192.168.100.32:11434/api/tags
[http] http://192.168.100.32:11434/api/tags -> HTTP 200 (3440 chars)
Available Ollama models (/api/tags):
   1. qwen3:8b
   2. qwen3:4b
   3. freehuntx/qwen3-coder:14b
   4. qwen3-vl:4b
   5. qwen3-vl:8b
   6. qwen2.5vl:7b
   7. qwen3-embedding:4b
   8. qwen3:14b
   9. DC1LEX/nomic-embed-text-v1.5-multimodal:latest
  10. nomic-embed-text-v1.5-multimodal:latest
[ollama] Auto-selected 'coder' model: freehuntx/qwen3-coder:14b
[file] #1 relative=ownCodeReview/main.py
[file] #1 resolved=/home/mpetrick/repos/codingWithGPT/ownCodeReview/main.py
[file] #1 read chars=22287 truncated=False
[ollama] #1 /api/generate ...
[ollama] Generating model=freehuntx/qwen3-coder:14b prompt_chars=22734
[http] POST http://192.168.100.32:11434/api/generate (json 24074 bytes)

