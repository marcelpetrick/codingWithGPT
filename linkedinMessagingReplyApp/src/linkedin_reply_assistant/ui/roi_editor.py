# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture preview with ROI overlay, and the dialog to drag a new ROI (§6.4)."""

from PIL import Image
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from linkedin_reply_assistant.capture.roi import Roi


def to_pixmap(image: Image.Image) -> QPixmap:
    rgb = image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimage = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


class PreviewWidget(QWidget):
    """Shows the last capture scaled to fit, with the ROI as a dashed rectangle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.roi: Roi | None = None
        self.placeholder = "No capture yet"
        self.setMinimumSize(QSize(260, 180))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_image(self, image: Image.Image | None) -> None:
        self._pixmap = to_pixmap(image) if image is not None else None
        self.update()

    def image_rect(self) -> QRect:
        if self._pixmap is None:
            return QRect()
        size = self._pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        left = (self.width() - size.width()) // 2
        top = (self.height() - size.height()) // 2
        return QRect(QPoint(left, top), size)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        if self._pixmap is None:
            painter.setPen(self.palette().placeholderText().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder)
            return
        target = self.image_rect()
        painter.drawPixmap(target, self._pixmap)
        if self.roi is not None:
            box = QRect(
                target.left() + round(self.roi.x * target.width()),
                target.top() + round(self.roi.y * target.height()),
                round(self.roi.width * target.width()),
                round(self.roi.height * target.height()),
            )
            painter.setPen(QPen(QColor("#0a66c2"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(box)


class RoiCanvas(PreviewWidget):
    """A preview where the user drags the conversation region."""

    def __init__(self, image: Image.Image, roi: Roi | None) -> None:
        super().__init__()
        self._size = image.size
        self.set_image(image)
        self.roi = roi
        self._start: QPoint | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(QSize(640, 400))

    def _to_image(self, point: QPoint) -> tuple[int, int]:
        rect = self.image_rect()
        x = (point.x() - rect.left()) * self._size[0] / max(1, rect.width())
        y = (point.y() - rect.top()) * self._size[1] / max(1, rect.height())
        return round(x), round(y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._start = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update(event.position().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._update(event.position().toPoint())
        self._start = None

    def _update(self, end: QPoint) -> None:
        if self._start is None:
            return
        x0, y0 = self._to_image(self._start)
        x1, y1 = self._to_image(end)
        try:
            self.roi = Roi.from_pixels(x0, y0, x1, y1, self._size)
        except ValueError:
            return  # too small while dragging; keep the last valid region
        self.update()


class RoiDialog(QDialog):
    def __init__(self, image: Image.Image, roi: Roi | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Capture Region")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Drag a rectangle around the conversation (messages only, no sidebar).")
        )
        self.canvas = RoiCanvas(image, roi)
        layout.addWidget(self.canvas, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def roi(self) -> Roi | None:
        return self.canvas.roi
