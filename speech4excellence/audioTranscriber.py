from openai import OpenAI
import os

class AudioTranscriber:

    def transcribe(self, filename):
        client = OpenAI()
        audio_file = open(filename, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        #print(f"Transcription: {transcription.text}")
        return transcription.text

# Example usage:
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key}")
transcriber = AudioTranscriber()
transcription = transcriber.transcribe('recording.mp3')
print(f"transcription: {transcription}")
