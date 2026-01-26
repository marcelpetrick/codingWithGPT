import json
import sys
import urllib.request

HOST = "http://192.168.100.32:11434"
# HOST = "http://localhost:11434"   # change if needed
TAGS_PATH = "/api/tags"

def main():
    url = HOST.rstrip("/") + TAGS_PATH
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"Error connecting to Ollama at {url}: {e}", file=sys.stderr)
        sys.exit(1)

    models = data.get("models", [])
    if not models:
        print("No models found.")
        return

    for m in models:
        name = m.get("name")
        if name:
            print(name)

if __name__ == "__main__":
    main()
