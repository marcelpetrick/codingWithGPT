import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
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

        self._nextPhoto = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._nextPhoto)

        self.positionHolder = PositionHolder()
        self.anim = QPropertyAnimation(self.positionHolder, b'pos')
        self.positionHolder.valueChanged.connect(self._photo.setPos)

        self.anim.setDuration(1000)  # duration of the animation in milliseconds
        self.anim.setEasingCurve(QEasingCurve.OutQuint)


    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        #rect = QtCore.QRectF(self._photo.pixmap().rect())
        rect = QtCore.QRectF(0, 0, self._photo.pixmap().width(), self._photo.pixmap().height())

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

    def setPhoto(self, pixmap=None, direction=1):
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

        # Calculate start and end positions for animation
        start_pos = self._photo.pos()
        end_pos = QtCore.QPointF(-direction * self._photo.pixmap().width(), start_pos.y())
        #next_start_pos = QtCore.QPointF(direction * self._photo.pixmap().width(), start_pos.y())
        next_start_pos = QtCore.QPointF(start_pos.x() + direction * self._photo.pixmap().width(), start_pos.y())

        # Setup the next photo
        self._nextPhoto.setPixmap(pixmap)
        self._nextPhoto.setPos(next_start_pos)

        # Swap photo references so that _nextPhoto becomes the _photo after animation
        self._photo, self._nextPhoto = self._nextPhoto, self._photo

        # Start animation
        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)
        self.anim.start()

        self.fitInView()

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

        self.showFullScreen() # uncomment this to have a full screen app

    def keyPressEvent(self, event):
        direction = 0
        if event.key() == QtCore.Qt.Key_Right:
            self.index = (self.index + 1) % len(self.files)
            direction = 1
        elif event.key() == QtCore.Qt.Key_Left:
            self.index = (self.index - 1) % len(self.files)
            direction = -1
        if direction:
            self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]), direction)
        super(Window, self).keyPressEvent(event)

    def dragged(self, x):
        direction = 1 if x > 0 else -1
        self.index = (self.index - direction) % len(self.files)
        self.viewer.setPhoto(QtGui.QPixmap(self.files[self.index]), direction)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
