import logging
from typing import Callable, Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aiwand.agents import TranslateAgent
from aiwand.config import Config
from aiwand.ui.widgets import RoundedWidget


class GlobalEventFilter(QtCore.QObject):
    """Global event filter to prevent toolbar closing when dropdown is active"""

    def eventFilter(self, obj, event):
        if AIToolbar.dropdown_active and event.type() in [
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.MouseButtonDblClick,
        ]:
            pass
        return False


class SingleClickComboBox(QtWidgets.QComboBox):
    """Custom QComboBox that opens on single click"""

    def __init__(self, parent=None):
        super().__init__(parent)
        view = self.view()
        if view is not None:
            view.installEventFilter(self)
        self.popup_active = False
        self.parent_toolbar = parent
        if view is not None:
            vp = view.viewport()
            if vp is not None:
                vp.installEventFilter(self)
            view.setMouseTracking(True)

    def showPopup(self):
        self.popup_active = True
        if isinstance(self.parent(), AIToolbar):
            AIToolbar.dropdown_active = True
        super().showPopup()

    def hidePopup(self):
        self.popup_active = False
        if isinstance(self.parent(), AIToolbar):
            parent = self.parent()
            other_active = False
            for combo_attr in ['style_combo', 'source_lang_combo', 'target_lang_combo']:
                if hasattr(parent, combo_attr):
                    combo = getattr(parent, combo_attr)
                    if combo != self and hasattr(combo, 'popup_active') and combo.popup_active:
                        other_active = True
                        break
            if not other_active:
                AIToolbar.dropdown_active = False
        super().hidePopup()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.showPopup()
        else:
            super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.view():
            if event.type() in [
                QtCore.QEvent.MouseButtonPress,
                QtCore.QEvent.MouseButtonRelease,
                QtCore.QEvent.MouseButtonDblClick,
            ]:
                event.accept()
        return super().eventFilter(obj, event)


