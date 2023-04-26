# Write me some python code, which does the following.
# *  have a nice PyQt-Gui with a lineedit where i can enter a song title. right next to it is a play-button and a stop-button.
# * when i enter a song title, it does a search on youtube for the very first hit for that song
# * when i press the play button, it should play that song. maybe by streaming it or downloading it before, i don't know what is best. make a suggestion. i guess just streaming it in the background is better.
# * if i press the stop-button, then the song should stop to be played.

# for pip
# pip install PyQt5 youtube-search-python python-vlc

# I also don't have mpv or any other player installed. just use what can be taken from python or pip.
# pip install pygame

import sys
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
import yt_dlp
import urllib.request
import re
import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTableView, QHeaderView, QAbstractItemView, QScrollBar
from PyQt5.QtCore import Qt, QAbstractTableModel, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem


# player solution without external vlc or ffmpeg
# pip install moviepy --user
import moviepy.editor as mp

def read_loved_songs_file(file_path):
    result = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            try:
                artist, album = eval(line)  # Convert the line to a tuple
                result.append({artist: album})
            except Exception as e:
                print(f"Error parsing line '{line}': {e}")
    return result


# # quick test
# file_path = "lovedSongs.txt"
# data = read_loved_songs_file(file_path)
# print(data)

#-------------------------------------
class ArtistAlbumModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self.data = data

    def rowCount(self, parent=None):
        return len(self.data)

    def columnCount(self, parent=None):
        return 2

    def data(self, index, role):
        if role == Qt.DisplayRole:
            artist_album = list(self.data[index.row()].items())[0]
            return artist_album[index.column()]

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return ["Artist", "Album"][section]


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Music Player")
        self.resize(800, 600) # QApplication.instance().desktop().height())

        layout = QVBoxLayout(self)

        self.lineEdit = QLineEdit(self)
        layout.addWidget(self.lineEdit)

        self.play_button = QPushButton("Play", self)
        layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop", self)
        layout.addWidget(self.stop_button)

        self.artist_album_model = ArtistAlbumModel(read_loved_songs_file("lovedSongs.txt"))

        self.table_view = QTableView(self)
        self.table_view.setModel(self.artist_album_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_view.setFixedHeight(10 * self.table_view.rowHeight(0) + self.table_view.horizontalHeader().height())
        layout.addWidget(self.table_view)

        pygame.mixer.init()

    def search_song(self, song_title):
        search_keyword = song_title.replace(" ", "+")
        html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_keyword)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        result = "https://www.youtube.com/watch?v=" + video_ids[0]
        return result

    # refactored manually
    def prepare_song_file(self, song_title):
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

        # Convert the audio file to .ogg format
        audio = mp.AudioFileClip(audio_file)
        ogg_audio_file = 'temp_audio.ogg'
        audio.write_audiofile(ogg_audio_file, codec='libvorbis')

        return ogg_audio_file

    def play_song(self):
        song_title = self.song_title_input.text()
        if not song_title:
            return

        ogg_audio_file = self.prepare_song_file(song_title)

        pygame.mixer.music.load(ogg_audio_file)
        pygame.mixer.music.play()

    def stop_song(self):
        pygame.mixer.music.stop()

#-------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())
