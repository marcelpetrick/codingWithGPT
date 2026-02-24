#!/usr/bin/env python3
import json
import socket
import sys
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7766

HELP = """\
Commands:
  send <player> <turn> <first_score> <second_score> [third_score]
      Send one score packet (third_score is optional; default 0)

  file <path>
      Send JSON from a file (e.g. test/will_0.json). Sends the file content as-is.

  raw <json>
      Send raw JSON typed on the command line (must be a JSON object)

  demo-will
      Sends a few packets like your will_*.json examples.

  help
  quit | exit

Notes:
- Your Qt receiver expects keys: player, turn, first_score, second_score, third_score
- turn is the frame index (0..9) in your model.
- Ctrl+C exits cleanly.
"""

def parse_int(s: str, name: str) -> int:
    try:
        return int(s, 10)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got: {s!r}")

def send_bytes(sock: socket.socket, addr, data: bytes) -> None:
    sock.sendto(data, addr)
    preview = data.decode("utf-8", errors="replace")
    if len(preview) > 200:
        preview = preview[:200] + "..."
    print(f"-> sent {len(data)} bytes: {preview}")

def send_obj(sock: socket.socket, addr, obj: dict) -> None:
    # Compact JSON; Qt's QJsonDocument::fromJson() is fine with this.
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    send_bytes(sock, addr, data)

def validate_payload(obj: dict) -> None:
    # Minimal validation to catch the typical mismatch early
    required = ["player", "turn", "first_score", "second_score", "third_score"]
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f"missing keys: {missing}. Expected {required}")
    if not isinstance(obj["player"], str) or not obj["player"]:
        raise ValueError("player must be a non-empty string")
    # turn/score fields can be int-like; we accept and let Qt clamp defaults if needed
    # but we enforce turn range here because your model rejects >9.
    turn = int(obj["turn"])
    if turn < 0 or turn > 9:
        raise ValueError("turn must be in range 0..9")

def main() -> int:
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = parse_int(sys.argv[2], "port")

    addr = (host, port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f"UDP sender -> {host}:{port}")
    print("Type 'help' for commands. Ctrl+C to quit.")

    try:
        while True:
            line = input("what to send? > ").strip()
            if not line:
                continue

            cmd, *rest = line.split(" ", 1)
            cmd = cmd.lower()

            if cmd in ("quit", "exit"):
                print("bye.")
                return 0

            if cmd == "help":
                print(HELP)
                continue

            if cmd == "send":
                parts = rest[0].split() if rest else []
                if len(parts) not in (4, 5):
                    print("usage: send <player> <turn> <first_score> <second_score> [third_score]")
                    continue

                player = parts[0]
                try:
                    turn = parse_int(parts[1], "turn")
                    first_score = parse_int(parts[2], "first_score")
                    second_score = parse_int(parts[3], "second_score")
                    third_score = parse_int(parts[4], "third_score") if len(parts) == 5 else 0
                except ValueError as e:
                    print(f"error: {e}")
                    continue

                obj = {
                    "player": player,
                    "turn": turn,
                    "first_score": first_score,
                    "second_score": second_score,
                    "third_score": third_score,
                }

                try:
                    validate_payload(obj)
                except ValueError as e:
                    print(f"error: {e}")
                    continue

                send_obj(sock, addr, obj)
                continue

            if cmd == "file":
                if not rest:
                    print("usage: file <path>")
                    continue
                path = Path(rest[0].strip()).expanduser()
                if not path.exists():
                    print(f"error: not found: {path}")
                    continue

                data = path.read_bytes()
                # Optional sanity check: ensure file contains a JSON object the receiver expects
                try:
                    obj = json.loads(data.decode("utf-8"))
                    if not isinstance(obj, dict):
                        raise ValueError("JSON must be an object at top-level")
                    validate_payload(obj)
                except Exception as e:
                    print(f"warning: file JSON didn't validate ({e}); sending as-is anyway.")
                send_bytes(sock, addr, data)
                continue

            if cmd == "raw":
                if not rest:
                    print("usage: raw <json>")
                    continue
                raw = rest[0].strip()
                try:
                    obj = json.loads(raw)
                    if not isinstance(obj, dict):
                        print("error: JSON must be an object")
                        continue
                    validate_payload(obj)
                except Exception as e:
                    print(f"error: invalid/unsupported JSON for this receiver: {e}")
                    continue
                send_obj(sock, addr, obj)
                continue

            if cmd == "demo-will":
                demo_packets = [
                    {"player": "Will", "turn": 0, "first_score": 10, "second_score": 0, "third_score": 0},
                    {"player": "Will", "turn": 2, "first_score": 5,  "second_score": 5, "third_score": 0},
                    {"player": "Will", "turn": 4, "first_score": 10, "second_score": 0, "third_score": 0},
                ]
                for p in demo_packets:
                    send_obj(sock, addr, p)
                continue

            print(f"unknown command: {cmd!r}. type 'help'.")

    except KeyboardInterrupt:
        print("\nCtrl+C -> quitting.")
        return 0
    finally:
        sock.close()

if __name__ == "__main__":
    raise SystemExit(main())
