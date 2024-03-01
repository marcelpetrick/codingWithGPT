import sys
import qrcode
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel, QPushButton, QComboBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSlot

class CutePrinter(QWidget):
    def __init__(self):
        super().__init__()
        self.currentQRImagePath = None  # Path to save the current QR code image
        self.initUI()

    def initUI(self):
        self.setWindowTitle('cutePrinter')
        self.layout = QVBoxLayout()

        self.textEdit = QTextEdit()
        self.textEdit.textChanged.connect(self.onTextChanged)
        self.layout.addWidget(self.textEdit)

        self.imageLabel = QLabel()
        self.layout.addWidget(self.imageLabel)

        self.printerComboBox = QComboBox()
        self.printerComboBox.addItem("None")  # Default selection
        self.printerComboBox.addItems(self.getAvailablePrinters())
        self.layout.addWidget(self.printerComboBox)

        self.printButton = QPushButton('Print Now')
        self.printButton.clicked.connect(self.onPrintButtonClicked)
        self.layout.addWidget(self.printButton)

        self.setLayout(self.layout)
        self.resize(400, 300)

    @pyqtSlot()
    def onTextChanged(self):
        text = self.textEdit.toPlainText()
        if text:  # Only generate QR if there's text
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            self.currentQRImagePath = "temp_qr.jpg"
            img.save(self.currentQRImagePath)
            img_qt = QImage(self.currentQRImagePath)
            self.imageLabel.setPixmap(QPixmap.fromImage(img_qt))

    def getAvailablePrinters(self):
        # Uses the lpstat command to list available printers
        try:
            printers = subprocess.check_output(["lpstat", "-e"]).decode().strip().split('\n')
            return printers
        except subprocess.CalledProcessError as e:
            print("Error fetching printers: ", e)
            return []

    @pyqtSlot()
    def onPrintButtonClicked(self):
        selectedPrinter = self.printerComboBox.currentText()
        if selectedPrinter and selectedPrinter != "None" and self.currentQRImagePath:
            try:
                subprocess.run(["lp", "-d", selectedPrinter, self.currentQRImagePath])
                print(f"Printing on {selectedPrinter}")
            except subprocess.CalledProcessError as e:
                print("Error printing: ", e)

def main():
    app = QApplication(sys.argv)
    ex = CutePrinter()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
