import sys
import markdown
import random
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QMovie, QPainter, QColor, QPen
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QTextEdit, QLabel, QScrollBar, QProgressBar
from PyQt5.QtGui import QIcon
import os
import openai
import time

openai.api_key = os.getenv("OPENAI_API_KEY")

def gpt4request(gpt_prompt):
  #gpt_prompt = input ("What prompt do you want to use: ")
  print(f"Working with gpt_prompt: {gpt_prompt}")
  #gpt_prompt = "Write me a python program which prints the very first 100 prime numbers. Not up to 100, but the first 100 ones."
  start_time = time.time()

  message=[{"role": "user", "content": gpt_prompt}]
  response = openai.ChatCompletion.create(
      model="gpt-4-0613",
      messages = message,
      temperature=0.2,
      max_tokens=1000,
      frequency_penalty=0.0
  )
  end_time = time.time()

  elapsed_time = end_time - start_time
  print(f"The code took {elapsed_time} seconds to run.")
  print(f"response: {response}")
  return response


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
    tokenCountReady = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        result = self.processPrompt()
        self.tokenCountReady.emit(str(result[1]))
        self.resultReady.emit(result[0])

    def processPrompt(self):
        result = gpt4request(self.prompt)

        processedResult = result["choices"][0]["message"]["content"]
        tokenUsage = result["usage"]["total_tokens"]
        #print(f"used tokens: {tokenUsage}")

        # Format the prompt and random text as Markdown
        formatted_prompt = f"**Prompt:**\n\n{self.prompt}"
        formatted_result = f"\n\n**Result:**\n\n{processedResult}\n\n{'-' * 30}"

        return [formatted_prompt + formatted_result, tokenUsage]


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
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(600, 400)

        self.setStyleSheet(FUTURISTIC_STYLE)

        main_layout = QVBoxLayout()

        # Create API key input field
        api_layout = QHBoxLayout()
        self.api_label = QLabel("OpenAI API key:")
        self.api_line_edit = QLineEdit()
        self.api_line_edit.setMaxLength(2048)
        api_layout.addWidget(self.api_label)
        api_layout.addWidget(self.api_line_edit)

        input_layout = QHBoxLayout()
        self.prompt_label = QLabel("Prompt:")
        self.prompt_line_edit = QLineEdit()
        self.prompt_line_edit.setMaxLength(2048)
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.processButtonClicked)
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.prompt_line_edit)
        input_layout.addWidget(self.go_button)

        self.separator_line = SeparatorLine()

        self.loading_spinner = QProgressBar()
        self.loading_spinner.setRange(0, 0)  # Indeterminate progress
        self.loading_spinner.setTextVisible(False)
        self.loading_spinner.hide()

        # Add API layout to main layout
        main_layout.addLayout(api_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.separator_line)
        main_layout.addWidget(self.loading_spinner)

        # Initialize internal variable for API key
        self.api_key = ""

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

        self.currentTokens = 0
        self.usedTokens = 0

        self.updateStatistics()

    def processButtonClicked(self):
        prompt = self.prompt_line_edit.text()
        self.api_key = self.api_line_edit.text()  # Update the API key variable with user input
        if prompt:
            self.disableInput()
            self.startProcessingThread(prompt)

    def startProcessingThread(self, prompt):
        self.loading_spinner.show()
        self.go_button.setEnabled(False)
        self.prompt_line_edit.setEnabled(False)

        self.thread = ProcessThread(prompt)
        self.thread.resultReady.connect(self.updateResult)
        self.thread.tokenCountReady.connect(self.updateTokenCount)
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
        self.updateStatistics()

    def updateTokenCount(self, result):
        self.currentTokens = int(result)
        self.usedTokens += self.currentTokens

    def processingFinished(self):
        self.enableInput()
        self.prompt_line_edit.clear()

    def scrollResultViewToBottom(self):
        scrollbar = self.result_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def updateStatistics(self):
        self.stats_label1.setText("Used tokens currently: {}".format(self.currentTokens))
        self.stats_label2.setText("Used tokens total: {}".format(self.usedTokens))
        self.stats_label3.setText("Used money: ~{} $".format(self.usedTokens / 1000 * 0.03))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
