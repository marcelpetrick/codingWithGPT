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

## A full run with demo-game mode

```
    ~/repos/codingWithGPT/udpBowlingSimulator    master *6 !1 ?4  python3 main.py 127.0.0.1 7766                                                                                                                                                                              ✔ 
UDP sender -> 127.0.0.1:7766
Type 'help' for commands. Ctrl+C to quit.
what to send? > demo-game
[demo-game] Players: 1) Will  2) Risk
[demo-game] Delay: 0.35s per packet

[demo-game] Frame 01 | Will -> 4, 5, 0
-> sent 75 bytes: {"player":"Will","turn":0,"first_score":4,"second_score":5,"third_score":0}
[demo-game] Frame 01 | Risk -> 1, 5, 0
-> sent 75 bytes: {"player":"Risk","turn":0,"first_score":1,"second_score":5,"third_score":0}
[demo-game] Frame 02 | Will -> 7, 2, 0
-> sent 75 bytes: {"player":"Will","turn":1,"first_score":7,"second_score":2,"third_score":0}
[demo-game] Frame 02 | Risk -> 5, 3, 0
-> sent 75 bytes: {"player":"Risk","turn":1,"first_score":5,"second_score":3,"third_score":0}
[demo-game] Frame 03 | Will -> 4, 1, 0
-> sent 75 bytes: {"player":"Will","turn":2,"first_score":4,"second_score":1,"third_score":0}
[demo-game] Frame 03 | Risk -> 6, 0, 0
-> sent 75 bytes: {"player":"Risk","turn":2,"first_score":6,"second_score":0,"third_score":0}
[demo-game] Frame 04 | Will -> 8, 0, 0
-> sent 75 bytes: {"player":"Will","turn":3,"first_score":8,"second_score":0,"third_score":0}
[demo-game] Frame 04 | Risk -> 9, 1, 0
-> sent 75 bytes: {"player":"Risk","turn":3,"first_score":9,"second_score":1,"third_score":0}
[demo-game] Frame 05 | Will -> 1, 5, 0
-> sent 75 bytes: {"player":"Will","turn":4,"first_score":1,"second_score":5,"third_score":0}
[demo-game] Frame 05 | Risk -> 3, 1, 0
-> sent 75 bytes: {"player":"Risk","turn":4,"first_score":3,"second_score":1,"third_score":0}
[demo-game] Frame 06 | Will -> 1, 0, 0
-> sent 75 bytes: {"player":"Will","turn":5,"first_score":1,"second_score":0,"third_score":0}
[demo-game] Frame 06 | Risk -> 2, 6, 0
-> sent 75 bytes: {"player":"Risk","turn":5,"first_score":2,"second_score":6,"third_score":0}
[demo-game] Frame 07 | Will -> 7, 3, 0
-> sent 75 bytes: {"player":"Will","turn":6,"first_score":7,"second_score":3,"third_score":0}
[demo-game] Frame 07 | Risk -> 5, 2, 0
-> sent 75 bytes: {"player":"Risk","turn":6,"first_score":5,"second_score":2,"third_score":0}
[demo-game] Frame 08 | Will -> 5, 1, 0
-> sent 75 bytes: {"player":"Will","turn":7,"first_score":5,"second_score":1,"third_score":0}
[demo-game] Frame 08 | Risk -> 8, 2, 0
-> sent 75 bytes: {"player":"Risk","turn":7,"first_score":8,"second_score":2,"third_score":0}
[demo-game] Frame 09 | Will -> 5, 5, 0
-> sent 75 bytes: {"player":"Will","turn":8,"first_score":5,"second_score":5,"third_score":0}
[demo-game] Frame 09 | Risk -> 5, 2, 0
-> sent 75 bytes: {"player":"Risk","turn":8,"first_score":5,"second_score":2,"third_score":0}
[demo-game] Frame 10 | Will -> 0, 5, 0
-> sent 75 bytes: {"player":"Will","turn":9,"first_score":0,"second_score":5,"third_score":0}
[demo-game] Frame 10 | Risk -> 8, 2, 2
-> sent 75 bytes: {"player":"Risk","turn":9,"first_score":8,"second_score":2,"third_score":2}

[demo-game] Finished full game for both players.
what to send? > exit
bye.
    ~/repos/codingWithGPT/udpBowlingSimulator    master *6 !1 ?4         
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
