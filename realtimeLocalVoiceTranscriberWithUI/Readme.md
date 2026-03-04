# draft implementation of a local, realtime voice transcriber (from audio to text)
* using right now the Vosk models; have to be downloaded from https://alphacephei.com/vosk/models

## test run with version 0.1.0
```
 python main.py          ✔  realtimeLocalVoiceTranscriberWithUI  
[INFO] Starting application
[INFO] Initializing main window
[INFO] Refreshing microphone device list
[INFO] Querying audio input devices
[INFO] Found 6 input devices
[INFO] Using default model path: /home/mpetrick/repos/codingWithGPT/realtimeLocalVoiceTranscriberWithUI/model
[INFO] GUI started
[INFO] User opened model directory dialog
[INFO] User selected model directory: /home/mpetrick/repos/codingWithGPT/realtimeLocalVoiceTranscriberWithUI/model/vosk-model-small-en-us-0.15
[INFO] User pressed START recording
[INFO] Starting worker thread (device_index=2)
[INFO] Worker start requested (device_index=2)
[INFO] Loading Vosk model from: /home/mpetrick/repos/codingWithGPT/realtimeLocalVoiceTranscriberWithUI/model/vosk-model-small-en-us-0.15
[INFO] Model successfully loaded
[INFO] Opening microphone stream (device=2)
[INFO] Audio stream started
[INFO] Partial transcription: test
[INFO] Partial transcription: test test
[INFO] Partial transcription: test test test
[INFO] Partial transcription: test test test
[INFO] Partial transcription: test test test test
[INFO] Partial transcription: test test test test
[INFO] Partial transcription: test test test test
[INFO] Final transcription: test test test test
[INFO] Partial transcription: for
[INFO] Final transcription: for
zsh: IOT instruction (core dumped)  python main.py
```
