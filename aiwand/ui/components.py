from typing import Optional

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QFont, QIcon

from aiwand.config import Config

QPushButton = QtWidgets.QPushButton
QLabel = QtWidgets.QLabel
QTextEdit = QtWidgets.QTextEdit


class UIComponents:
    """Reusable UI components with consistent styling"""

    @staticmethod
    def create_rounded_widget(
        widget,
        radius: int = 10,
        bg_color: str = "#FFFFFF",
        border_color: Optional[str] = None,
        shadow: bool = True,
    ):
        """Apply rounded corners to any widget"""
        widget.setStyleSheet(f"""
            background-color: {bg_color};
            border-radius: {radius}px;
            {f'border: 1px solid {border_color};' if border_color else ''}
        """)
        if shadow:
            shadow_effect = QtWidgets.QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(15)
            shadow_effect.setColor(QtGui.QColor(0, 0, 0, 30))
            shadow_effect.setOffset(0, 2)
            widget.setGraphicsEffect(shadow_effect)
        return widget

    @staticmethod
    def create_button(
        text: str, icon: Optional[str] = None, primary: bool = True, config: Optional[Config] = None
    ):
        """Create a styled button with optional icon"""
        button = QPushButton(text)
        if config:
            color = config.PRIMARY_COLOR if primary else config.INACTIVE_COLOR
            radius = config.BORDER_RADIUS
        else:
            color = "#007AFF" if primary else "#8E8E93"
            radius = 10
        if icon:
            button.setIcon(QIcon(icon))
            button.setIconSize(QSize(20, 20))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: {radius}px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
            QPushButton:pressed {{
                background-color: {color}AA;
            }}
        """)
        return button

    @staticmethod
    def create_label(text: str, is_title: bool = False, config: Optional[Config] = None):
        """Create a styled label"""
        label = QLabel(text)
        if is_title:
            label.setFont(QFont(config.FONT_FAMILY if config else "Arial", 16, QFont.Bold))
        else:
            label.setFont(QFont(config.FONT_FAMILY if config else "Arial", 10))
        return label

    @staticmethod
    def create_status_indicator(state, config: Optional[Config] = None):
        """Create a colored status indicator based on state"""
        indicator = QLabel()
        indicator.setFixedSize(12, 12)
        if config:
            if state.value == "active":
                color = config.SECONDARY_COLOR
            elif state.value == "processing":
                color = config.PRIMARY_COLOR
            else:
                color = config.INACTIVE_COLOR
        else:
            if getattr(state, 'value', 'inactive') == "active":
                color = "#34C759"
            elif getattr(state, 'value', 'inactive') == "processing":
                color = "#007AFF"
            else:
                color = "#8E8E93"
        indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)
        return indicator

    @staticmethod
    def create_log_viewer(config: Optional[Config] = None):
        """Create a styled log viewer component"""
        log_viewer = QTextEdit()
        log_viewer.setReadOnly(True)
        if config:
            font = QFont(config.FONT_FAMILY, 9)
            radius = config.BORDER_RADIUS
        else:
            font = QFont("Consolas", 9)
            radius = 10
        log_viewer.setFont(font)
        log_viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: #FFFFFF;
                border-radius: {radius}px;
                padding: 10px;
                border: 1px solid #E5E5EA;
            }}
        """)
        return log_viewer
