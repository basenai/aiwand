from PyQt5 import QtCore, QtGui, QtWidgets


class RoundedWidget(QtWidgets.QWidget):
    """Custom widget with rounded corners and shadow that handles its own painting"""

    def __init__(self, parent=None, radius=10, bg_color="#FFFFFF", border_color=None, shadow=True):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = QtGui.QColor(bg_color)
        self.border_color = QtGui.QColor(border_color) if border_color else None
        self.shadow = shadow

        # Make widget receive events and handle transparency
        self.setAttribute(QtCore.Qt.WA_StyledBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        # Critical for event handling
        self.setMouseTracking(True)

    def paintEvent(self, event):
        """Custom paint event to draw rounded corners and border"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw shadow if enabled
        if self.shadow:
            shadow_path = QtGui.QPainterPath()
            shadow_path.addRoundedRect(
                QtCore.QRectF(3, 3, self.width() - 6, self.height() - 6), self.radius, self.radius
            )
            painter.fillPath(shadow_path, QtGui.QColor(0, 0, 0, 15))

        # Create a path for the main background
        path = QtGui.QPainterPath()
        path.addRoundedRect(
            QtCore.QRectF(0, 0, self.width(), self.height()), self.radius, self.radius
        )

        # Draw background
        painter.fillPath(path, self.bg_color)

        # Draw border if color provided
        if self.border_color:
            painter.setPen(QtGui.QPen(self.border_color, 1))
            painter.drawPath(path)

        super().paintEvent(event)

    def mousePressEvent(self, event):
        """Explicitly handle mouse press events"""
        # Stop event propagation to prevent click-through
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Explicitly handle mouse release events"""
        event.accept()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Explicitly handle mouse move events"""
        event.accept()
        super().mouseMoveEvent(event)

    def event(self, event):
        """Override to ensure all events are properly handled"""
        # Make sure widget consumes events
        result = super().event(event)
        if event.type() in (
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.MouseMove,
        ):
            event.accept()
        return result

    def enterEvent(self, event):
        """Handle mouse enter events"""
        event.accept()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events"""
        event.accept()
        super().leaveEvent(event)
