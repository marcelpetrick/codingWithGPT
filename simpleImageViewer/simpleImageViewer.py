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
        self.dragPos = None


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
        #self.fitInView()

    def wheelEvent(self, event):
        pass

    def mousePressEvent(self, event):
        self.dragPos = event.pos()
        super(PhotoViewer, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragPos:
            moved = event.pos() - self.dragPos
            if moved.manhattanLength() > 4:
                self.dragPos = event.pos()
                self.window().dragged(moved.x())

    def mouseReleaseEvent(self, event):
        self.dragPos = None

class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.viewer = PhotoViewer(self)
        self.setCentralWidget(self.viewer)

        self.files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.png')])
        self.index = 0
        self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))

        #self.showFullScreen() # uncomment this to have a full screen app

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            self.index = (self.index + 1) % len(self.files)
            self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))
        elif event.key() == QtCore.Qt.Key_Left:
            self.index = (self.index - 1) % len(self.files)
            self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))
        super(Window, self).keyPressEvent(event)

    def dragged(self, x):
        if x > 0:
            self.index = (self.index - 1) % len(self.files)
        else:
            self.index = (self.index + 1) % len(self.files)
        self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]))

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
