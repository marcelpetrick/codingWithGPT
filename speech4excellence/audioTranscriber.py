from openai import OpenAI
import os

class AudioTranscriber:
    def __init__(self, api_key):
        self.api_key = api_key
        #openai.api_key = self.api_key

    def transcribe(self, filename):
        #from openai import OpenAI
        client = OpenAI()

        audio_file = open(filename, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            #response_format="text"
        )
        print(f"Transcription: {transcription.text}")
        return transcription.text

# Example usage:
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key}")
transcriber = AudioTranscriber(api_key=api_key)
transcription = transcriber.transcribe('recording.mp3')
print(transcription)
