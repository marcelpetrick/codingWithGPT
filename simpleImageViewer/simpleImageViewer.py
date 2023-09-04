import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint
import os


class PositionHolder(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(QtCore.QPointF)

    def __init__(self):
        super(PositionHolder, self).__init__()
        self._pos = QtCore.QPointF(0, 0)

    @QtCore.pyqtProperty(QtCore.QPointF, notify=valueChanged)
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        if self._pos != value:
            self._pos = value
            self.valueChanged.emit(self._pos)


class PhotoViewer(QtWidgets.QGraphicsView):

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)

        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._nextPhoto = QtWidgets.QGraphicsPixmapItem()

        self._scene.addItem(self._photo)
        self._scene.addItem(self._nextPhoto)

        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.positionHolder = PositionHolder()
        self.positionHolder.valueChanged.connect(self._photo.setPos)

        self.anim = QPropertyAnimation(self.positionHolder, b"pos")
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.OutQuint)

        self.dragPos = None

    def setPhotos(self, currentPixmap, nextPixmap, direction):
        self._photo.setPixmap(currentPixmap)
        self._nextPhoto.setPixmap(nextPixmap)

        start_pos = QPoint(0, 0)
        end_pos = QPoint(-direction * currentPixmap.width(), 0)
        self._nextPhoto.setPos(direction * currentPixmap.width(), 0)

        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)
        self.anim.start()

    def fitInView(self):
        self.setSceneRect(QtCore.QRectF(self._photo.pixmap().rect()))
        unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
        self.scale(1 / unity.width(), 1 / unity.height())

    def mousePressEvent(self, event):
        self.dragPos = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragPos:
            moved = event.pos() - self.dragPos
            if abs(moved.x()) > 5:
                direction = 1 if moved.x() > 0 else -1
                self.window().dragged(direction)
                self.dragPos = None

    def mouseReleaseEvent(self, event):
        self.dragPos = None


class ImageViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super(ImageViewer, self).__init__()

        self.viewer = PhotoViewer(self)
        self.setCentralWidget(self.viewer)

        self.files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.png')])
        self.index = 0

        self.loadImage()

    def loadImage(self):
        if self.files:
            pixmap = QtGui.QPixmap(self.files[self.index])
            next_index = (self.index + 1) % len(self.files)
            next_pixmap = QtGui.QPixmap(self.files[next_index])
            self.viewer.setPhotos(pixmap, next_pixmap, 1)
            self.viewer.fitInView()

    def keyPressEvent(self, event):
        direction = 0
        if event.key() == QtCore.Qt.Key_Right:
            direction = 1
        elif event.key() == QtCore.Qt.Key_Left:
            direction = -1
        if direction:
            self.dragged(direction)

    def dragged(self, direction):
        if direction == 1:  # Right
            self.index = (self.index + 1) % len(self.files)
        else:  # Left
            self.index = (self.index - 1) % len(self.files)
        self.loadImage()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ImageViewer()
    window.showMaximized()
    sys.exit(app.exec_())
