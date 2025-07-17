import sys
import os
import subprocess
import whisper

def extract_audio(video_path, audio_path):
    """Extracts audio from video using ffmpeg."""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path
        ], check=True)
    except subprocess.CalledProcessError:
        print("Failed to extract audio with ffmpeg.")
        sys.exit(1)

def transcribe_audio(audio_path):
    """Transcribes audio using Whisper."""
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <video_file>")
        sys.exit(1)

    video_file = sys.argv[1]

    if not os.path.isfile(video_file):
        print(f"File not found: {video_file}")
        sys.exit(1)

    base_path = os.path.splitext(video_file)[0]
    audio_file = base_path + ".temp.wav"
    transcript_file = video_file + ".transcript.md"

    print("\n[1/3] Extracting audio...")
    extract_audio(video_file, audio_file)

    print("[2/3] Transcribing...")
    transcript = transcribe_audio(audio_file)

    print("[3/3] Saving transcript...")
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(transcript)

    os.remove(audio_file)
    print(f"\nTranscript saved to: {transcript_file}")

if __name__ == "__main__":
    main()
