import os
import time
import pygame

# Configuration
HUB_LOCATION = "2-1"  # Replace with your USB hub location
PORT_NUMBER = 1  # The port to control
NOTES_FILE = "odeToJoy.notes"  # File containing notes (e.g., C D E F G)
TEMPO = 120  # Beats per minute (default)

# Calculate note duration based on tempo
def calculate_note_duration(tempo):
    return 60 / tempo  # Duration of a quarter note in seconds

# Turn the USB hub port on
def turn_on_usb_port():
    os.system(f"sudo uhubctl -l {HUB_LOCATION} -p {PORT_NUMBER} -a 1")

# Turn the USB hub port off
def turn_off_usb_port():
    os.system(f"sudo uhubctl -l {HUB_LOCATION} -p {PORT_NUMBER} -a 0")

# Load notes from a file
def load_notes(file_path):
    with open(file_path, "r") as file:
        notes = file.read().strip().split()
    return notes

# Play a note using pygame
def play_audio(note, duration):
    frequencies = {
        "C": 261.63,
        "D": 293.66,
        "E": 329.63,
        "F": 349.23,
        "G": 392.00,
        "A": 440.00,
        "B": 493.88,
    }

    if note not in frequencies:
        return  # Skip invalid notes

    frequency = frequencies[note]
    sample_rate = 44100  # Hz
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)  # Time array
    wave = (32767 * 0.5 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)  # Sine wave

    pygame.mixer.init(frequency=sample_rate)
    sound = pygame.sndarray.make_sound(wave)
    sound.play()
    time.sleep(duration)
    sound.stop()

# Main function to play notes and control USB LED
def main():
    note_duration = calculate_note_duration(TEMPO)
    notes = load_notes(NOTES_FILE)

    for note in notes:
        print(f"Playing note: {note}")

        # Turn on USB port
        turn_on_usb_port()

        # Play audio for the note
        play_audio(note, note_duration)

        # Turn off USB port after note duration
        turn_off_usb_port()
        time.sleep(note_duration / 2)  # Add a short gap between notes

if __name__ == "__main__":
    main()
