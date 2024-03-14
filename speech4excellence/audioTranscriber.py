import os
from openai import OpenAI

class AudioTranscriber:
    def __init__(self, api_key):
        """Initialize the AudioTranscriber with the OpenAI API key."""
        if api_key is None:
            raise ValueError("API key must be provided")
        self.client = OpenAI(api_key=api_key)

    def transcribe(self, filename):
        """Transcribe the given audio file to text using OpenAI's audio API."""
        try:
            with open(filename, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcription.text
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {filename} was not found.")
        except Exception as e:
            raise Exception(f"An error occurred during transcription: {e}")


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    transcriber = AudioTranscriber(api_key)
    try:
        transcription = transcriber.transcribe('recording.mp3')
        print(f"Transcription: {transcription}")
    except Exception as e:
        print(f"Error: {e}")
