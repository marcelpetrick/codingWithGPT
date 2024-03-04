import sys
import os
import pygame
import yt_dlp
import moviepy.editor as mp
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
from urllib.request import urlopen
import re

class PlayerHelper:
    def __init__(self):
        self.current_audio_file = None
        self.ogg_audio_file = None
        pygame.mixer.init()

    def direct_search(self, input):
        search_keyword = input.replace(" ", "+")
        html = urlopen("https://www.youtube.com/results?search_query=" + search_keyword)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        result = "https://www.youtube.com/watch?v=" + video_ids[0]
        print("result:", result)
        return result

    def download_and_convert(self, song_url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(song_url, download=True)
            self.current_audio_file = ydl.prepare_filename(info_dict)

        audio = mp.AudioFileClip(self.current_audio_file)
        self.ogg_audio_file = self.current_audio_file.rsplit('.', 1)[0] + '.ogg'
        audio.write_audiofile(self.ogg_audio_file, codec='libvorbis')

    def play_song(self):
        if self.ogg_audio_file:
            pygame.mixer.music.load(self.ogg_audio_file)
            pygame.mixer.music.play()

    def stop_song(self):
        pygame.mixer.music.stop()
        self.cleanup_files()

    def cleanup_files(self):
        if self.ogg_audio_file and os.path.exists(self.ogg_audio_file):
            os.remove(self.ogg_audio_file)
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            os.remove(self.current_audio_file)
        self.current_audio_file = None
        self.ogg_audio_file = None


class Ui_MainWindow(QWidget):
    def __init__(self, player_helper):
        super().__init__()
        self.player_helper = player_helper
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        self.song_title_input = QLineEdit(self)
        self.layout.addWidget(self.song_title_input)

        self.play_button = QPushButton("Play", self)
        self.play_button.clicked.connect(self.on_play_clicked)
        self.layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.layout.addWidget(self.stop_button)

    def on_play_clicked(self):
        song_title = self.song_title_input.text()
        if not song_title:
            return

        song_url = self.player_helper.direct_search(song_title)
        if not song_url:
            return

        self.player_helper.download_and_convert(song_url)
        self.player_helper.play_song()

    def on_stop_clicked(self):
        self.player_helper.stop_song()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    player_helper = PlayerHelper()
    main_window = Ui_MainWindow(player_helper)
    main_window.show()

    sys.exit(app.exec_())
