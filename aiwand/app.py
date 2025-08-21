import os
import sys
from typing import Optional

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox

from aiwand.app_main import AIWand
from aiwand.config import Config
from aiwand.ui.main_window import MainWindow


def _install_qt_message_handler():
    """Install a Qt message handler to suppress known noisy font warnings.

    Suppresses messages like:
      - "QFontDatabase: Cannot find font directory .../PyQt5/Qt5/lib/fonts."
      - "Note that Qt no longer ships fonts. ..."
    All other Qt messages are forwarded to stderr.
    """

    def _handler(mode, context, message):
        msg = str(message)
        if (
            "QFontDatabase: Cannot find font directory" in msg
            or "Qt no longer ships fonts" in msg
        ):
            return  # suppress only these known benign warnings

        try:
            mt = QtCore.QtMsgType
            mapping = {
                mt.QtDebugMsg: "DEBUG",
                mt.QtInfoMsg: "INFO",
                mt.QtWarningMsg: "WARNING",
                mt.QtCriticalMsg: "CRITICAL",
                mt.QtFatalMsg: "FATAL",
            }
            level = mapping.get(mode, "LOG")
            sys.stderr.write(f"Qt[{level}]: {msg}\n")
        except Exception:
            # Last-resort: avoid crashing if logging fails
            pass

    # Install once per process; repeated installs just replace the handler
    QtCore.qInstallMessageHandler(_handler)


def _ensure_gui_platform():
    """Ensure a GUI platform is used when launching the app interactively on Windows.

    If QT_QPA_PLATFORM=offscreen leaked from test/CI runs, the app would start
    headless (no window). Clear it on Windows unless we're under pytest.
    """
    try:
        if os.name == 'nt' and 'PYTEST_CURRENT_TEST' not in os.environ:
            if os.environ.get('QT_QPA_PLATFORM', '').lower() == 'offscreen':
                os.environ.pop('QT_QPA_PLATFORM', None)
    except Exception:
        pass


def create_qapplication(existing_app: Optional[QApplication] = None) -> QApplication:
    if existing_app is not None:
        return existing_app
    app = QApplication.instance()
    return app or QApplication(sys.argv)


def main() -> int:
    try:
        # Suppress benign Qt font warnings before QApplication is created
        _install_qt_message_handler()

        # Ensure we are not in accidental headless mode on Windows
        _ensure_gui_platform()

        # Run full application (handles its own QApplication lifecycle)
        if AIWand is not None:
            app_instance = AIWand()
            return app_instance.run()

        # Fallback: show bare MainWindow with loaded Config
        app = create_qapplication()

        # Determine config path based on execution environment (match previous behavior)
        if getattr(sys, 'frozen', False):
            bundle_dir = os.path.dirname(sys.executable)
            config_path = os.path.join(bundle_dir, "settings.json")
        else:
            config_path = "settings.json"
        config = Config.load(config_path)

        window = MainWindow(config)
        window.show()
        return app.exec_()
    except Exception as e:  # Show a user-friendly error
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("AI Wand - Error")
            msg.setText("Failed to start AI Wand")
            msg.setInformativeText(str(e))
            msg.exec_()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
