import sys

import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

import aiwand.app_main as app_main
from aiwand.agents.definition_agent import DefinitionAgent
from aiwand.agents.rewrite_agent import RewriteAgent
from aiwand.app_main import AIWand, AppState


@pytest.fixture(scope="session")
def qapp():
    # Ensure Qt uses offscreen platform in CI
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    return app


class _DummyHotkeys:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        return None

    def stop(self):
        return None


class _DummyKeyboard:
    class Listener:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

        def stop(self):
            return None


class _DummyMouse:
    class Listener:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

        def stop(self):
            return None

    class Controller:
        @property
        def position(self):
            return (100, 200)


class _DummyMainWindow:
    def __init__(self, *args, **kwargs):
        class _Log:
            pass

        class _Tabs:
            def setCurrentIndex(self, *_):
                return None

        self.log_viewer = _Log()
        self.tab_widget = _Tabs()

    def show(self):
        return None

    def raise_(self):
        return None

    def activateWindow(self):
        return None

    def update_status_indicator(self, *_):
        return None


class _DummyPopup:
    def __init__(self, *args, **kwargs):
        self.speaker_icon = type(
            "S",
            (),
            {
                "clicked": type("C", (), {"connect": lambda *a, **k: None})(),
                "setProperty": lambda *a, **k: None,
                "property": lambda *a, **k: None,
            },
        )()

    def show_definition(self, *args, **kwargs):
        return None

    def hide(self, *args, **kwargs):
        return None


class _DummyEventFilter(QtCore.QObject):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def eventFilter(self, *_):
        # Do not consume any events
        return False

    def update_speech_status(self, *_):
        return None


class _DummyToolbar:
    def __init__(self, *args, **kwargs):
        class _Sig:
            def connect(self, *_args, **_kwargs):
                return None

        self.define_signal = _Sig()
        self.rewrite_signal = _Sig()
        self.summarize_signal = _Sig()
        self.translate_signal = _Sig()
        self.speak_signal = _Sig()

    def show_toolbar(self, *args, **kwargs):
        return None

    def hide(self, *args, **kwargs):
        return None


def test_toggle_activation_changes_state(monkeypatch, qapp):
    # Mock global hooks and dialogs before constructing AIWand
    monkeypatch.setattr(app_main, "GlobalHotKeys", _DummyHotkeys, raising=True)
    monkeypatch.setattr(app_main, "keyboard", _DummyKeyboard, raising=True)
    monkeypatch.setattr(app_main, "mouse", _DummyMouse, raising=True)
    # Mock heavy UI classes
    monkeypatch.setattr(app_main, "MainWindow", _DummyMainWindow, raising=True)
    monkeypatch.setattr(app_main, "AIWandPopup", _DummyPopup, raising=True)
    monkeypatch.setattr(app_main, "AIToolbar", _DummyToolbar, raising=True)
    # Mock GlobalEventFilter and TextToSpeech to avoid native integrations
    monkeypatch.setattr(app_main, "GlobalEventFilter", _DummyEventFilter, raising=True)

    class _DummyTTS:
        MAX_TEXT_LENGTH = 4000

        def __init__(self):
            self.on_speech_complete = None

        def is_available(self):
            return True

        def speak(self, *_):
            return True

        def stop(self):
            return None

    monkeypatch.setattr(app_main, "TextToSpeech", _DummyTTS, raising=True)

    # Mock Logger to avoid UI-bound logging handlers
    class _DummyLogger:
        @staticmethod
        def setup_logging(*_args, **_kwargs):
            import logging

            logging.basicConfig(level=logging.INFO)
            return logging.getLogger("test")

    monkeypatch.setattr(app_main, "Logger", _DummyLogger, raising=True)

    # Avoid popping UI when API key missing
    monkeypatch.setattr(AIWand, "_show_api_key_dialog", lambda self: None, raising=True)

    app = AIWand()
    # start inactive
    assert app.state == AppState.INACTIVE
    app.toggle_activation()
    assert app.state == AppState.ACTIVE
    app.toggle_activation()
    assert app.state == AppState.INACTIVE
    app._cleanup()


def test_process_selected_text_emits_toolbar_when_active(monkeypatch, qapp):
    # Mock hooks and dialog
    monkeypatch.setattr(app_main, "GlobalHotKeys", _DummyHotkeys, raising=True)
    monkeypatch.setattr(app_main, "keyboard", _DummyKeyboard, raising=True)
    monkeypatch.setattr(app_main, "mouse", _DummyMouse, raising=True)
    monkeypatch.setattr(app_main, "MainWindow", _DummyMainWindow, raising=True)
    monkeypatch.setattr(app_main, "AIWandPopup", _DummyPopup, raising=True)
    monkeypatch.setattr(app_main, "AIToolbar", _DummyToolbar, raising=True)
    monkeypatch.setattr(AIWand, "_show_api_key_dialog", lambda self: None, raising=True)

    app = AIWand()
    # Activate
    if app.state != AppState.ACTIVE:
        app.toggle_activation()

    # Mock mouse position and selected text
    calls = {}

    def capture_show_toolbar(text, x, y):
        calls['args'] = (text, x, y)

    app.signals.show_toolbar.disconnect()
    app.signals.show_toolbar.connect(capture_show_toolbar)

    # Stub text selector
    app.text_selector.get_selected_text = lambda: "hello world"

    app.process_selected_text()

    assert 'args' in calls
    text, x, y = calls['args']
    assert text == "hello world"
    assert isinstance(x, int) and isinstance(y, int)

    app._cleanup()


def test_process_selected_text_noop_when_inactive(monkeypatch, qapp):
    monkeypatch.setattr(app_main, "GlobalHotKeys", _DummyHotkeys, raising=True)
    monkeypatch.setattr(app_main, "keyboard", _DummyKeyboard, raising=True)
    monkeypatch.setattr(app_main, "mouse", _DummyMouse, raising=True)
    monkeypatch.setattr(app_main, "MainWindow", _DummyMainWindow, raising=True)
    monkeypatch.setattr(app_main, "AIWandPopup", _DummyPopup, raising=True)
    monkeypatch.setattr(app_main, "AIToolbar", _DummyToolbar, raising=True)
    monkeypatch.setattr(AIWand, "_show_api_key_dialog", lambda self: None, raising=True)

    app = AIWand()
    # Ensure inactive
    if app.state == AppState.ACTIVE:
        app.toggle_activation()

    emitted = {'called': False}

    def capture(*args, **kwargs):
        emitted['called'] = True

    app.signals.show_toolbar.disconnect()
    app.signals.show_toolbar.connect(capture)

    app.process_selected_text()

    assert emitted['called'] is False
    app._cleanup()


def test_agents_fallback_without_api_key():
    from aiwand.config import Config

    cfg = Config()
    cfg.API_KEY = ""  # ensure no key
    d = DefinitionAgent(cfg)
    r = RewriteAgent(cfg)

    out_def = d.define("test")
    assert isinstance(out_def, str) and len(out_def) > 0

    out_rw = r.rewrite("hello", "Formal")
    assert isinstance(out_rw, str) and len(out_rw) > 0
