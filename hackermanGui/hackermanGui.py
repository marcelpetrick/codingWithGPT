import sys
import markdown
import random
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QTextEdit, QLabel, QScrollBar


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
"""


class ProcessThread(QThread):
    resultReady = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        self.resultReady.emit(self.processPrompt())

    def processPrompt(self):
        # Generate random text after 2 seconds
        time.sleep(2)
        random_text = "This is the random result."

        # Format the prompt and random text as Markdown
        formatted_prompt = f"**Prompt:**\n\n{self.prompt}\n\n**Result:**\n\n{random_text}"
        return formatted_prompt


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
        input_layout.addWidget(self.prompt_line_edit)
        input_layout.addWidget(self.go_button)

        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True)

        self.stats_label1 = QLabel("Stat 1:")
        self.stats_label2 = QLabel("Stat 2:")
        self.stats_label3 = QLabel("Stat 3:")

        main_layout.addLayout(input_layout)
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
        self.thread = ProcessThread(prompt)
        self.thread.resultReady.connect(self.updateResult)
        self.thread.finished.connect(self.enableInput)
        self.thread.start()

    def disableInput(self):
        self.prompt_line_edit.setEnabled(False)
        self.go_button.setEnabled(False)

    def enableInput(self):
        self.prompt_line_edit.setEnabled(True)
        self.go_button.setEnabled(True)

    def updateResult(self, result):
        self.promptResults += "<br>" + result
        processed_html = markdown.markdown(self.promptResults)  # Convert result to HTML
        self.result_text_edit.setHtml(processed_html)

    def updateStatistics(self, stat1, stat2, stat3):
        self.stats_label1.setText("Stat 1: {}".format(stat1))
        self.stats_label2.setText("Stat 2: {}".format(stat2))
        self.stats_label3.setText("Stat 3: {}".format(stat3))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
