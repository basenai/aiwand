import logging
import os
import sys

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtWidgets import QMainWindow as _QMainWindow

from aiwand.app_state import AppState
from aiwand.config import Config
from aiwand.ui.components import UIComponents

# Aliases for Qt classes (to mirror main.py style)
QApplication = QtWidgets.QApplication
QWidget = QtWidgets.QWidget
QLabel = QtWidgets.QLabel
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QPushButton = QtWidgets.QPushButton
QTextEdit = QtWidgets.QTextEdit
QMainWindow = QtWidgets.QMainWindow
QTabWidget = QtWidgets.QTabWidget
QScrollArea = QtWidgets.QScrollArea
QSystemTrayIcon = QtWidgets.QSystemTrayIcon
QMenu = QtWidgets.QMenu
QAction = QtWidgets.QAction

Qt = QtCore.Qt
QTimer = QtCore.QTimer

QFont = QtGui.QFont
QIcon = QtGui.QIcon
QColor = QtGui.QColor
QPalette = QtGui.QPalette
QPixmap = QtGui.QPixmap


class MainWindow(_QMainWindow):
    CONFIG_FILE = "settings.json"
    """Main application window with modern Apple-style UI"""

    def __init__(self, config: Config, aiwand_instance=None):
        # Determine config path based on execution environment
        if aiwand_instance is not None and hasattr(aiwand_instance, 'config_path'):
            self.config_path = aiwand_instance.config_path
        else:
            if getattr(sys, 'frozen', False):
                bundle_dir = os.path.dirname(sys.executable)
                self.config_path = os.path.join(bundle_dir, self.CONFIG_FILE)
            else:
                self.config_path = self.CONFIG_FILE

        super().__init__()
        self.config = config
        self.aiwand = aiwand_instance
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Store color settings
        self.selected_color_primary = self.config.PRIMARY_COLOR
        self.selected_color_secondary = self.config.SECONDARY_COLOR
        self.selected_color_background = self.config.BACKGROUND_COLOR
        self.selected_color_card = self.config.CARD_BACKGROUND

        self._setup_ui()
        self._setup_system_tray()
        self._setup_connections()

        # Initial state
        self.update_status_indicator(AppState.INACTIVE)

    def _setup_ui(self):
        """Initialize the UI components with a clean, minimalistic design"""
        # Main window setup
        self.setWindowTitle(self.config.WINDOW_TITLE)
        self.setMinimumSize(self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.config.BACKGROUND_COLOR};
            }}
            QLabel {{
                color: #333333;
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
            }}
            QPushButton {{
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
                padding: 8px 16px;
                border-radius: {self.config.BORDER_RADIUS}px;
            }}
            QTabWidget {{
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
            }}
        """)

        # Set application icon
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

        # Central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            self.config.PADDING, self.config.PADDING, self.config.PADDING, self.config.PADDING
        )
        main_layout.setSpacing(self.config.PADDING)

        # Header with logo and status - simplified
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            background-color: {self.config.CARD_BACKGROUND};
            border-radius: {self.config.BORDER_RADIUS}px;
            padding: 10px;
        """)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)

        # Logo and title with better styling
        title_label = QLabel("AI Wand")
        title_label.setFont(QFont(self.config.FONT_FAMILY, 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")

        # Status indicator with improved visibility
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet(f"""
            background-color: {self.config.INACTIVE_COLOR};
            border-radius: 6px;
        """)

        self.status_label = QLabel("Inactive")
        self.status_label.setFont(QFont(self.config.FONT_FAMILY, self.config.FONT_SIZE))
        self.status_label.setStyleSheet("color: #333333; font-weight: bold;")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # Activation button with better contrast
        self.activate_button = QPushButton("Activate")
        self.activate_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.activate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.PRIMARY_COLOR};
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {self.config.PRIMARY_COLOR}DD;
            }}
            QPushButton:pressed {{
                background-color: {self.config.PRIMARY_COLOR}AA;
            }}
        """)
        self.activate_button.clicked.connect(self._toggle_activation)

        # Add to header layout
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(status_layout)
        header_layout.addWidget(self.activate_button)

        # Tab widget with improved styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.config.CARD_BACKGROUND};
                border-radius: {self.config.BORDER_RADIUS}px;
            }}
            QTabBar::tab {{
                background-color: {self.config.INACTIVE_COLOR}22;
                color: #333333;
                border-top-left-radius: {self.config.BORDER_RADIUS}px;
                border-top-right-radius: {self.config.BORDER_RADIUS}px;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: normal;
            }}
            QTabBar::tab:selected {{
                background-color: {self.config.PRIMARY_COLOR};
                color: white;
                font-weight: bold;
            }}
        """)

        # Dashboard tab - simplified
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        dashboard_layout.setSpacing(20)

        # Instructions card - simplified
        instructions_widget = QWidget()
        instructions_widget.setStyleSheet(f"""
            background-color: {self.config.CARD_BACKGROUND};
            border-radius: {self.config.BORDER_RADIUS}px;
            padding: 10px;
        """)

        instructions_layout = QVBoxLayout(instructions_widget)
        instructions_layout.setContentsMargins(15, 15, 15, 15)

        instructions_title = QLabel("How to Use")
        instructions_title.setFont(QFont(self.config.FONT_FAMILY, 12, QFont.Bold))
        instructions_title.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")

        instructions_text = QLabel(
            "<ol style='margin-left: 15px; line-height: 150%;'>"
            "<li>Activate AI Wand using the button above or press <b>Ctrl+Shift+A</b></li>"
            "<li>Select any text in any application</li>"
            "<li>Press <b>Right-Ctrl twice</b> to access AI features</li>"
            "<li>Choose an action: Define text, Rewrite text in different styles, Summarize text, Translate text to different languages, or Speak text aloud</li>"
            "</ol>"
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("font-size: 11pt;")

        instructions_layout.addWidget(instructions_title)
        instructions_layout.addWidget(instructions_text)

        # Shortcuts card - simplified
        shortcuts_widget = QWidget()
        shortcuts_widget.setStyleSheet(f"""
            background-color: {self.config.CARD_BACKGROUND};
            border-radius: {self.config.BORDER_RADIUS}px;
            padding: 10px;
        """)

        shortcuts_layout = QVBoxLayout(shortcuts_widget)
        shortcuts_layout.setContentsMargins(15, 15, 15, 15)

        shortcuts_title = QLabel("Keyboard Shortcuts")
        shortcuts_title.setFont(QFont(self.config.FONT_FAMILY, 12, QFont.Bold))
        shortcuts_title.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")

        shortcuts_table = QLabel(
            "<table style='width:100%; border-spacing: 10px; line-height: 150%;'>"
            "<tr><td style='padding-right:20px'><b>Ctrl+Shift+A</b></td><td>Toggle activation</td></tr>"
            "<tr><td style='padding-right:20px'><b>Right-Ctrl twice</b></td><td>Open AI features toolbar</td></tr>"
            "<tr><td style='padding-right:20px'><b>ESC</b></td><td>Dismiss popup/toolbar</td></tr>"
            "</table>"
        )
        shortcuts_table.setStyleSheet("font-size: 11pt;")

        shortcuts_layout.addWidget(shortcuts_title)
        shortcuts_layout.addWidget(shortcuts_table)

        # Add cards to dashboard
        dashboard_layout.addWidget(instructions_widget)
        dashboard_layout.addWidget(shortcuts_widget)
        dashboard_layout.addStretch()

        # Logs tab - simplified
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        logs_layout.setContentsMargins(20, 20, 20, 20)
        logs_layout.setSpacing(10)

        # Log viewer with better styling
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        self.log_viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.config.CARD_BACKGROUND};
                border-radius: {self.config.BORDER_RADIUS}px;
                padding: 10px;
                border: 1px solid #E5E5EA;
            }}
        """)
        self.log_viewer.setHtml("<p style='color:#666666;'>Log output will appear here...</p>")

        # Log controls
        log_controls_layout = QHBoxLayout()
        clear_logs_button = QPushButton("Clear Logs")
        clear_logs_button.setCursor(QtCore.Qt.PointingHandCursor)
        clear_logs_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.INACTIVE_COLOR};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: {self.config.BORDER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: {self.config.INACTIVE_COLOR}DD;
            }}
        """)
        clear_logs_button.clicked.connect(self._clear_logs)

        log_controls_layout.addStretch()
        log_controls_layout.addWidget(clear_logs_button)

        logs_layout.addWidget(self.log_viewer)
        logs_layout.addLayout(log_controls_layout)

        # LLM Settings tab
        settings_widget = self._create_llm_settings_tab()

        # UI Customization tab
        ui_customization_widget = self._create_ui_customization_tab()

        # Add tabs
        self.tab_widget.addTab(dashboard_widget, "Dashboard")
        self.tab_widget.addTab(logs_widget, "Logs")
        self.tab_widget.addTab(settings_widget, "LLM Settings")
        self.tab_widget.addTab(ui_customization_widget, "UI Customization")

        # Add widgets to main layout
        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.tab_widget)

        self.setCentralWidget(central_widget)

    def _create_llm_settings_tab(self):
        """Create the LLM Settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create content card with shadow
        content_card = QWidget()
        UIComponents.create_rounded_widget(
            content_card, self.config.BORDER_RADIUS, self.config.CARD_BACKGROUND
        )
        card_layout = QVBoxLayout(content_card)

        # Form layout for settings
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Title
        title_label = UIComponents.create_label("LLM Settings", True, self.config)
        card_layout.addWidget(title_label)

        # API Key
        self.api_key_input = QtWidgets.QLineEdit(self.config.API_KEY)
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your API key")
        self.api_key_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Show/Hide button for API key
        api_key_layout = QHBoxLayout()
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(8)
        api_key_layout.addWidget(self.api_key_input)
        show_button = QPushButton("Show")
        show_button.setCheckable(True)
        show_button.setFixedWidth(70)
        show_button.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        show_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F0F0F0;
                color: #333;
                border: 1px solid #CFCFCF;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
            QPushButton:pressed { background-color: #E0E0E0; }
            """
        )
        show_button.toggled.connect(lambda checked: self._toggle_api_key_visibility(checked))
        api_key_layout.addWidget(show_button)
        api_key_layout.setStretch(0, 1)  # Line edit grows, button stays visible
        form_layout.addRow("API Key:", api_key_layout)

        # Base URL
        self.base_url_input = QtWidgets.QLineEdit(self.config.BASE_URL)
        self.base_url_input.setPlaceholderText("https://api.example.com/v1")
        form_layout.addRow("Base URL:", self.base_url_input)

        # Model Name
        self.model_name_input = QtWidgets.QLineEdit(self.config.MODEL_NAME)
        self.model_name_input.setPlaceholderText("model-name")
        form_layout.addRow("Model Name:", self.model_name_input)

        # Max Definition Length
        self.max_def_length = QtWidgets.QSpinBox()
        self.max_def_length.setMinimum(10)
        self.max_def_length.setMaximum(150)
        self.max_def_length.setValue(self.config.MAX_DEFINITION_LENGTH)
        self.max_def_length.setSingleStep(10)
        self.max_def_length.setStyleSheet(
            f"""
            QSpinBox {{
                min-height: 28px;
                padding-right: 26px; /* space for buttons */
                background-color: {self.config.CARD_BACKGROUND};
                border: 1px solid #CFCFCF;
                border-radius: 6px;
            }}
            QSpinBox:focus {{
                border: 1px solid {self.config.SECONDARY_COLOR};
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 20px;
                background: #F0F0F0;
                border-left: 1px solid #CFCFCF;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                width: 20px;
                background: #F0F0F6;
                border-left: 1px solid #CFCFCF;
            }}
            QSpinBox::up-button {{
                border-top-right-radius: 6px;
            }}
            QSpinBox::down-button {{
                border-bottom-right-radius: 6px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: #E8E8E8;
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                width: 10px; height: 10px;
            }}
            """
        )
        form_layout.addRow("Max Definition Length (10-150):", self.max_def_length)

        # Add note about settings
        note_label = QLabel("Changes will take effect after saving.")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #777;")

        # Save button
        save_button = UIComponents.create_button("Save Settings", primary=True, config=self.config)
        save_button.clicked.connect(self._save_llm_settings)

        # Add to layout
        card_layout.addLayout(form_layout)
        card_layout.addSpacing(20)
        card_layout.addWidget(note_label)
        card_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        card_layout.addLayout(button_layout)

        # Add content card to tab layout
        layout.addWidget(content_card)

        return tab

    def _create_ui_customization_tab(self):
        """Create the UI Customization tab with a cleaner design"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create content card with clean design
        content_card = QWidget()
        content_card.setStyleSheet(f"""
            background-color: {self.config.CARD_BACKGROUND};
            border-radius: {self.config.BORDER_RADIUS}px;
            padding: 15px;
        """)
        card_layout = QVBoxLayout(content_card)
        card_layout.setSpacing(20)

        # Title
        title_label = QLabel("UI Customization")
        title_label.setFont(QFont(self.config.FONT_FAMILY, 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")
        card_layout.addWidget(title_label)

        # Quick themes with better styling
        themes_group = QtWidgets.QGroupBox("Theme Selection")
        themes_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.config.PRIMARY_COLOR};
            }}
        """)

        themes_layout = QHBoxLayout(themes_group)
        themes_layout.setContentsMargins(15, 20, 15, 15)

        light_theme = QPushButton("Light Theme")
        light_theme.setCursor(QtCore.Qt.PointingHandCursor)
        light_theme.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F5F7;
                color: #333333;
                border: 1px solid #E0E0E0;
                padding: 10px 20px;
                border-radius: {self.config.BORDER_RADIUS}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #EEEEEE;
                border: 1px solid #CCCCCC;
            }}
        """)
        light_theme.clicked.connect(lambda: self._apply_theme("light"))

        dark_theme = QPushButton("Dark Theme")
        dark_theme.setCursor(QtCore.Qt.PointingHandCursor)
        dark_theme.setStyleSheet(f"""
            QPushButton {{
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
                padding: 10px 20px;
                border-radius: {self.config.BORDER_RADIUS}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #444444;
                border: 1px solid #666666;
            }}
        """)
        dark_theme.clicked.connect(lambda: self._apply_theme("dark"))

        themes_layout.addWidget(light_theme)
        themes_layout.addWidget(dark_theme)
        card_layout.addWidget(themes_group)

        # Color scheme section with better styling
        colors_group = QtWidgets.QGroupBox("Color Scheme")
        colors_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.config.PRIMARY_COLOR};
            }}
        """)

        colors_layout = QtWidgets.QFormLayout(colors_group)
        colors_layout.setSpacing(15)
        colors_layout.setContentsMargins(15, 20, 15, 15)
        colors_layout.setLabelAlignment(Qt.AlignRight)

        # Primary color
        self.primary_button = self._create_color_button(self.config.PRIMARY_COLOR)
        colors_layout.addRow("Primary Color:", self.primary_button)

        # Secondary color
        self.secondary_button = self._create_color_button(self.config.SECONDARY_COLOR)
        colors_layout.addRow("Secondary Color:", self.secondary_button)

        # Background color
        self.background_button = self._create_color_button(self.config.BACKGROUND_COLOR)
        colors_layout.addRow("Background Color:", self.background_button)

        # Card background
        self.card_button = self._create_color_button(self.config.CARD_BACKGROUND)
        colors_layout.addRow("Card Background:", self.card_button)

        card_layout.addWidget(colors_group)

        # Font settings with better styling
        font_group = QtWidgets.QGroupBox("Font Settings")
        font_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.config.PRIMARY_COLOR};
            }}
        """)

        font_layout = QtWidgets.QFormLayout(font_group)
        font_layout.setSpacing(15)
        font_layout.setContentsMargins(15, 20, 15, 15)

        # Font family with better styling
        self.font_family = QtWidgets.QFontComboBox()
        self.font_family.setCurrentFont(QFont(self.config.FONT_FAMILY))
        self.font_family.setStyleSheet(f"""
            QFontComboBox {{
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                min-height: 30px;
            }}
        """)
        font_layout.addRow("Font Family:", self.font_family)

        # Font size with better styling
        self.font_size = QtWidgets.QSpinBox()
        self.font_size.setRange(8, 16)
        self.font_size.setValue(self.config.FONT_SIZE)
        self.font_size.setStyleSheet(f"""
            QSpinBox {{
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                min-height: 30px;
                min-width: 60px;
            }}
        """)
        font_layout.addRow("Font Size:", self.font_size)

        card_layout.addWidget(font_group)

        # Preview section with better styling
        preview_group = QtWidgets.QGroupBox("Preview")
        preview_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: {self.config.BORDER_RADIUS}px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.config.PRIMARY_COLOR};
            }}
        """)

        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(15, 20, 15, 15)

        self.preview_widget = QWidget()
        self.preview_widget.setMinimumHeight(120)
        self.update_preview()

        preview_layout.addWidget(self.preview_widget)
        card_layout.addWidget(preview_group)

        # Note about changes
        note_label = QLabel("Changes will be applied immediately. Click Apply to see your changes.")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #777; margin-top: 10px;")
        card_layout.addWidget(note_label)

        # Buttons with better styling
        button_layout = QHBoxLayout()

        apply_button = QPushButton("Apply Changes")
        apply_button.setCursor(QtCore.Qt.PointingHandCursor)
        apply_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: {self.config.BORDER_RADIUS}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.SECONDARY_COLOR}DD;
            }}
        """)
        apply_button.clicked.connect(self._apply_ui_changes)

        save_button = QPushButton("Save Settings")
        save_button.setCursor(QtCore.Qt.PointingHandCursor)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.PRIMARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: {self.config.BORDER_RADIUS}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.PRIMARY_COLOR}DD;
            }}
        """)
        save_button.clicked.connect(self._save_ui_settings)

        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(save_button)
        card_layout.addLayout(button_layout)

        # Add content card to tab layout
        layout.addWidget(content_card)

        return tab

    def _create_color_button(self, color):
        """Create a color picker button"""
        button = QPushButton()
        button.setFixedSize(80, 30)
        button.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
        button.clicked.connect(lambda: self._pick_color(button))
        return button

    def _pick_color(self, button):
        """Show color dialog and update button color"""
        current_color = button.palette().button().color()
        color = QtWidgets.QColorDialog.getColor(current_color, self)

        if color.isValid():
            color_hex = color.name()
            button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #ccc;")

            # Store selected color
            if button == self.primary_button:
                self.selected_color_primary = color_hex
            elif button == self.secondary_button:
                self.selected_color_secondary = color_hex
            elif button == self.background_button:
                self.selected_color_background = color_hex
            elif button == self.card_button:
                self.selected_color_card = color_hex

            self.update_preview()

    def _apply_theme(self, theme):
        """Apply a predefined theme"""
        if theme == "light":
            self.selected_color_primary = "#444444"  # Dark gray
            self.selected_color_secondary = "#4CAF50"  # Material green
            self.selected_color_background = "#F5F5F7"  # Light gray
            self.selected_color_card = "#FFFFFF"  # White
        elif theme == "dark":
            self.selected_color_primary = self.config.DARK_PRIMARY_COLOR
            self.selected_color_secondary = self.config.DARK_SECONDARY_COLOR
            self.selected_color_background = self.config.DARK_BACKGROUND_COLOR
            self.selected_color_card = self.config.DARK_CARD_BACKGROUND

        # Update button colors with better visibility
        self.primary_button.setStyleSheet(
            f"background-color: {self.selected_color_primary}; border: 1px solid #ccc; color: white;"
        )
        self.secondary_button.setStyleSheet(
            f"background-color: {self.selected_color_secondary}; border: 1px solid #ccc; color: white;"
        )
        self.background_button.setStyleSheet(
            f"background-color: {self.selected_color_background}; border: 1px solid #ccc; color: black;"
        )
        self.card_button.setStyleSheet(
            f"background-color: {self.selected_color_card}; border: 1px solid #ccc; color: black;"
        )

        # Apply theme immediately to the main window
        if self.aiwand:
            # Ensure running app uses updated config instance before reinit
            self.aiwand.config = self.config

            # Apply changes immediately
            self._apply_current_theme()

        self.update_preview()

    def update_preview(self):
        """Update the preview widget with selected colors"""
        # Create a new layout for the preview
        if self.preview_widget.layout():
            # Clear old layout
            QWidget().setLayout(self.preview_widget.layout())

        preview_layout = QVBoxLayout(self.preview_widget)

        # Set background color
        self.preview_widget.setStyleSheet(f"background-color: {self.selected_color_background};")

        # Create a card-like widget
        card = QWidget()
        card.setStyleSheet(f"""
            background-color: {self.selected_color_card};
            border-radius: 10px;
            padding: 10px;
        """)
        card_layout = QVBoxLayout(card)

        # Add some elements to the card
        title = QLabel("Preview Title")
        title.setFont(QFont(self.font_family.currentFont().family(), 12, QFont.Bold))
        title.setStyleSheet(f"color: {self.selected_color_primary};")

        button = QPushButton("Action Button")
        button.setStyleSheet(f"""
            background-color: {self.selected_color_primary};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
        """)

        status = QLabel("Status: Active")
        status.setStyleSheet(f"color: {self.selected_color_secondary};")

        card_layout.addWidget(title)
        card_layout.addWidget(status)
        card_layout.addWidget(button)

        preview_layout.addWidget(card)

    def _toggle_api_key_visibility(self, checked):
        """Toggle API key visibility"""
        if checked:
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Normal)
            sender_obj = self.sender()
            if isinstance(sender_obj, QtWidgets.QAbstractButton):
                sender_obj.setText("Hide")
        else:
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
            sender_obj = self.sender()
            if isinstance(sender_obj, QtWidgets.QAbstractButton):
                sender_obj.setText("Show")

    def _save_llm_settings(self):
        """Save LLM settings"""
        self.config.API_KEY = self.api_key_input.text()
        self.config.MODEL_NAME = self.model_name_input.text()
        self.config.BASE_URL = self.base_url_input.text()
        self.config.MAX_DEFINITION_LENGTH = self.max_def_length.value()
        save_path = self.aiwand.config_path if self.aiwand and hasattr(self.aiwand, 'config_path') else self.config_path
        self.config.save(save_path)
        self.logger.info(f"LLM settings saved to {save_path}")

        # Save API key to .env file for persistence across updates
        try:
            if getattr(sys, 'frozen', False):
                env_path = os.path.join(os.path.dirname(sys.executable), '.env')
            else:
                env_path = '.env'
            with open(env_path, 'w') as f:
                f.write(f"GEMINI_API_KEY={self.config.API_KEY}\n")
        except Exception as e:
            self.logger.error(f"Failed to save API key to .env file: {e}")

        if self.aiwand:
            # Ensure running app uses updated config instance before reinit
            self.aiwand.config = self.config
            self.aiwand._reinitialize_agents()

        QtWidgets.QMessageBox.information(self, "Success", "LLM settings saved successfully you might need to restart the application for changes to take effect!")

    def _save_ui_settings(self):
        """Save UI settings"""
        # Update color values
        self.config.PRIMARY_COLOR = self.selected_color_primary
        self.config.SECONDARY_COLOR = self.selected_color_secondary
        self.config.BACKGROUND_COLOR = self.selected_color_background
        self.config.CARD_BACKGROUND = self.selected_color_card

        # Update font settings
        self.config.FONT_FAMILY = self.font_family.currentFont().family()
        self.config.FONT_SIZE = self.font_size.value()

        # Save the updated config to file
        self.config.save(self.config_path)
        self.logger.info(f"UI settings saved to {self.config_path}")

        # Apply changes immediately where possible
        self._apply_current_theme()

        # Show message
        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "UI settings saved. Some changes will take effect after restarting the application.",
        )

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)

        # Use the proper icon file
        if os.path.exists("icon.ico"):
            self.tray_icon.setIcon(QIcon("icon.ico"))
        else:
            # Fallback to a simple colored icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(self.config.PRIMARY_COLOR))
            self.tray_icon.setIcon(QIcon(pixmap))

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)

        toggle_action = QAction("Toggle Activation", self)
        toggle_action.triggered.connect(self._toggle_activation)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)

        tray_menu.addAction(show_action)
        tray_menu.addAction(toggle_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Connect double-click to show window
        self.tray_icon.activated.connect(self._tray_activated)

    def _setup_connections(self):
        """Setup signal connections"""
        if self.aiwand:
            self.aiwand.signals.update_status.connect(self.update_status_indicator)

    def _toggle_activation(self):
        """Toggle application activation state"""
        if self.aiwand:
            try:
                self.aiwand.toggle_activation()
                # Ensure UI reflects current state even if a signal got missed
                if hasattr(self.aiwand, 'state'):
                    self.update_status_indicator(self.aiwand.state)
            except Exception as e:
                self.logger.error(f"Error toggling activation from MainWindow: {e}")
                QtWidgets.QMessageBox.warning(self, "Activation Error", str(e))

    def update_status_indicator(self, state):
        """Update status indicator based on application state"""
        # Update indicator color
        if state == AppState.ACTIVE:
            self.status_indicator.setStyleSheet(f"""
                background-color: {self.config.SECONDARY_COLOR};
                border-radius: 6px;
            """)
            self.status_label.setText("Active")
            self.activate_button.setText("Deactivate")
        elif state == AppState.PROCESSING:
            self.status_indicator.setStyleSheet(f"""
                background-color: {self.config.PRIMARY_COLOR};
                border-radius: 6px;
            """)
            self.status_label.setText("Processing")
        else:
            self.status_indicator.setStyleSheet(f"""
                background-color: {self.config.INACTIVE_COLOR};
                border-radius: 6px;
            """)
            self.status_label.setText("Inactive")
            self.activate_button.setText("Activate")

    def _clear_logs(self):
        """Clear log viewer"""
        self.log_viewer.clear()
        self.log_viewer.setHtml("<p style='color:#8E8E93;'>Log output will appear here...</p>")

    def _tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_application(self):
        """Quit the application"""
        QApplication.quit()

    def closeEvent(self, event):
        """Handle window close event"""
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "AI Wand",
            "Application minimized to tray. Double-click to restore.",
            QSystemTrayIcon.Information,
            2000,
        )

    def _apply_current_theme(self):
        """Apply the current theme to all UI components immediately"""
        # Update main window styling
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.config.BACKGROUND_COLOR};
            }}
            QLabel {{
                color: {self.config.PRIMARY_COLOR};
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
            }}
            QPushButton {{
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
                padding: 8px 16px;
                border-radius: {self.config.BORDER_RADIUS}px;
            }}
            QTabWidget {{
                font-family: {self.config.FONT_FAMILY};
                font-size: {self.config.FONT_SIZE}pt;
            }}
        """)

        # Update header
        cw = self.centralWidget()
        cw_layout = cw.layout() if cw is not None else None
        header_item = cw_layout.itemAt(0) if cw_layout is not None else None
        header_widget = header_item.widget() if header_item is not None else None
        if header_widget is not None:
            header_widget.setStyleSheet(f"""
            background-color: {self.config.CARD_BACKGROUND};
            border-radius: {self.config.BORDER_RADIUS}px;
            padding: 10px;
        """)

        # Update title
        if header_widget is not None:
            header_layout = header_widget.layout()
            title_item = header_layout.itemAt(0) if header_layout is not None else None
            title_label = title_item.widget() if title_item is not None else None
            if isinstance(title_label, QLabel):
                title_label.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")
                title_label.setFont(QFont(self.config.FONT_FAMILY, 14, QFont.Bold))

        # Update status indicator
        self.status_indicator.setStyleSheet(f"""
            background-color: {self.config.INACTIVE_COLOR};
            border-radius: 6px;
        """)

        # Update activate button
        self.activate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.PRIMARY_COLOR};
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {self.config.PRIMARY_COLOR}DD;
            }}
            QPushButton:pressed {{
                background-color: {self.config.PRIMARY_COLOR}AA;
            }}
        """)

        # Update tab widget
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.config.CARD_BACKGROUND};
                border-radius: {self.config.BORDER_RADIUS}px;
            }}
            QTabBar::tab {{
                background-color: {self.config.INACTIVE_COLOR}22;
                color: {self.config.PRIMARY_COLOR};
                border-top-left-radius: {self.config.BORDER_RADIUS}px;
                border-top-right-radius: {self.config.BORDER_RADIUS}px;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: normal;
            }}
            QTabBar::tab:selected {{
                background-color: {self.config.PRIMARY_COLOR};
                color: white;
                font-weight: bold;
            }}
        """)

        # Update all cards in dashboard
        dashboard_widget = self.tab_widget.widget(0)
        dashboard_layout = dashboard_widget.layout() if dashboard_widget is not None else None
        if dashboard_layout is not None and dashboard_layout.count() > 0:
            for i in range(dashboard_layout.count() - 1):  # -1 to skip the stretch
                item = dashboard_layout.itemAt(i)
                card = item.widget() if item is not None else None
                if card:
                    card.setStyleSheet(f"""
                    background-color: {self.config.CARD_BACKGROUND};
                    border-radius: {self.config.BORDER_RADIUS}px;
                    padding: 10px;
                """)

                    # Update card title
                    card_layout = card.layout()
                    if card_layout and card_layout.count() > 0:
                        first_item = card_layout.itemAt(0)
                        title = first_item.widget() if first_item is not None else None
                        if isinstance(title, QLabel):
                            title.setStyleSheet(f"color: {self.config.PRIMARY_COLOR};")
                            title.setFont(QFont(self.config.FONT_FAMILY, 12, QFont.Bold))

        # Update log viewer
        self.log_viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.config.CARD_BACKGROUND};
                border-radius: {self.config.BORDER_RADIUS}px;
                padding: 10px;
                border: 1px solid #E5E5EA;
            }}
        """)
        self.log_viewer.setFont(QFont(self.config.FONT_FAMILY, self.config.FONT_SIZE))

    def _apply_ui_changes(self):
        """Apply UI customization changes immediately"""
        if self.aiwand:
            # Mutate the existing config to avoid resetting defaults
            self.config.PRIMARY_COLOR = self.selected_color_primary
            self.config.SECONDARY_COLOR = self.selected_color_secondary
            self.config.BACKGROUND_COLOR = self.selected_color_background
            self.config.CARD_BACKGROUND = self.selected_color_card

            # Update font settings
            self.config.FONT_FAMILY = self.font_family.currentFont().family()
            self.config.FONT_SIZE = self.font_size.value()

            # Propagate to main app
            self.aiwand.config = self.config

            # Apply changes immediately
            self._apply_current_theme()

            # Show a small notification
            QtWidgets.QMessageBox.information(
                self,
                "Changes Applied",
                "UI changes have been applied. Some changes may require restarting the application for full effect.",
            )
