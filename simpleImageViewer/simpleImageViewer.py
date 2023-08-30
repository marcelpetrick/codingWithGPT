# I need a python  script, which can read a given input folder, where several images files are located.
# Load those files and display them full screen. When the user swipes on the touch-display to the left, load the next image, then the next and then start a new (just like for nay ring-buffer). For swiping right the previous image shall be shwon.
# Libraries to use are free, but maybe stick at maximum to PyQt or something.
# The program should not react to any other input. Just the swipes left and right (maybe with mouse event it would be drag left and right?).
# Also the program should not show any window borders or something. Just the image full screen.

import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import os

class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.mousePressPos = None

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        pass

    def mousePressEvent(self, event):
        self.mousePressPos = event.pos()
        super(PhotoViewer, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        moved = event.pos() - self.mousePressPos
        if moved.manhattanLength() > 4:
            event.ignore()
            return
        super(PhotoViewer, self).mouseReleaseEvent(event)


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.viewer = PhotoViewer(self)
        self.setCentralWidget(self.viewer)
        self.viewer.setPhoto(QtGui.QPixmap('1.png'))
        self.index = 0
        self.files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.png')]

        self.show()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            self.index = (self.index + 1) % len(self.files)
            self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))
        elif event.key() == QtCore.Qt.Key_Left:
            self.index = (self.index - 1) % len(self.files)
            self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))
        super(Window, self).keyPressEvent(event)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
