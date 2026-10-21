# what is this?
Test project to implement some sender-receiver-functionality, where the receiver handles the major workload and transfers just a boolean result back to the sender. Should run in the local network. Thought also about using sockets, but this is more valuable.

## Python environment

Use Python 3.11 with the pinned requirements. Pillow 13 requires Python 3.11 or later. The existing NumPy 1.24.3 pin supports Python 3.11.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The optional cat detector also needs YOLOv5 and its model environment. Those dependencies are not included in `requirements.txt`.
