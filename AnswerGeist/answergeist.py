import sys
import cv2
import os
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QHBoxLayout, QComboBox
)


class CaptureWorker(QThread):
    image_captured = pyqtSignal(QPixmap, str)

    def __init__(self, camera_index=0, camera_name="Camera", resolution=(640, 480)):
        super().__init__()
        self.camera_index = camera_index
        self.camera_name = camera_name
        self.resolution = resolution

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Camera {self.camera_index} could not be opened")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        ret, frame = cap.read()
        cap.release()

        if ret:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.camera_name}_{timestamp}.jpg"
            filepath = os.path.join(output_dir, filename)
            try:
                cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            except Exception as e:
                print(f"Failed to save image: {e}")
                return

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.image_captured.emit(pixmap, filename)


class CaptureCard(QWidget):
    def __init__(self, image, filename, parent=None):
        super().__init__(parent)
        self.init_ui(image, filename)

    def init_ui(self, image, filename):
        layout = QHBoxLayout(self)

        image_label = QLabel()
        thumbnail = image.scaledToWidth(160)
        image_label.setPixmap(thumbnail)
        layout.addWidget(image_label)

        self.status_label = QLabel(f"Saved: output/{filename}\nStatus: Processing...")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

    def set_status(self, status_text):
        current_text = self.status_label.text().split('\n')[0]
        self.status_label.setText(f"{current_text}\nStatus: {status_text}")


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

        # Resolution selector
        self.resolution_selector = QComboBox()
        self.resolution_options = [(1920, 1080), (1280, 720), (1024, 768), (800, 600), (640, 480)]
        self.resolution_selector.addItems([f"{w}x{h}" for w, h in self.resolution_options])
        self.resolution_selector.setCurrentIndex(len(self.resolution_options) - 1)
        self.layout.addWidget(self.resolution_selector)

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
        camera_name = self.camera_selector.currentText().replace(" ", "")

        resolution_index = self.resolution_selector.currentIndex()
        resolution = self.resolution_options[resolution_index]

        self.worker = CaptureWorker(camera_index, camera_name, resolution)
        self.worker.image_captured.connect(self.add_result_card)
        self.worker.start()

    def add_result_card(self, image_pixmap, filename):
        card = CaptureCard(image_pixmap, filename)
        self.scroll_layout.addWidget(card)
        QTimer.singleShot(2000, lambda: card.set_status("Complete"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnswergeistUI()
    window.show()
    sys.exit(app.exec_())
