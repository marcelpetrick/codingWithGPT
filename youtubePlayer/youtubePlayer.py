# Write me some python code, which does the following.
# *  have a nice PyQt-Gui with a lineedit where i can enter a song title. right next to it is a play-button and a stop-button.
# * when i enter a song title, it does a search on youtube for the very first hit for that song
# * when i press the play button, it should play that song. maybe by streaming it or downloading it before, i don't know what is best. make a suggestion. i guess just streaming it in the background is better.
# * if i press the stop-button, then the song should stop to be played.

# for pip
# pip install PyQt5 youtube-search-python python-vlc

# I also dont have mpv or any other player installed. just use what can be taken from python or pip.
# pip install pygame
# pip install pygame

import sys
import pygame
#import pafy
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
# there is no module name youtube search
# from youtube_search import YoutubeSearch

#pip install youtube_dl

import sys
import pygame
import pafy
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
from googlesearch import search

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()

        self.song_title_input = QLineEdit(self)
        self.layout.addWidget(self.song_title_input)

        self.play_button = QPushButton("Play", self)
        self.play_button.clicked.connect(self.play_song)
        self.layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_song)
        self.layout.addWidget(self.stop_button)

        self.setLayout(self.layout)

        pygame.mixer.init()

    def search_song(self, song_title):
        query = f"{song_title} site:youtube.com"
        print("after the query")
        for j in search(query, num_results=1):
            return j
        return None

    def play_song(self):
        song_title = self.song_title_input.text()
        if not song_title:
            return

        print("song_title:", song_title) # added by me

        song_url = self.search_song(song_title)
        if not song_url:
            return

        print("song_url:", song_url)  # added by me

        video = pafy.new(song_url)
        best_audio = video.getbestaudio()
        audio_url = best_audio.url

        pygame.mixer.music.load(audio_url)
        pygame.mixer.music.play()

    def stop_song(self):
        pygame.mixer.music.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())
