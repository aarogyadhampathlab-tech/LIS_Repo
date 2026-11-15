from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QDialog, QWidget

COLORS = {
    "background": "#11191D",
    "surface": "#182327",
    "surface_alt": "#1E2D31",
    "border": "#2C3E42",
    "text": "#E8F0ED",
    "muted": "#96A9A4",
    "accent": "#75C7B3",
    "accent_dark": "#245E55",
    "accent_soft": "#243B3A",
    "online": "#77C99A",
    "offline": "#E58B83",
    "warning": "#E7BB70",
}

class DraggableDialog(QDialog):
    drag_position_changed = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_offset = None
        self._dragged = False

    def add_drag_area(self, widget):
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        if isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._dragged = False
            elif (
                event.type() == QEvent.Type.MouseMove
                and self._drag_offset is not None
                and event.buttons() & Qt.MouseButton.LeftButton
            ):
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                self._dragged = True
                self.drag_position_changed.emit(self.frameGeometry().topLeft())
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
                if self._dragged:
                    self._dragged = False
                    return True
        return super().eventFilter(watched, event)
