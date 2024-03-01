import sys
import qrcode
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSlot

class CutePrinter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('cutePrinter')
        self.layout = QVBoxLayout()

        self.textEdit = QTextEdit()
        self.textEdit.textChanged.connect(self.onTextChanged)
        self.layout.addWidget(self.textEdit)

        self.imageLabel = QLabel()
        self.layout.addWidget(self.imageLabel)

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
            img_qt = self.convertToQtImage(img)
            self.imageLabel.setPixmap(QPixmap.fromImage(img_qt))

    def convertToQtImage(self, img):
        img.save("temp.jpg")
        qt_img = QImage("temp.jpg")
        return qt_img

def main():
    app = QApplication(sys.argv)
    ex = CutePrinter()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
