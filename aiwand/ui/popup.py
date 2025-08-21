import logging
from typing import Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aiwand.config import Config
from aiwand.ui.widgets import RoundedWidget


class AIWandPopup(QWidget):
    """Enhanced popup widget with Apple-style design and animations"""

    def __init__(self, config: Config, aiwand=None):
        super().__init__()
        self.config = config
        self.aiwand = aiwand
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._setup_ui()
        self._setup_auto_hide_timer()
        self._setup_animation()

    def _setup_ui(self):
        """Initialize the UI components with modern styling"""
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.inner_widget = RoundedWidget(
            self,
            radius=self.config.BORDER_RADIUS,
            bg_color=self.config.CARD_BACKGROUND,
            border_color="#D1D1D6",
            shadow=True,
        )
        self.inner_widget.setAutoFillBackground(True)
        palette = self.inner_widget.palette()
        palette.setColor(QPalette.Background, QColor(self.config.CARD_BACKGROUND))
        self.inner_widget.setPalette(palette)

        inner_layout = QVBoxLayout(self.inner_widget)
        inner_layout.setContentsMargins(15, 12, 15, 12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)

        self.title_label = QLabel("AI Wand")
        header_layout.addWidget(self.title_label)

        self.speaker_icon = QPushButton("🔊")
        self.speaker_icon.setFixedSize(24, 24)
        self.speaker_icon.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.SECONDARY_COLOR};
                color: white;
                border-radius: 12px;
                border: none;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {self.config.SECONDARY_COLOR}DD;
            }}
        """)
        self.speaker_icon.setVisible(False)
        header_layout.addWidget(self.speaker_icon)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {self.config.SECONDARY_COLOR}; font-weight: bold;")
        self.status_label.setVisible(False)
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setFont(QFont(self.config.FONT_FAMILY, 14))
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.INACTIVE_COLOR}22;
                color: {self.config.INACTIVE_COLOR};
                border-radius: 10px;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.ERROR_COLOR}22;
                color: {self.config.ERROR_COLOR};
            }}
        """)
        close_button.clicked.connect(lambda: self.hide(immediate=True))
        header_layout.addWidget(close_button)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setFont(QFont(self.config.FONT_FAMILY, self.config.FONT_SIZE))
        self.label.setStyleSheet("""
            background-color: transparent;
            color: #000000;
            padding: 4px;
            line-height: 135%;
        """)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setTextFormat(Qt.RichText)

        self.limit_warning = QLabel()
        self.limit_warning.setStyleSheet("color: #FF3B30; font-size: 10pt;")
        self.limit_warning.setAlignment(Qt.AlignCenter)
        self.limit_warning.setVisible(False)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.label)
        content_layout.addWidget(self.limit_warning)

        self.config.POPUP_WIDTH = 450
        self.content_widget.setMinimumWidth(self.config.POPUP_WIDTH - 30)
        self.content_widget.setMaximumWidth(self.config.POPUP_WIDTH - 30)
        self.content_widget.setStyleSheet("background-color: transparent;")

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #EEEEEE;
                width: 5px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        scroll_area.setMaximumHeight(350)

        inner_layout.addLayout(header_layout)
        inner_layout.addWidget(scroll_area)

        main_layout.addWidget(self.inner_widget)
        self.setLayout(main_layout)

    def _setup_auto_hide_timer(self):
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

    def _setup_animation(self):
        self._opacity = 0.0
        self.fade_timer = QTimer()
        self.fade_timer.setInterval(16)
        self.fading_in = True
        self.fade_progress = 0.0
        self.fade_step = 0.08
        self.fade_timer.timeout.connect(self._update_fade)

    def _update_fade(self):
        if self.fading_in:
            self.fade_progress += self.fade_step
            if self.fade_progress >= 1.0:
                self.fade_progress = 1.0
                self.fade_timer.stop()
        else:
            self.fade_progress -= self.fade_step
            if self.fade_progress <= 0.0:
                self.fade_progress = 0.0
                self.fade_timer.stop()
                super().hide()
                return
        self.setWindowOpacity(self.fade_progress)

    def show_definition(self, text: str, x: int, y: int):
        try:
            self.speaker_icon.setVisible(False)
            self.status_label.setVisible(False)
            self.limit_warning.setVisible(False)
            self.title_label.setText("AI Wand")

            is_error = (
                text.startswith("No text") or text.startswith("Error") or text.startswith("Failed")
            )
            is_processing = text == "Getting definition..."

            if is_error:
                self.label.setStyleSheet(f"""
                    color: {self.config.ERROR_COLOR};
                    background-color: transparent;
                    padding: 4px;
                    line-height: 135%;
                """)
            elif is_processing:
                self.label.setStyleSheet(f"""
                    color: {self.config.PRIMARY_COLOR};
                    background-color: transparent;
                    padding: 4px;
                    line-height: 135%;
                """)
            else:
                self.label.setStyleSheet("""
                    color: #000000;
                    background-color: transparent;
                    padding: 4px;
                    line-height: 135%;
                """)

            self.label.setText(text)

            text_length = len(text)
            line_count = text.count('\n') + 1
            estimated_height = min(max(line_count * 20 + 60, 150), 350)
            if text_length > 500 and estimated_height < 300:
                estimated_height = 300
            elif text_length > 200 and estimated_height < 200:
                estimated_height = 200

            self.resize(self.config.POPUP_WIDTH, estimated_height)

            screen = QtWidgets.QApplication.primaryScreen()
            screen_geometry = (
                screen.availableGeometry() if screen is not None else QtCore.QRect(0, 0, 1920, 1080)
            )
            popup_width = self.width()
            popup_height = self.height()
            popup_x = min(x + 10, screen_geometry.width() - popup_width - 10)
            popup_x = max(popup_x, 10)
            if y + popup_height + 10 > screen_geometry.height():
                popup_y = max(y - popup_height - 10, 10)
            else:
                popup_y = y + 10

            self.move(popup_x, popup_y)
            self.setFocus(Qt.OtherFocusReason)
            self.setFocusPolicy(Qt.StrongFocus)
            self.setWindowOpacity(0.0)
            super().show()
            self.raise_()
            self.activateWindow()
            self.fading_in = True
            self.fade_progress = 0.0
            self.fade_timer.start()

            if is_error:
                self.auto_hide_timer.start(5000)
        except Exception as e:
            self.logger.error(f"Error showing popup: {e}")

    def show_speech(
        self,
        text: str,
        is_speaking: bool,
        original_text: Optional[str] = None,
        text_limit: Optional[int] = None,
    ) -> None:
        try:
            self.title_label.setText("AI Wand")
            self.speaker_icon.setVisible(True)
            self.status_label.setVisible(True)
            self.status_label.setText("Speak")
            self.label.setText(text)
            self.label.setStyleSheet("""
                color: #000000;
                background-color: transparent;
                padding: 4px;
                line-height: 135%;
            """)
            if original_text:
                self.speaker_icon.setProperty("original_text", original_text)
            if text_limit and original_text and len(original_text) > text_limit:
                self.limit_warning.setText(
                    f"Text exceeds {text_limit} character limit and has been truncated"
                )
                self.limit_warning.setVisible(True)
            else:
                self.limit_warning.setVisible(False)

            if not self.isVisible():
                text_length = len(text)
                line_count = text.count('\n') + 1
                estimated_height = min(max(line_count * 20 + 60, 150), 350)
                if text_length > 500:
                    estimated_height = 350
                elif text_length > 200:
                    estimated_height = 250
                self.resize(self.config.POPUP_WIDTH, estimated_height)
                screen = QtWidgets.QApplication.primaryScreen()
                screen_geometry = (
                    screen.availableGeometry() if screen is not None else QtCore.QRect(0, 0, 1920, 1080)
                )
                popup_width = self.width()
                popup_height = self.height()
                popup_x = screen_geometry.width() // 2 - popup_width // 2
                popup_x = min(popup_x, screen_geometry.width() - popup_width - 10)
                popup_x = max(popup_x, 10)
                popup_y = screen_geometry.height() // 2 - popup_height // 2
                popup_y = min(popup_y, screen_geometry.height() - popup_height - 10)
                popup_y = max(popup_y, 10)
                self.move(popup_x, popup_y)
                self.setWindowOpacity(0.0)
                super().show()
                self.raise_()
                self.activateWindow()
                self.fading_in = True
                self.fade_progress = 0.0
                self.fade_timer.start()
            else:
                self.update()
        except Exception as e:
            self.logger.error(f"Error showing speech popup: {e}")

    @QtCore.pyqtSlot(bool)
    def update_speech_status(self, is_speaking: bool) -> None:
        self.status_label.setText("Speak")
        self.update()

    def hide(self, immediate: bool = False) -> None:
        self.auto_hide_timer.stop()
        if self.aiwand and hasattr(self.aiwand, 'text_to_speech'):
            try:
                self.aiwand.text_to_speech.stop()
            except Exception as e:
                self.logger.error(f"Error stopping speech: {e}")
        if immediate:
            self.fade_timer.stop()
            super().hide()
        else:
            self.fading_in = False
            self.fade_timer.start()

    def mousePressEvent(self, event):
        event.accept()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide(immediate=True)
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Ensure speech stops immediately when the popup is closed
        try:
            self.hide(immediate=True)
        except Exception:
            pass
        event.accept()
