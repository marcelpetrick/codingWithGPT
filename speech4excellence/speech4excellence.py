import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
import pyaudio
import wave
from pydub import AudioSegment
import audioop
from audioTranscriber import AudioTranscriber

class AudioRecorder(QThread):
    update_timecode = pyqtSignal(str)
    update_amplitude = pyqtSignal(float)  # New signal for amplitude

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.frames = []

    def run(self):
        self.is_recording = True
        self.frames = []

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=2,
                        rate=44100,
                        input=True,
                        frames_per_buffer=1024)

        while self.is_recording:
            data = stream.read(1024, exception_on_overflow=False)
            self.frames.append(data)
            rms = audioop.rms(data, 2)  # Calculate RMS of the data
            self.update_amplitude.emit(rms)  # Emit the RMS value

        stream.stop_stream()
        stream.close()
        p.terminate()

    def stop(self):
        self.is_recording = False

    def save(self, filename):
        wf = wave.open(filename, 'wb')
        wf.setnchannels(2)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        # Convert to MP3
        sound = AudioSegment.from_wav(filename)
        sound.export(filename.replace('.wav', '.mp3'), format='mp3')
        os.remove(filename)  # Remove the temporary WAV file


class MainWindow(QWidget):
    def __init__(self, transcriber):
        super().__init__()
        self.transcriber = transcriber  # The AudioTranscriber instance
        self.recorder = AudioRecorder()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        self.timecodeLabel = QLabel('00:00:00')
        self.layout.addWidget(self.timecodeLabel)

        self.amplitudeLabel = QLabel('Amplitude: 0')
        self.layout.addWidget(self.amplitudeLabel)

        self.filenameLineEdit = QLineEdit('recording.mp3')
        self.layout.addWidget(self.filenameLineEdit)

        self.recordButton = QPushButton('Record')
        self.recordButton.clicked.connect(self.toggleRecording)
        self.layout.addWidget(self.recordButton)

        self.transcribeButton = QPushButton('Transcribe')
        self.transcribeButton.clicked.connect(self.transcribeAudio)
        self.layout.addWidget(self.transcribeButton)

        self.transcriptionPreview = QTextEdit()
        self.transcriptionPreview.setReadOnly(True)
        self.layout.addWidget(self.transcriptionPreview)

        self.recorder.update_amplitude.connect(self.updateAmplitude)
        self.recorder.update_timecode.connect(self.updateTimecode)

        self.setLayout(self.layout)
        self.setWindowTitle('Audio Recorder and Transcriber')
        self.show()

    def updateAmplitude(self, rms):
        self.amplitudeLabel.setText(f'Amplitude: {rms}')

    def toggleRecording(self):
        if self.recorder.is_recording:
            self.recorder.stop()
            self.recorder.wait()  # Wait for the recording thread to finish
            filename = self.filenameLineEdit.text()
            if not filename.endswith('.mp3'):
                filename += '.mp3'
            self.recorder.save('temp.wav')
            if os.path.exists(filename):
                os.remove(filename)
            os.rename('temp.mp3', filename)
            self.recordButton.setText('Record')
        else:
            self.recorder.start()
            self.recordButton.setText('Stop')

    def updateTimecode(self, timecode):
        self.timecodeLabel.setText(timecode)

    def transcribeAudio(self):
        """Transcribe the recorded audio and display the text."""
        filename = self.filenameLineEdit.text()
        if not os.path.exists(filename):
            self.transcriptionPreview.setText("File not found. Please record something first.")
            return
        try:
            transcription = self.transcriber.transcribe(filename)
            self.transcriptionPreview.setText(transcription)
        except Exception as e:
            self.transcriptionPreview.setText(f"Error during transcription: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
    transcriber = AudioTranscriber(api_key)
    ex = MainWindow(transcriber)
    sys.exit(app.exec_())
