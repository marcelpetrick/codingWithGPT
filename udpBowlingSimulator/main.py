#!/usr/bin/env python3
import json
import random
import socket
import sys
import time
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

  demo-game [delay_seconds] [seed]
      Simulate a full 10-frame bowling game for TWO random players and send
      updates step-by-step (alternating players each frame).
      - delay_seconds: float (default 0.35)
      - seed: int (optional; makes results deterministic)

  help
  quit | exit

Notes:
- Receiver expects keys: player, turn, first_score, second_score, third_score
- turn is the frame index (0..9) in your model.
- Ctrl+C exits cleanly.
"""

def parse_int(s: str, name: str) -> int:
    try:
        return int(s, 10)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got: {s!r}")

def parse_float(s: str, name: str) -> float:
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{name} must be a number, got: {s!r}")

def send_bytes(sock: socket.socket, addr, data: bytes) -> None:
    sock.sendto(data, addr)
    preview = data.decode("utf-8", errors="replace")
    if len(preview) > 200:
        preview = preview[:200] + "..."
    print(f"-> sent {len(data)} bytes: {preview}")

def send_obj(sock: socket.socket, addr, obj: dict) -> None:
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    send_bytes(sock, addr, data)

def validate_payload(obj: dict) -> None:
    required = ["player", "turn", "first_score", "second_score", "third_score"]
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f"missing keys: {missing}. Expected {required}")
    if not isinstance(obj["player"], str) or not obj["player"]:
        raise ValueError("player must be a non-empty string")
    turn = int(obj["turn"])
    if turn < 0 or turn > 9:
        raise ValueError("turn must be in range 0..9")

# ---------------- Demo game generation ----------------

_FIRST_NAMES = [
    "Will", "Mia", "Noah", "Lena", "Omar", "Zoe", "Kai", "Nora",
    "Ben", "Ivy", "Theo", "Eli", "Ada", "Mila", "Sam", "Lea"
]
_LAST_NAMES = [
    "Fischer", "Novak", "Klein", "Rossi", "Nguyen", "Ito", "Garcia", "Khan",
    "Meyer", "Dubois", "Silva", "Nowak", "Schmidt", "Bauer", "Lopez", "Sato"
]

def random_player_name(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"

def gen_frame_scores(rng: random.Random, frame_index: int) -> tuple[int, int, int]:
    """
    Returns (first, second, third) for a frame.
    Simple bowling rules:
    - Frames 0..8: strike => second=0, third=0; else second in 0..(10-first)
    - Frame 9: if strike or spare => allow third roll
    """
    if frame_index < 9:
        first = rng.randint(0, 10)
        if first == 10:
            return 10, 0, 0
        second = rng.randint(0, 10 - first)
        return first, second, 0

    # 10th frame
    first = rng.randint(0, 10)
    if first == 10:
        # strike: second is 0..10, third is 0..10 (simplified; common enough for UI demo)
        second = rng.randint(0, 10)
        third = rng.randint(0, 10)
        return first, second, third

    second = rng.randint(0, 10 - first)
    if first + second == 10:
        # spare: allow one more ball
        third = rng.randint(0, 10)
        return first, second, third

    return first, second, 0

def run_demo_game(sock: socket.socket, addr, delay_s: float = 0.35, seed: int | None = None) -> None:
    rng = random.Random(seed)

    # Fixed player names
    p1 = "Will"
    p2 = "Risk"

    print(f"[demo-game] Players: 1) {p1}  2) {p2}")
    if seed is not None:
        print(f"[demo-game] Seed: {seed}")
    print(f"[demo-game] Delay: {delay_s:.2f}s per packet\n")

    # Pre-generate a full game (10 frames) for each player
    game = {
        p1: [gen_frame_scores(rng, f) for f in range(10)],
        p2: [gen_frame_scores(rng, f) for f in range(10)],
    }

    # Send step-by-step: alternate players per frame
    for frame in range(10):
        for player in (p1, p2):
            first, second, third = game[player][frame]

            packet = {
                "player": player,
                "turn": frame,
                "first_score": first,
                "second_score": second,
                "third_score": third,
            }

            validate_payload(packet)

            print(
                f"[demo-game] Frame {frame+1:02d} | {player:<4} -> "
                f"{first}, {second}, {third}"
            )

            send_obj(sock, addr, packet)
            time.sleep(delay_s)

    print("\n[demo-game] Finished full game for both players.")

# ---------------- CLI ----------------

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

            if cmd == "demo-game":
                parts = rest[0].split() if rest else []
                delay_s = 0.35
                seed = None
                try:
                    if len(parts) >= 1:
                        delay_s = parse_float(parts[0], "delay_seconds")
                    if len(parts) >= 2:
                        seed = parse_int(parts[1], "seed")
                except ValueError as e:
                    print(f"error: {e}")
                    continue

                run_demo_game(sock, addr, delay_s=delay_s, seed=seed)
                continue

            print(f"unknown command: {cmd!r}. type 'help'.")

    except KeyboardInterrupt:
        print("\nCtrl+C -> quitting.")
        return 0
    finally:
        sock.close()

if __name__ == "__main__":
    raise SystemExit(main())
