import types

import pytest
from PyQt5.QtWidgets import QApplication

from aiwand.config import Config
from aiwand.ui.popup import AIWandPopup


@pytest.fixture(scope="session")
def qapp_session():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _dummy_aiwand():
    tts = types.SimpleNamespace(stop=lambda: None)
    return types.SimpleNamespace(text_to_speech=tts)


def test_popup_show_definition_basic(qapp_session):
    cfg = Config()
    pop = AIWandPopup(cfg, aiwand=_dummy_aiwand())
    # Speed up animation
    pop.fade_step = 1.0

    pop.show_definition("Hello world", 10, 10)
    assert pop.isVisible()
    assert pop.label.text() == "Hello world"

    # Hide and ensure no error
    pop.hide(immediate=True)
    assert not pop.isVisible()


def test_popup_show_definition_error_styles(qapp_session):
    cfg = Config()
    pop = AIWandPopup(cfg)
    pop.fade_step = 1.0

    # Error text triggers auto hide timer start; we just ensure it shows without error
    pop.show_definition("Error: something", 20, 20)
    assert pop.isVisible()
    assert "Error" in pop.label.text()
    pop.hide(immediate=True)


def test_popup_show_speech_and_update(qapp_session):
    cfg = Config()
    pop = AIWandPopup(cfg)
    pop.fade_step = 1.0

    pop.show_speech("Speaking...", is_speaking=True, original_text="Original", text_limit=10)
    assert pop.isVisible()
    assert pop.status_label.isVisible()
    assert pop.speaker_icon.isVisible()
    assert "Speaking" in pop.label.text() or "Speaking" in pop.status_label.text()

    # update should not error
    pop.update_speech_status(True)

    pop.hide(immediate=True)
    assert not pop.isVisible()
