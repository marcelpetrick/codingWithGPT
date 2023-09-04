import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
import os

class PhotoViewer(QtWidgets.QGraphicsView):
    photoSwitched = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._empty = True
        self._photo.setPixmap(QtGui.QPixmap())
        self.anim = QPropertyAnimation(self, b"horizontalScrollBar.value")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.OutQuint)

    def loadImage(self, pixmap):
        self._empty = False
        self.setSceneRect(pixmap.rect())
        self._photo.setPixmap(pixmap)
        self.fitInView()

    def fitInView(self):
        self.setSceneRect(QtCore.QRectF(self._photo.pixmap().rect()))
        unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
        self.scale(1 / unity.width(), 1 / unity.height())

    def slidePhotos(self, direction):
        if self._empty:
            return
        startValue = self.horizontalScrollBar().value()
        width = self.viewport().width()
        endValue = startValue + direction * width
        self.anim.setStartValue(startValue)
        self.anim.setEndValue(endValue)
        self.anim.start()
        self.anim.finished.connect(self.photoSwitched.emit)

class ImageViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super(ImageViewer, self).__init__()

        self.viewer = PhotoViewer(self)
        self.setCentralWidget(self.viewer)

        self.files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.png')])
        self.index = 0
        self.viewer.loadImage(QtGui.QPixmap(self.files[self.index]))

        self.viewer.photoSwitched.connect(self.onPhotoSwitched)

    def loadImage(self, direction=1):
        self.index = (self.index + direction) % len(self.files)
        pixmap = QtGui.QPixmap(self.files[self.index])
        self.viewer.loadImage(pixmap)

    def onPhotoSwitched(self):
        direction = 1 if self.viewer.anim.endValue() > self.viewer.anim.startValue() else -1
        self.loadImage(direction)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            self.viewer.slidePhotos(1)
        elif event.key() == QtCore.Qt.Key_Left:
            self.viewer.slidePhotos(-1)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ImageViewer()
    window.showMaximized()
    sys.exit(app.exec_())
