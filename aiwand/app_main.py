import os
import sys
import threading
import time

from pynput import keyboard, mouse
from pynput.keyboard import GlobalHotKeys
from PyQt5 import QtCore, QtGui, QtWidgets

from aiwand.agents import DefinitionAgent, RewriteAgent, SummarizeAgent, TranslateAgent
from aiwand.app_state import AppState
from aiwand.config import Config
from aiwand.core import TextSelector
from aiwand.logging_util import Logger
from aiwand.services import TextToSpeech
from aiwand.signals import SignalEmitter
from aiwand.ui.main_window import MainWindow
from aiwand.ui.popup import AIWandPopup
from aiwand.ui.toolbar import AIToolbar, GlobalEventFilter


class AIWand:
    """Main application class with enhanced error handling and maintainability"""

    def __init__(self):
        # Determine config path and load a single shared Config instance
        if getattr(sys, 'frozen', False):
            bundle_dir = os.path.dirname(sys.executable)
            self.config_path = os.path.join(bundle_dir, MainWindow.CONFIG_FILE)
        else:
            self.config_path = MainWindow.CONFIG_FILE

        self.config = Config.load(self.config_path)

        # Initialize Qt application first
        self._initialize_qt_app()

        # Initialize components
        self._initialize_components()

        # Setup logger after UI components
        self.logger = Logger.setup_logging(self.main_window.log_viewer, self.config.LOG_MAX_LINES)

        # Set initial state
        self.state = AppState.INACTIVE

        # Store the most recent spoken text
        self.last_spoken_text = ""

        # Validate configuration
        if not self._validate_config():
            self.logger.info("Configuration validation failed")
            self.signals.update_status.emit(AppState.INACTIVE)

            # Show configuration dialog if API key is missing
            if not self.config.API_KEY:
                self._show_api_key_dialog()
            # Do NOT return; allow UI and hotkeys to initialize in inactive mode

        # Setup event handlers
        self._setup_hotkeys()
        self._setup_keyboard_listener()
        self._setup_mouse_listener()

        self.logger.info("AIWand initialized successfully")
        self._print_usage_info()

    def _validate_config(self) -> bool:
        """Validate application configuration"""
        if not self.config.API_KEY:
            self.logger.warning(
                "API key not configured. Please set GEMINI_API_KEY environment variable."
            )
            return False

        # Agents import presence is guaranteed by our imports; keep message for clarity.
        return True

    def _show_api_key_dialog(self):
        """Show dialog to configure API key"""
        # MainWindow hosts settings UI; delegate to it if available
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        # Open LLM Settings tab (index 2 in existing UI)
        self.main_window.tab_widget.setCurrentIndex(2)

    def _initialize_qt_app(self):
        """Initialize Qt application"""
        # Reuse existing instance if present (important for tests/CI)
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Set application style
        self.app.setStyle("Fusion")

        # Set application icon
        if os.path.exists("icon.ico"):
            self.app.setWindowIcon(QtGui.QIcon("icon.ico"))

        # Install global event filter to handle dropdown events
        self.app.installEventFilter(GlobalEventFilter())

    def _initialize_components(self):
        """Initialize application components"""
        # Create signals first
        self.signals = SignalEmitter()

        # Create UI components
        # Pass the SAME config instance to every component
        self.main_window = MainWindow(self.config, self)
        self.popup = AIWandPopup(self.config, self)  # Pass AIWand instance to popup
        self.toolbar = AIToolbar(self.config)

        # Create functional components
        self.text_selector = TextSelector(self.config)
        self.definition_agent = DefinitionAgent(self.config)
        self.rewrite_agent = RewriteAgent(self.config)
        self.summarize_agent = SummarizeAgent(self.config)
        self.translate_agent = TranslateAgent(self.config)
        self.text_to_speech = TextToSpeech()

        # Connect signals
        self._connect_signals()

    def _connect_signals(self):
        """Connect all signals to their handlers"""
        # Popup signals
        self.signals.show_popup.connect(self.popup.show_definition)
        self.signals.hide_popup.connect(self.popup.hide)

        # Status signal
        self.signals.update_status.connect(self.main_window.update_status_indicator)

        # Toolbar signals
        self.signals.show_toolbar.connect(self.toolbar.show_toolbar)
        self.signals.hide_toolbar.connect(self.toolbar.hide)

        # Assign toolbar button handlers
        self.toolbar.define_signal = self._handle_define_clicked
        self.toolbar.rewrite_signal = self._handle_rewrite_clicked
        self.toolbar.summarize_signal = self._handle_summarize_clicked
        self.toolbar.translate_signal = self._handle_translate_clicked
        self.toolbar.speak_signal = self._handle_speak_clicked
        self.toolbar.settings_signal = lambda: self._show_main_window_tab(2)  # LLM Settings
        self.toolbar.customize_signal = lambda: self._show_main_window_tab(3)  # UI Customization

        # Connect emitted work signals to processing slots
        self.signals.rewrite_text.connect(self._rewrite_text)
        self.signals.summarize_text.connect(self._summarize_text)
        self.signals.translate_text.connect(self._translate_text)
        self.signals.speak_text.connect(self._speak_text)

        # Connect speaker icon click
        self.popup.speaker_icon.clicked.connect(self._listen_again_clicked)

        # Set up callback for speech completion
        self.text_to_speech.on_speech_complete = self._on_speech_complete
        self.last_ctrl_press_time: float = 0.0

    def _setup_hotkeys(self):
        """Setup global hotkeys with error handling"""
        try:
            self.hotkeys = GlobalHotKeys(
                {
                    '<ctrl>+<shift>+a': self.toggle_activation,
                }
            )
            self.hotkeys.start()
            self.logger.info("Global hotkeys registered successfully")
        except Exception as e:
            self.logger.warning(f"Failed to setup hotkeys: {e}")
            raise

    def _on_press(self, key):
        try:
            if key == keyboard.Key.ctrl_r:
                current_time = time.time()
                if current_time - self.last_ctrl_press_time < 0.3:
                    self.process_selected_text()
                self.last_ctrl_press_time = current_time
        except Exception as e:
            self.logger.error(f"Error in _on_press: {e}")

    def _setup_keyboard_listener(self):
        """Setup keyboard listener for double press"""
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
            self.keyboard_listener.start()
            self.logger.info("Keyboard listener started successfully")
        except Exception as e:
            self.logger.warning(f"Failed to setup keyboard listener: {e}")
            raise

    def _setup_mouse_listener(self):
        """Setup mouse listener for hiding popup"""
        try:
            self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
            self.mouse_listener.start()
            self.logger.info("Mouse listener started successfully")
        except Exception as e:
            self.logger.warning(f"Failed to setup mouse listener: {e}")
            raise

    def _print_usage_info(self):
        """Print usage information"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("AI Definition Wand - Ready!")
        self.logger.info("=" * 60)
        self.logger.info("Controls:")
        self.logger.info("   • Ctrl+Shift+A: Toggle activation (currently OFF)")
        self.logger.info("   • Right-Ctrl twice: Open AI toolbar with multiple features")
        self.logger.info("Usage:")
        self.logger.info("   1. Activate the tool with Ctrl+Shift+A")
        self.logger.info("   2. Select any text")
        self.logger.info("   3. Press Right-Ctrl twice to open the AI toolbar")
        self.logger.info("   4. Choose an action from the toolbar")
        self.logger.info("=" * 60)

    def toggle_activation(self):
        """Toggle application activation state"""
        try:
            if self.state == AppState.ACTIVE:
                self.state = AppState.INACTIVE
                self.logger.info("AIWand DEACTIVATED")
                self.signals.update_status.emit(AppState.INACTIVE)
            else:
                self.state = AppState.ACTIVE
                self.logger.info("AIWand ACTIVATED")
                self.signals.update_status.emit(AppState.ACTIVE)
        except Exception as e:
            self.logger.error(f"Error toggling activation: {e}")

    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse clicks to hide popup only when clicking outside"""
        try:
            if pressed:
                if self.popup.isVisible():
                    popup_global_rect = QtCore.QRect(
                        self.popup.mapToGlobal(QtCore.QPoint(0, 0)),
                        self.popup.size(),
                    )
                    if not popup_global_rect.contains(x, y):
                        self.signals.hide_popup.emit()

                if self.toolbar.isVisible():
                    if AIToolbar.dropdown_active:
                        return

                    toolbar_global_rect = QtCore.QRect(
                        self.toolbar.mapToGlobal(QtCore.QPoint(0, 0)),
                        self.toolbar.size(),
                    )

                    # Check dropdown views
                    for combo_attr in ['style_combo', 'source_lang_combo', 'target_lang_combo']:
                        if hasattr(self.toolbar, combo_attr):
                            combo = getattr(self.toolbar, combo_attr)
                            if combo.view() and combo.view().isVisible():
                                dropdown_rect = QtCore.QRect(
                                    combo.view().mapToGlobal(QtCore.QPoint(0, 0)),
                                    combo.view().size(),
                                )
                                if dropdown_rect.contains(x, y):
                                    return

                    any_dropdown_active = False
                    for combo_attr in ['style_combo', 'source_lang_combo', 'target_lang_combo']:
                        if hasattr(self.toolbar, combo_attr):
                            combo = getattr(self.toolbar, combo_attr)
                            if hasattr(combo, 'popup_active') and combo.popup_active:
                                any_dropdown_active = True
                                break

                    if any_dropdown_active:
                        return

                    if not toolbar_global_rect.contains(x, y):
                        self.signals.hide_toolbar.emit()
        except Exception as e:
            self.logger.error(f"Error handling mouse click: {e}")

    def process_selected_text(self):
        """Process selected text and show AI toolbar"""
        if self.state != AppState.ACTIVE:
            return

        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)

            mouse_pos = mouse.Controller().position
            x, y = mouse_pos

            selected_text = self.text_selector.get_selected_text()

            self.signals.show_toolbar.emit(selected_text, x, y)
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)
        except Exception as e:
            self.logger.error(f"Error processing selected text: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error processing text: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _handle_define_clicked(self, text):
        if not text:
            return
        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)
            x, y = mouse.Controller().position
            self.signals.show_popup.emit("Getting definition...", x, y)
            threading.Thread(
                target=self._get_definition_thread,
                args=(text, x, y),
                daemon=True,
            ).start()
        except Exception as e:
            self.logger.error(f"Error handling define text: {e}")
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _handle_rewrite_clicked(self, text, style):
        if not text:
            return
        try:
            self.signals.rewrite_text.emit(text, style)
        except Exception as e:
            self.logger.error(f"Error preparing text for rewrite: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error preparing text for rewrite: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )

    def _handle_summarize_clicked(self, text):
        if not text:
            return
        try:
            self.signals.summarize_text.emit(text)
        except Exception as e:
            self.logger.error(f"Error preparing text for summarization: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error preparing text for summarization: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )

    def _handle_translate_clicked(self, text, source_lang, target_lang):
        if not text:
            return
        try:
            self.signals.translate_text.emit(text, source_lang, target_lang)
        except Exception as e:
            self.logger.error(f"Error preparing text for translation: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error preparing text for translation: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )

    def _handle_speak_clicked(self, text):
        if not text:
            return
        try:
            self.signals.speak_text.emit(text)
        except Exception as e:
            self.logger.error(f"Error preparing text for speech: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error preparing text for speech: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )

    def _show_main_window_tab(self, tab_index):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        self.main_window.tab_widget.setCurrentIndex(tab_index)

    def _rewrite_text(self, text: str, style: str):
        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)
            x, y = mouse.Controller().position
            self.signals.show_popup.emit(f"Rewriting text in {style} style...", x, y)
            threading.Thread(
                target=self._get_rewrite_thread,
                args=(text, style, x, y),
                daemon=True,
            ).start()
        except Exception as e:
            self.logger.error(f"Error rewriting text: {e}")
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _get_rewrite_thread(self, text: str, style: str, x: int, y: int):
        try:
            rewritten = self.rewrite_agent.rewrite(text, style)
            self.signals.show_popup.emit(rewritten, x, y)
        except Exception as e:
            self.logger.error(f"Error in rewrite thread: {e}")
            self.signals.show_popup.emit(f"Failed to rewrite text: {str(e)}", x, y)
        finally:
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _get_definition_thread(self, text: str, x: int, y: int):
        """Background thread: fetch definition and show popup."""
        try:
            definition = self.definition_agent.define(text)
            self.signals.show_popup.emit(definition, x, y)
        except Exception as e:
            self.logger.error(f"Error in definition thread: {e}")
            self.signals.show_popup.emit(f"Failed to get definition: {str(e)}", x, y)
        finally:
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _summarize_text(self, text: str):
        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)
            x, y = mouse.Controller().position
            self.signals.show_popup.emit("Summarizing text...", x, y)
            threading.Thread(
                target=self._get_summary_thread,
                args=(text, x, y),
                daemon=True,
            ).start()
        except Exception as e:
            self.logger.error(f"Error summarizing text: {e}")
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _get_summary_thread(self, text: str, x: int, y: int):
        try:
            summary = self.summarize_agent.summarize(text)
            self.signals.show_popup.emit(summary, x, y)
        except Exception as e:
            self.logger.error(f"Error in summary thread: {e}")
            self.signals.show_popup.emit(f"Failed to summarize text: {str(e)}", x, y)
        finally:
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _translate_text(self, text: str, source_lang: str, target_lang: str):
        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)
            x, y = mouse.Controller().position
            self.signals.show_popup.emit(f"Translating text to {target_lang}...", x, y)
            threading.Thread(
                target=self._get_translation_thread,
                args=(text, source_lang, target_lang, x, y),
                daemon=True,
            ).start()
        except Exception as e:
            self.logger.error(f"Error translating text: {e}")
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _get_translation_thread(
        self, text: str, source_lang: str, target_lang: str, x: int, y: int
    ):
        try:
            translation = self.translate_agent.translate(text, source_lang, target_lang)
            if (
                translation.startswith("Failed")
                or translation.startswith("Error")
                or translation.startswith("Unable")
                or translation.startswith("AI service")
            ):
                formatted_translation = translation
            else:
                parts = translation.split("\n")
                if len(parts) >= 2:
                    native = parts[0].strip()
                    romanized = parts[1].strip()
                    formatted_translation = f"""<div style=\"text-align: center;\">\n<span style=\"font-size: 14pt; font-weight: bold;\">{native}</span>\n<br><br>\n<span style=\"font-size: 12pt; color: #555;\">{romanized}</span>\n</div>"""
                else:
                    formatted_translation = translation
            self.signals.show_popup.emit(formatted_translation, x, y)
        except Exception as e:
            self.logger.error(f"Error in translation thread: {e}")
            self.signals.show_popup.emit(
                f"Failed to translate text to {target_lang}: {str(e)}", x, y
            )
        finally:
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _speak_text(self, text: str):
        try:
            self.state = AppState.PROCESSING
            self.signals.update_status.emit(AppState.PROCESSING)
            x, y = mouse.Controller().position
            if not self.text_to_speech.is_available():
                self.signals.show_popup.emit(
                    "Text-to-speech is not available. Please install the pyttsx3 library.",
                    x,
                    y,
                )
                self.state = AppState.ACTIVE
                self.signals.update_status.emit(AppState.ACTIVE)
                return
            self.last_spoken_text = text
            if len(text) > self.text_to_speech.MAX_TEXT_LENGTH:
                display_text = text[: self.text_to_speech.MAX_TEXT_LENGTH]
                speak_text = text[: self.text_to_speech.MAX_TEXT_LENGTH]
            else:
                display_text = text
                speak_text = text
            formatted_text = f"""
<div style="margin-top: 5px; padding: 10px; border: 1px solid #E5E5EA; border-radius: 5px; background-color: #F8F8F8;">
{display_text}
</div>
"""
            self.popup.show_speech(
                formatted_text,
                True,
                speak_text,
                self.text_to_speech.MAX_TEXT_LENGTH,
            )
            success = self.text_to_speech.speak(speak_text)
            if not success:
                self.popup.update_speech_status(False)
                self.signals.show_popup.emit(
                    "Failed to speak the text. Text-to-speech service may not be available.",
                    x,
                    y,
                )
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)
        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {e}")
            mouse_pos = mouse.Controller().position
            self.signals.show_popup.emit(
                f"Error in text-to-speech: {str(e)}",
                mouse_pos[0],
                mouse_pos[1],
            )
            self.state = AppState.ACTIVE
            self.signals.update_status.emit(AppState.ACTIVE)

    def _on_speech_complete(self):
        QtCore.QMetaObject.invokeMethod(
            self.popup,
            "update_speech_status",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(bool, False),
        )

    def _listen_again_clicked(self):
        try:
            original_text = self.popup.speaker_icon.property("original_text")
            if original_text:
                if self.text_to_speech.speak(original_text):
                    self.popup.update_speech_status(True)
            else:
                if self.last_spoken_text:
                    if self.text_to_speech.speak(self.last_spoken_text):
                        self.popup.update_speech_status(True)
        except Exception as e:
            self.logger.error(f"Error handling listen again: {e}")
            self.popup.update_speech_status(False)

    def _ensure_window_visible(self):
        """Bring the main window to the foreground and center if off-screen."""
        try:
            w = self.main_window
            # Ensure it's a normal, visible window
            w.showNormal()
            w.raise_()
            w.activateWindow()

            # If window is off-screen (e.g., due to monitor changes), center it
            screen = self.app.primaryScreen()
            if screen is not None:
                ag = screen.availableGeometry()
                fg = w.frameGeometry()
                if not ag.intersects(fg):
                    center_pos = ag.center() - w.rect().center()
                    w.move(center_pos)
        except Exception as e:
            self.logger.warning(f"Failed to ensure window visible: {e}")

    def run(self) -> int:
        try:
            self.logger.info("Starting application main loop")
            self.main_window.show()
            # Bring window to foreground to ensure visibility on startup
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()
            # Log visibility and geometry to help debugging
            try:
                g = self.main_window.geometry()
                self.logger.info(
                    f"Main window visible={self.main_window.isVisible()} geom=({g.x()},{g.y()},{g.width()},{g.height()})"
                )
            except Exception:
                pass

            # Ensure visibility again after the event loop starts
            QtCore.QTimer.singleShot(50, self._ensure_window_visible)
            return self.app.exec_()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            return 0
        except Exception as e:
            print(f"Application error: {e}")
            return 1
        finally:
            self._cleanup()

    def _cleanup(self):
        try:
            if hasattr(self, 'hotkeys'):
                self.hotkeys.stop()
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
            if hasattr(self, 'keyboard_listener'):
                self.keyboard_listener.stop()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def _reinitialize_agents(self):
        try:
            self.definition_agent = DefinitionAgent(self.config)
            self.rewrite_agent = RewriteAgent(self.config)
            self.summarize_agent = SummarizeAgent(self.config)
            self.translate_agent = TranslateAgent(self.config)
            self.logger.info("AI agents reinitialized with new configuration")
        except Exception as e:
            self.logger.warning(f"Failed to reinitialize AI agents: {e}")
