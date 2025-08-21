import logging
from typing import Optional

# Clipboard backends
try:
    import win32clipboard
    import win32con

    HAS_WIN32 = True
except Exception:  # pragma: no cover - non-Windows
    HAS_WIN32 = False

import pyperclip


class ClipboardManager:
    """Robust clipboard management with multiple fallback methods."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_clipboard_content(self) -> Optional[str]:
        """Get current clipboard content with fallback methods."""
        try:
            if HAS_WIN32:
                return self._get_win32_clipboard()
            else:
                return pyperclip.paste()
        except Exception as e:
            self.logger.warning(f"Failed to get clipboard content: {e}")
            return None

    def set_clipboard_content(self, text: str) -> bool:
        """Set clipboard content with fallback methods."""
        try:
            if HAS_WIN32:
                return self._set_win32_clipboard(text)
            else:
                pyperclip.copy(text)
                return True
        except Exception as e:
            self.logger.warning(f"Failed to set clipboard content: {e}")
            return False

    def clear_clipboard(self) -> bool:
        """Clear clipboard content."""
        try:
            if HAS_WIN32:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.CloseClipboard()
                return True
            else:
                pyperclip.copy("")
                return True
        except Exception as e:
            self.logger.warning(f"Failed to clear clipboard: {e}")
            return False

    def _get_win32_clipboard(self) -> Optional[str]:
        """Get clipboard content using win32 API."""
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return data
            else:
                win32clipboard.CloseClipboard()
                return None
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            raise

    def _set_win32_clipboard(self, text: str) -> bool:
        """Set clipboard content using win32 API."""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            raise
