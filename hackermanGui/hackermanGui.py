import sys
import markdown
import random
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QMovie, QPainter, QColor, QPen
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QTextEdit, QLabel, QScrollBar, QProgressBar


FUTURISTIC_STYLE = """
QWidget {
    background-color: #333333;
    color: #FFFFFF;
    font-family: Arial, sans-serif;
    font-size: 12px;
}

QLineEdit {
    background-color: #222222;
    color: #FFFFFF;
    border: 1px solid #666666;
    padding: 5px;
}

QPushButton {
    background-color: #7B68EE;
    color: #FFFFFF;
    border: none;
    padding: 5px 10px;
    margin-left: 5px;
}

QPushButton:hover {
    background-color: #8A2BE2;
}

QProgressBar {
    background-color: #222222;
    color: #FFFFFF;
    border: 1px solid #666666;
    padding: 1px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #7B68EE;
    width: 10px;
}

QTextEdit {
    background-color: #222222;
    color: #FFFFFF;
    border: 1px solid #666666;
    padding: 5px;
}

QLabel {
    color: #FFFFFF;
    font-weight: bold;
}

#loading_spinner {
    width: 16px;
    height: 16px;
    margin-left: 5px;
}
"""


class ProcessThread(QThread):
    resultReady = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        result = self.processPrompt()
        self.resultReady.emit(result)

    def processPrompt(self):
        # Generate random text after 2 seconds
        time.sleep(2)
        random_text = "This is the random result."

        # Format the prompt and random text as Markdown
        formatted_prompt = f"**Prompt:**\n\n{self.prompt}"
        formatted_result = f"\n\n**Result:**\n\n{random_text}\n\n{'-' * 30}"
        return formatted_prompt + formatted_result


class SeparatorLine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(1)
        self.setMaximumHeight(1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(0, 0, 0))
        painter.setPen(pen)
        painter.drawLine(0, 0, self.width(), 0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("hackerman gui")
        self.resize(600, 400)

        self.setStyleSheet(FUTURISTIC_STYLE)

        main_layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        self.prompt_line_edit = QLineEdit()
        self.prompt_line_edit.setMaxLength(2048)
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.processButtonClicked)

        self.separator_line = SeparatorLine()

        input_layout.addWidget(self.prompt_line_edit)
        input_layout.addWidget(self.go_button)

        self.loading_spinner = QProgressBar()
        self.loading_spinner.setRange(0, 0)  # Indeterminate progress
        self.loading_spinner.setTextVisible(False)
        self.loading_spinner.hide()

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.separator_line)
        main_layout.addWidget(self.loading_spinner)

        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True)

        self.stats_label1 = QLabel("Stat 1:")
        self.stats_label2 = QLabel("Stat 2:")
        self.stats_label3 = QLabel("Stat 3:")

        main_layout.addWidget(self.result_text_edit)
        main_layout.addWidget(self.stats_label1)
        main_layout.addWidget(self.stats_label2)
        main_layout.addWidget(self.stats_label3)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.promptResults = ""

    def processButtonClicked(self):
        prompt = self.prompt_line_edit.text()
        if prompt:
            self.disableInput()
            self.startProcessingThread(prompt)

    def startProcessingThread(self, prompt):
        self.loading_spinner.show()
        self.go_button.setEnabled(False)
        self.prompt_line_edit.setEnabled(False)

        self.thread = ProcessThread(prompt)
        self.thread.resultReady.connect(self.updateResult)
        self.thread.finished.connect(self.processingFinished)
        self.thread.start()

    def disableInput(self):
        self.prompt_line_edit.setEnabled(False)
        self.go_button.setEnabled(False)

    def enableInput(self):
        self.prompt_line_edit.setEnabled(True)
        self.go_button.setEnabled(True)
        self.loading_spinner.hide()

    def updateResult(self, result):
        formatted_result = f"<br>{result}"
        self.promptResults += formatted_result
        processed_html = markdown.markdown(self.promptResults)  # Convert result to HTML
        self.result_text_edit.setHtml(processed_html)
        self.scrollResultViewToBottom()

    def processingFinished(self):
        self.enableInput()
        self.prompt_line_edit.clear()

    def scrollResultViewToBottom(self):
        scrollbar = self.result_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def updateStatistics(self, stat1, stat2, stat3):
        self.stats_label1.setText("Stat 1: {}".format(stat1))
        self.stats_label2.setText("Stat 2: {}".format(stat2))
        self.stats_label3.setText("Stat 3: {}".format(stat3))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
