import types

import pytest

from aiwand.core.clipboard import ClipboardManager


@pytest.fixture()
def mgr():
    return ClipboardManager()


def test_get_clipboard_content_win32_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    fake = types.SimpleNamespace()
    calls = {}

    def OpenClipboard():
        calls["open"] = True

    def CloseClipboard():
        calls["close"] = True

    def IsClipboardFormatAvailable(fmt):
        return True

    def GetClipboardData():
        return "hello"

    fake.OpenClipboard = OpenClipboard
    fake.CloseClipboard = CloseClipboard
    fake.IsClipboardFormatAvailable = IsClipboardFormatAvailable
    fake.GetClipboardData = GetClipboardData

    monkeypatch.setattr(cb, "win32clipboard", fake, raising=False)
    monkeypatch.setattr(cb, "win32con", types.SimpleNamespace(CF_TEXT=1), raising=False)
    monkeypatch.setattr(cb, "HAS_WIN32", True, raising=False)

    assert mgr.get_clipboard_content() == "hello"
    assert calls.get("open") and calls.get("close")


def test_get_clipboard_content_win32_no_text(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    fake = types.SimpleNamespace()

    def OpenClipboard():
        pass

    def CloseClipboard():
        pass

    def IsClipboardFormatAvailable(fmt):
        return False

    fake.OpenClipboard = OpenClipboard
    fake.CloseClipboard = CloseClipboard
    fake.IsClipboardFormatAvailable = IsClipboardFormatAvailable

    monkeypatch.setattr(cb, "win32clipboard", fake, raising=False)
    monkeypatch.setattr(cb, "win32con", types.SimpleNamespace(CF_TEXT=1), raising=False)
    monkeypatch.setattr(cb, "HAS_WIN32", True, raising=False)

    assert mgr.get_clipboard_content() is None


def test_get_clipboard_content_pyperclip_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    monkeypatch.setattr(cb, "HAS_WIN32", False, raising=False)
    monkeypatch.setattr(cb.pyperclip, "paste", lambda: "world")

    assert mgr.get_clipboard_content() == "world"


def test_set_clipboard_content_win32_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    fake = types.SimpleNamespace()
    calls = {}

    def OpenClipboard():
        calls["open"] = True

    def CloseClipboard():
        calls["close"] = True

    def EmptyClipboard():
        calls["empty"] = True

    def SetClipboardText(text):
        calls["text"] = text

    fake.OpenClipboard = OpenClipboard
    fake.CloseClipboard = CloseClipboard
    fake.EmptyClipboard = EmptyClipboard
    fake.SetClipboardText = SetClipboardText

    monkeypatch.setattr(cb, "win32clipboard", fake, raising=False)
    monkeypatch.setattr(cb, "HAS_WIN32", True, raising=False)

    assert mgr.set_clipboard_content("abc") is True
    assert calls == {"open": True, "empty": True, "text": "abc", "close": True}


def test_set_clipboard_content_pyperclip_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    monkeypatch.setattr(cb, "HAS_WIN32", False, raising=False)
    called = {}
    monkeypatch.setattr(cb.pyperclip, "copy", lambda s: called.setdefault("copy", s))

    assert mgr.set_clipboard_content("xyz") is True
    assert called["copy"] == "xyz"


def test_clear_clipboard_win32_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    fake = types.SimpleNamespace()
    calls = {}

    def OpenClipboard():
        calls["open"] = True

    def CloseClipboard():
        calls["close"] = True

    def EmptyClipboard():
        calls["empty"] = True

    fake.OpenClipboard = OpenClipboard
    fake.CloseClipboard = CloseClipboard
    fake.EmptyClipboard = EmptyClipboard

    monkeypatch.setattr(cb, "win32clipboard", fake, raising=False)
    monkeypatch.setattr(cb, "HAS_WIN32", True, raising=False)

    assert mgr.clear_clipboard() is True
    assert calls == {"open": True, "empty": True, "close": True}


def test_clear_clipboard_pyperclip_success(monkeypatch, mgr):
    import aiwand.core.clipboard as cb

    monkeypatch.setattr(cb, "HAS_WIN32", False, raising=False)
    called = {}
    monkeypatch.setattr(cb.pyperclip, "copy", lambda s: called.setdefault("copy", s))

    assert mgr.clear_clipboard() is True
    assert called["copy"] == ""


def test_error_paths_log_warning(monkeypatch, mgr, caplog):
    import aiwand.core.clipboard as cb

    # Force exceptions in both backends and assert graceful failure
    caplog.set_level("WARNING")

    # get_clipboard_content (win32 path)
    monkeypatch.setattr(cb, "HAS_WIN32", True, raising=False)
    fake = types.SimpleNamespace(OpenClipboard=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(cb, "win32clipboard", fake, raising=False)
    assert mgr.get_clipboard_content() is None
    assert any("Failed to get clipboard content" in rec.message for rec in caplog.records)

    # set_clipboard_content (pyperclip path)
    caplog.clear()
    monkeypatch.setattr(cb, "HAS_WIN32", False, raising=False)

    def bad_copy(_):
        raise RuntimeError("bad")

    monkeypatch.setattr(cb.pyperclip, "copy", bad_copy)
    assert mgr.set_clipboard_content("t") is False
    assert any("Failed to set clipboard content" in rec.message for rec in caplog.records)

    # clear_clipboard (pyperclip path)
    caplog.clear()

    def bad_copy2(_):
        raise RuntimeError("bad2")

    monkeypatch.setattr(cb.pyperclip, "copy", bad_copy2)
    assert mgr.clear_clipboard() is False
    assert any("Failed to clear clipboard" in rec.message for rec in caplog.records)
