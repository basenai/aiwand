from PyQt5 import QtCore


class SignalEmitter(QtCore.QObject):
    """Qt signal emitter for cross-thread communication"""

    show_popup = QtCore.pyqtSignal(str, int, int)
    hide_popup = QtCore.pyqtSignal()
    update_status = QtCore.pyqtSignal(object)  # Accepts AppState
    update_log = QtCore.pyqtSignal(str)
    show_toolbar = QtCore.pyqtSignal(str, int, int)  # Selected text, x, y
    hide_toolbar = QtCore.pyqtSignal()
    rewrite_text = QtCore.pyqtSignal(str, str)  # Original text, style
    summarize_text = QtCore.pyqtSignal(str)  # Text to summarize
    translate_text = QtCore.pyqtSignal(str, str, str)  # text, src, dst
    speak_text = QtCore.pyqtSignal(str)  # Text to speak
