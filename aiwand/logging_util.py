import datetime
import logging
import sys
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class Logger:
    """Centralized logging configuration with optional QTextEdit UI handler."""

    class QTextEditLogger(logging.Handler):
        """Logging handler that writes to a QTextEdit safely across threads."""

        def __init__(self, text_edit: QtWidgets.QTextEdit, max_lines: int = 1000):
            super().__init__()
            self.text_edit = text_edit
            self.max_lines = max_lines
            self.level_colors = {
                logging.DEBUG: "#8E8E93",
                logging.INFO: "#000000",
                logging.WARNING: "#FF9500",
                logging.ERROR: "#FF3B30",
                logging.CRITICAL: "#AF52DE",
            }

        def emit(self, record: logging.LogRecord) -> None:
            color = self.level_colors.get(record.levelno, "#000000")
            timestamp = datetime.datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            formatted = (
                f'<span style="color:{color}"><b>[{timestamp}]</b> '
                f"{record.levelname}: {record.getMessage()}</span>"
            )
            QtCore.QMetaObject.invokeMethod(
                self.text_edit,
                "append",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, formatted),
            )
            # Trim lines
            doc = self.text_edit.document()
            if doc is not None and doc.lineCount() > self.max_lines:
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QtGui.QTextCursor.Start)
                cursor.movePosition(
                    QtGui.QTextCursor.Down,
                    QtGui.QTextCursor.KeepAnchor,
                    doc.lineCount() - self.max_lines,
                )
                cursor.removeSelectedText()

    @staticmethod
    def setup_logging(text_edit: Optional[QtWidgets.QTextEdit] = None, max_lines: int = 1000) -> logging.Logger:
        handlers: list[logging.Handler] = [
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('aiwand.log', mode='a', encoding='utf-8'),
        ]
        if text_edit is not None:
            ui_handler = Logger.QTextEditLogger(text_edit, max_lines)
            ui_handler.setFormatter(logging.Formatter('%(message)s'))
            handlers.append(ui_handler)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )
        return logging.getLogger(__name__)