class AIToolbar(QWidget):
    """Apple-style toolbar with multiple AI features that stays open when dropdown is used"""

    dropdown_active = False

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.selected_text = ""
        self._setup_ui()
        self._setup_animation()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        # Callback hooks set by app_main
        self.define_signal: Optional[Callable[[str], None]] = None
        self.rewrite_signal: Optional[Callable[[str, str], None]] = None
        self.summarize_signal: Optional[Callable[[str], None]] = None
        self.translate_signal: Optional[Callable[[str, str, str], None]] = None
        self.speak_signal: Optional[Callable[[str], None]] = None
        self.settings_signal: Optional[Callable[[], None]] = None
        self.customize_signal: Optional[Callable[[], None]] = None

    def _setup_ui(self):
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

        inner_layout = QVBoxLayout(self.inner_widget)
        inner_layout.setContentsMargins(15, 12, 15, 12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)

        title_label = QLabel("AI Wand")
        title_label.setFont(QFont(self.config.FONT_FAMILY, 12, QFont.Bold))

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
        close_button.clicked.connect(self.hide)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)

        features_layout = QVBoxLayout()
        features_layout.setSpacing(10)

        define_button = self._create_feature_button(
            "Define Text",
            "Get an AI-powered definition of the selected text",
            self._on_define_clicked,
        )
        define_button.setMinimumHeight(50)

        rewrite_layout = QHBoxLayout()
        rewrite_button = self._create_feature_button(
            "Rewrite Text",
            "Rewrite selected text in a different style",
            self._on_rewrite_clicked,
        )
        rewrite_button.setMinimumHeight(50)

        self.style_combo = SingleClickComboBox(self)
        self.style_combo.addItems(
            ["Simple", "Technical", "Professional", "Formal", "Normal", "Common", "Grammar Fix"]
        )
        self.style_combo.setMinimumHeight(45)
        self.style_combo.setStyleSheet(f"""
            QComboBox {{
                border-radius: {self.config.BORDER_RADIUS}px;
                padding: 5px 10px;
                background-color: {self.config.BACKGROUND_COLOR};
                border: 1px solid #E5E5EA;
                font-size: 11pt;
            }}
            QComboBox:hover {{
                border: 1px solid {self.config.PRIMARY_COLOR};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right;
                width: 25px;
                border-left: 1px solid #E5E5EA;
            }}
        """)
        self.style_combo.installEventFilter(self)
        self.style_combo.setFocusPolicy(Qt.StrongFocus)
        self.style_combo.activated.connect(self._on_style_selected)

        rewrite_layout.addWidget(rewrite_button, 3)
        rewrite_layout.addWidget(self.style_combo, 1)

        summarize_button = self._create_feature_button(
            "Summarize Text",
            "Create a concise summary that covers all key points",
            self._on_summarize_clicked,
        )
        summarize_button.setMinimumHeight(50)

        translate_layout = QHBoxLayout()
        translate_button = self._create_feature_button(
            "Translate Text",
            "Translate text to another language",
            self._on_translate_clicked,
        )
        translate_button.setMinimumHeight(50)

        self.source_lang_combo = SingleClickComboBox(self)
        self.source_lang_combo.addItem("Auto-detect")
        for lang in sorted(TranslateAgent.LANGUAGES.keys()):
            self.source_lang_combo.addItem(lang)
        self.source_lang_combo.setMinimumHeight(45)

        self.target_lang_combo = SingleClickComboBox(self)
        for lang in sorted(TranslateAgent.LANGUAGES.keys()):
            self.target_lang_combo.addItem(lang)
        self.target_lang_combo.setCurrentText("English")
        self.target_lang_combo.setMinimumHeight(45)

        self.source_lang_combo.activated.connect(self._on_language_selected)
        self.target_lang_combo.activated.connect(self._on_language_selected)

        for combo in [self.source_lang_combo, self.target_lang_combo]:
            combo.setStyleSheet(f"""
                QComboBox {{
                    border-radius: {self.config.BORDER_RADIUS}px;
                    padding: 5px 10px;
                    background-color: {self.config.BACKGROUND_COLOR};
                    border: 1px solid #E5E5EA;
                    font-size: 11pt;
                }}
                QComboBox:hover {{
                    border: 1px solid {self.config.PRIMARY_COLOR};
                }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: right;
                    width: 25px;
                    border-left: 1px solid #E5E5EA;
                }}
            """)

        translate_lang_layout = QHBoxLayout()
        translate_lang_layout.addWidget(QLabel("From:"))
        translate_lang_layout.addWidget(self.source_lang_combo)
        translate_lang_layout.addWidget(QLabel("To:"))
        translate_lang_layout.addWidget(self.target_lang_combo)

        translate_layout.addWidget(translate_button, 1)

        speak_button = self._create_feature_button(
            "Speak Text",
            "Read the selected text aloud using text-to-speech",
            self._on_speak_clicked,
        )
        speak_button.setMinimumHeight(50)

        features_layout.addWidget(define_button)
        features_layout.addLayout(rewrite_layout)
        features_layout.addWidget(summarize_button)
        features_layout.addLayout(translate_layout)
        features_layout.addLayout(translate_lang_layout)
        features_layout.addWidget(speak_button)

        inner_layout.addLayout(header_layout)
        inner_layout.addLayout(features_layout)

        main_layout.addWidget(self.inner_widget)
        self.setLayout(main_layout)
        self.setFixedWidth(350)

    def _create_feature_button(self, text, tooltip, callback):
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 12px 15px;
                background-color: {self.config.BACKGROUND_COLOR};
                border: 1px solid #E5E5EA;
                border-radius: {self.config.BORDER_RADIUS}px;
                color: #000000;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.PRIMARY_COLOR}22;
                border: 1px solid {self.config.PRIMARY_COLOR};
            }}
            QPushButton:pressed {{
                background-color: {self.config.PRIMARY_COLOR}44;
            }}
        """)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def _setup_animation(self):
        # Create fade in/out animations using a timer instead of opacity effect
        self.fade_timer = QTimer()
        self.fade_timer.setInterval(16)  # ~60fps
        # Store fade direction and progress
        self.fading_in = True
        self.fade_progress = 0.0
        self.fade_step = 0.08  # Controls fade speed
        # Connect timer to update method
        self.fade_timer.timeout.connect(self._update_fade)

    def _update_fade(self):
        """Update the fade animation"""
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
        # Apply the opacity
        self.setWindowOpacity(self.fade_progress)

    def eventFilter(self, obj, event):
        if event.type() in [
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.MouseButtonDblClick,
        ]:
            if AIToolbar.dropdown_active:
                return False
        return super().eventFilter(obj, event)

    def _on_define_clicked(self):
        if self.define_signal:
            self.define_signal(self.selected_text)
        self.hide()

    def _on_rewrite_clicked(self):
        if self.rewrite_signal:
            style = self.style_combo.currentText()
            self.rewrite_signal(self.selected_text, style)
        self.hide()

    def _on_summarize_clicked(self):
        if self.summarize_signal:
            self.summarize_signal(self.selected_text)
        self.hide()

    def _on_translate_clicked(self):
        if self.translate_signal:
            source = self.source_lang_combo.currentText()
            target = self.target_lang_combo.currentText()
            self.translate_signal(self.selected_text, source, target)
        self.hide()

    def _on_speak_clicked(self):
        if self.speak_signal:
            self.speak_signal(self.selected_text)
        self.hide()

    def _on_style_selected(self, index):
        pass

    def _on_language_selected(self, index):
        pass

    def show_toolbar(self, text: str, x: int, y: int):
        try:
            # Store the selected text
            self.selected_text = text

            # Position toolbar intelligently (match legacy)
            screen = QtWidgets.QApplication.primaryScreen()
            screen_geometry = (
                screen.availableGeometry() if screen is not None else QtCore.QRect(0, 0, 1920, 1080)
            )
            toolbar_width = self.sizeHint().width()
            toolbar_height = self.sizeHint().height()

            toolbar_x = min(x + 10, screen_geometry.width() - toolbar_width - 10)
            toolbar_x = max(toolbar_x, 10)

            if y + toolbar_height + 10 > screen_geometry.height():
                toolbar_y = max(y - toolbar_height - 10, 10)
            else:
                toolbar_y = y + 10

            self.move(toolbar_x, toolbar_y)

            # Ensure proper focus and initial opacity for fade-in
            self.setFocus(Qt.OtherFocusReason)
            self.setFocusPolicy(Qt.StrongFocus)
            self.setWindowOpacity(0.0)

            # Show with fade-in animation
            super().show()
            self.raise_()
            self.activateWindow()

            self.fading_in = True
            self.fade_progress = 0.0
            self.fade_timer.start()
        except Exception as e:
            self.logger.error(f"Error showing toolbar: {e}")

    def hide(self):
        try:
            # Start fade out animation (match legacy)
            self.fading_in = False
            self.fade_timer.start()
        except Exception as e:
            self.logger.error(f"Error hiding toolbar: {e}")
