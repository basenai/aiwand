import types

import pytest
from PyQt5.QtWidgets import QApplication

import aiwand.ui.toolbar as tb
from aiwand.config import Config


@pytest.fixture(scope="session")
def qapp_session():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def patched_translate_agent(monkeypatch):
    dummy = types.SimpleNamespace(LANGUAGES={"English": "en", "French": "fr"})
    monkeypatch.setattr(tb, "TranslateAgent", dummy, raising=False)
    return dummy


def test_toolbar_constructs(qapp_session, patched_translate_agent):
    cfg = Config()
    bar = tb.AIToolbar(cfg)
    assert bar is not None
    # style/source/target combos should be present and populated
    assert bar.style_combo.count() > 0
    assert bar.source_lang_combo.count() >= 1  # includes Auto-detect
    assert bar.target_lang_combo.count() > 0


def test_toolbar_show_and_hide(qapp_session, patched_translate_agent, monkeypatch):
    cfg = Config()
    bar = tb.AIToolbar(cfg)

    # Speed up fade animation to keep test quick
    bar.fade_step = 1.0

    # Spy on move calls
    calls = {"move": None}
    orig_move = bar.move

    def move_spy(x, y):
        calls["move"] = (x, y)
        return orig_move(x, y)

    monkeypatch.setattr(bar, "move", move_spy)

    # Show near top-left to trigger standard placement
    bar.show_toolbar("hello", 10, 10)

    assert bar.selected_text == "hello"
    assert isinstance(calls["move"], tuple)
    assert bar.isVisible()

    # Hide triggers fade-out then QWidget.hide via timer; call twice to ensure no error
    bar.hide()
    bar.hide()
