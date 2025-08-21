# Ensure the project root is importable as a package without installation
import os
import sys
from pathlib import Path

import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication for tests and force headless Qt.

    Many tests don't need Qt, but when they do, this ensures a single
    QApplication exists and that Qt uses the offscreen platform which is
    compatible with CI/headless environments.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Install a message handler to suppress benign font warnings from Qt
    def _qt_msg_handler(mode, context, message):
        msg = str(message)
        if (
            "QFontDatabase: Cannot find font directory" in msg
            or "Qt no longer ships fonts" in msg
        ):
            return
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
            pass

    QtCore.qInstallMessageHandler(_qt_msg_handler)
    return QApplication.instance() or QApplication([])
