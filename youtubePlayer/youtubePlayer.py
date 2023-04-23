# Write me some python code, which does the following.
# *  have a nice PyQt-Gui with a lineedit where i can enter a song title. right next to it is a play-button and a stop-button.
# * when i enter a song title, it does a search on youtube for the very first hit for that song
# * when i press the play button, it should play that song. maybe by streaming it or downloading it before, i don't know what is best. make a suggestion. i guess just streaming it in the background is better.
# * if i press the stop-button, then the song should stop to be played.

# for pip
# pip install PyQt5 youtube-search-python python-vlc

# I also don't have mpv or any other player installed. just use what can be taken from python or pip.
# pip install pygame
# pip install pygame

#pip install youtube_dl

import sys
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
import yt_dlp
from yt_dlp import YoutubeDL

# inserted to replace youtube-search and googlesearch
def directSearch(input):
    import urllib.request
    import re

    search_keyword = input.replace(" ", "+")
    html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_keyword)
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    result = "https://www.youtube.com/watch?v=" + video_ids[0]
    print("result:", result)
    return result

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
        return directSearch(song_title)

    def play_song(self):
        song_title = self.song_title_input.text()
        if not song_title:
            return

        song_url = self.search_song(song_title)
        if not song_url:
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'temp_audio.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([song_url])

        audio_file = ydl.prepare_filename(ydl.extract_info(song_url, download=False))
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()

    def stop_song(self):
        pygame.mixer.music.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())


# problem with js-part of the player: googled myself
# pip install git+https://github.com/blackjack4494/yt-dlc
