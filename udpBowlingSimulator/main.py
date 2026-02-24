#!/usr/bin/env python3
import json
import socket
import sys

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7766

HELP = """\
Commands:
  send <player_id> <frame_id> <turn> <score>   Send one JSON datagram
  raw <json>                                   Send raw JSON (exactly as typed)
  demo                                          Send a small demo sequence
  help                                          Show this help
  quit | exit                                   Quit

Notes:
- Your app expects keys: player_id, frame_id, turn, score
- All values are integers.
"""

def send_json(sock: socket.socket, addr, payload: dict) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sock.sendto(data, addr)
    print(f"-> sent {len(data)} bytes: {data.decode('utf-8')}")

def parse_int(s: str, name: str) -> int:
    try:
        return int(s, 10)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got: {s!r}")

def main():
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    # Optional CLI args: host port
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
                break

            if cmd == "help":
                print(HELP)
                continue

            if cmd == "send":
                parts = rest[0].split() if rest else []
                if len(parts) != 4:
                    print("usage: send <player_id> <frame_id> <turn> <score>")
                    continue
                try:
                    player_id = parse_int(parts[0], "player_id")
                    frame_id  = parse_int(parts[1], "frame_id")
                    turn      = parse_int(parts[2], "turn")
                    score     = parse_int(parts[3], "score")
                except ValueError as e:
                    print(f"error: {e}")
                    continue

                payload = {
                    "player_id": player_id,
                    "frame_id": frame_id,
                    "turn": turn,
                    "score": score,
                }
                send_json(sock, addr, payload)
                continue

            if cmd == "raw":
                if not rest:
                    print("usage: raw <json>")
                    continue
                raw = rest[0].strip()
                try:
                    obj = json.loads(raw)
                    if not isinstance(obj, dict):
                        print("error: JSON must be an object, e.g. {\"player_id\":1,...}")
                        continue
                except json.JSONDecodeError as e:
                    print(f"error: invalid JSON: {e}")
                    continue
                send_json(sock, addr, obj)
                continue

            if cmd == "demo":
                # A tiny demo: player 1, frame 0, two rolls; then next frame strike
                demo_packets = [
                    {"player_id": 1, "frame_id": 0, "turn": 0, "score": 7},
                    {"player_id": 1, "frame_id": 0, "turn": 1, "score": 2},
                    {"player_id": 1, "frame_id": 1, "turn": 0, "score": 10},
                ]
                for p in demo_packets:
                    send_json(sock, addr, p)
                continue

            print(f"unknown command: {cmd!r}. type 'help'.")

    except KeyboardInterrupt:
        print("\nCtrl+C -> quitting.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
