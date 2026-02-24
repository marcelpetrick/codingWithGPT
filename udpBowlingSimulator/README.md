# UDP CLI Sender for Qt Bowling Scoreboard

Simple interactive command-line tool to send UDP JSON datagrams to the Qt6 Bowling Scoreboard application.

It allows manual testing of the networking and scoring pipeline without the real hardware or backend.

---

## ✨ Features

* Interactive **"what to send?"** prompt
* Sends valid JSON packets via UDP
* Demo command for quick testing
* Raw JSON mode for edge cases
* Clean exit with **Ctrl+C**
* Configurable host and port

---

## 📦 Requirements

* Python **3.10+**
* OS: Linux, macOS, or Windows
* Running Qt application listening on:

```
127.0.0.1:7766
```

(Default used by the current Bowling app)

---

## 📁 Project Structure

```
udp-cli-sender/
│
├── main.py
├── README.md
└── .venv/              # local virtual environment (not committed)
```

---

## 🐍 Python Virtual Environment Setup

### Linux / macOS

```bash
cd udp-cli-sender

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

### Windows (PowerShell)

```powershell
cd udp-cli-sender

python -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
```

### Windows (cmd)

```cmd
cd udp-cli-sender

python -m venv .venv
.venv\Scripts\activate.bat

python -m pip install --upgrade pip
```

> No external dependencies are required.

---

## ▶️ Running the Tool

Activate the virtual environment, then:

```bash
python main.py
```

Or specify a custom target:

```bash
python main.py 127.0.0.1 7766
```

---

## 💬 Interactive Commands

```
send <player_id> <frame_id> <turn> <score>
```

Example:

```
send 1 0 0 10
```

---

```
raw <json>
```

Example:

```
raw {"player_id":2,"frame_id":0,"turn":0,"score":8}
```

---

```
demo
```

Sends a short predefined sequence.

---

```
help
quit / exit
```

---

## 🧾 JSON Packet Format

The Qt application expects:

```json
{
  "player_id": 1,
  "frame_id": 0,
  "turn": 0,
  "score": 10
}
```

### Field Description

| Field     | Type | Description                 |
| --------- | ---- | --------------------------- |
| player_id | int  | Player identifier           |
| frame_id  | int  | Frame index (0–9)           |
| turn      | int  | Roll index within the frame |
| score     | int  | Pins knocked down           |

---

## 🧪 Quick Test Workflow

1. Start the Qt Bowling application
2. Run the UDP CLI sender
3. Execute:

```
demo
```

You should see the UI update immediately.

---

## 🛑 Exit

Press:

```
Ctrl + C
```

or type:

```
quit
```

---

## 🧰 Development Notes

* Uses `socket.AF_INET` + `SOCK_DGRAM`
* Sends compact JSON (no whitespace)
* No blocking network operations
* Safe to run multiple instances

---

## 📄 License

MIT (or match your project license)

---

## Recommended `.gitignore` addition

```
.venv/
__pycache__/
```

---

## Optional: auto-activation helper (Linux/macOS)

If you use this often:

```bash
echo "source .venv/bin/activate" > .envrc
```

(with `direnv`)

