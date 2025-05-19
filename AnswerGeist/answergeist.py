import sys
import cv2
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QHBoxLayout, QComboBox
)


class CaptureWorker(QThread):
    image_captured = pyqtSignal(QPixmap)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Camera {self.camera_index} could not be opened")
            return

        ret, frame = cap.read()
        cap.release()

        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.image_captured.emit(pixmap)


class CaptureCard(QWidget):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.init_ui(image)

    def init_ui(self, image):
        layout = QHBoxLayout(self)

        image_label = QLabel()
        thumbnail = image.scaledToWidth(160)
        image_label.setPixmap(thumbnail)
        layout.addWidget(image_label)

        self.status_label = QLabel("Processing...")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

    def set_status(self, status_text):
        self.status_label.setText(status_text)


class AnswergeistUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Answergeist")
        self.resize(800, 600)

        self.layout = QVBoxLayout(self)

        # Camera selector
        self.camera_selector = QComboBox()
        self.camera_indices = self.get_available_cameras()
        self.camera_selector.addItems([f"Camera {i}" for i in self.camera_indices])
        self.layout.addWidget(self.camera_selector)

        # Capture button
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.clicked.connect(self.capture_image)
        self.layout.addWidget(self.capture_button)

        # Scrollable area for capture cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

    def get_available_cameras(self, max_tested=5):
        available = []
        for i in range(max_tested):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def capture_image(self):
        selected_index = self.camera_selector.currentIndex()
        camera_index = self.camera_indices[selected_index]
        self.worker = CaptureWorker(camera_index)
        self.worker.image_captured.connect(self.add_result_card)
        self.worker.start()

    def add_result_card(self, image_pixmap):
        card = CaptureCard(image_pixmap)
        self.scroll_layout.addWidget(card)
        QTimer.singleShot(2000, lambda: card.set_status("Complete"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnswergeistUI()
    window.show()
    sys.exit(app.exec_())
