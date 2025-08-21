import logging
import time
from typing import Optional

from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key

from aiwand.config import Config

from .clipboard import ClipboardManager


class TextSelector:
    """Handles text selection from various sources with context awareness."""

    def __init__(self, config: Config):
        self.config = config
        self.clipboard_manager = ClipboardManager()
        self.keyboard_controller = KeyboardController()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Context capture settings
        self.enable_context = getattr(config, 'ENABLE_CONTEXT_DEFINITIONS', True)
        self.max_context_length = getattr(config, 'MAX_CONTEXT_LENGTH', 500)
        self.context_sentences_before = getattr(config, 'CONTEXT_SENTENCES_BEFORE', 1)
        self.context_sentences_after = getattr(config, 'CONTEXT_SENTENCES_AFTER', 1)

    def get_selected_text(self) -> Optional[str]:
        """
        Get selected text using multiple robust methods
        Returns None if no text is selected or an error occurs
        """
        original_clipboard = self.clipboard_manager.get_clipboard_content() or ""

        try:
            # Clear clipboard before copying
            if not self.clipboard_manager.clear_clipboard():
                self.logger.warning("Failed to clear clipboard")

            # Attempt to copy selected text multiple times
            selected_text = self._attempt_copy_selection()

            if selected_text and selected_text.strip():
                # Restore original clipboard content
                self._restore_clipboard(original_clipboard)
                return selected_text.strip()

            # Restore original clipboard if no text was selected
            self._restore_clipboard(original_clipboard)
            return None

        except Exception as e:
            self.logger.error(f"Error getting selected text: {e}")
            self._restore_clipboard(original_clipboard)
            return None

    def get_selected_text_with_context(self) -> tuple[Optional[str], str, str]:
        """
        Get selected text along with surrounding context
        Returns: (selected_text, context_before, context_after)
        """
        if not self.enable_context:
            # If context is disabled, return selected text with empty context
            selected_text = self.get_selected_text()
            return selected_text, "", ""

        original_clipboard = self.clipboard_manager.get_clipboard_content() or ""

        try:
            # First get the selected text normally
            selected_text = self.get_selected_text()
            if not selected_text:
                return None, "", ""

            # Try to get extended context using multiple strategies
            context_result = self._capture_extended_context(selected_text)

            if context_result:
                full_context, selected_pos = context_result
                context_before, context_after = self._extract_surrounding_context(
                    full_context, selected_text, selected_pos
                )
                return selected_text, context_before, context_after

            # Fallback: return selected text with no context
            return selected_text, "", ""

        except Exception as e:
            self.logger.error(f"Error getting selected text with context: {e}")
            self._restore_clipboard(original_clipboard)
            return None, "", ""

    def _capture_extended_context(self, selected_text: str) -> Optional[tuple[str, int]]:
        """
        Capture extended context around selected text using multiple strategies
        Returns: (full_context, selected_position) or None
        """
        strategies = [
            self._strategy_extended_selection,
            self._strategy_paragraph_selection,
            self._strategy_line_selection,
        ]

        for strategy in strategies:
            try:
                result = strategy(selected_text)
                if result:
                    return result
            except Exception as e:
                self.logger.debug(f"Context strategy {strategy.__name__} failed: {e}")

        return None

    def _strategy_extended_selection(self, selected_text: str) -> Optional[tuple[str, int]]:
        """Strategy 1: Try to extend selection to capture more context."""
        original_clipboard = self.clipboard_manager.get_clipboard_content() or ""

        try:
            # Try to select more text by extending selection
            # Ctrl+Shift+Left Arrow to extend selection left
            for _ in range(10):  # ~10 words to the left
                with self.keyboard_controller.pressed(Key.ctrl, Key.shift):
                    self.keyboard_controller.press(Key.left)
                    self.keyboard_controller.release(Key.left)
                time.sleep(0.01)

            # Ctrl+Shift+Right Arrow to extend selection right
            for _ in range(20):  # ~20 words to the right
                with self.keyboard_controller.pressed(Key.ctrl, Key.shift):
                    self.keyboard_controller.press(Key.right)
                    self.keyboard_controller.release(Key.right)
                time.sleep(0.01)

            # Copy the extended selection
            time.sleep(0.05)
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.press('c')
                self.keyboard_controller.release('c')

            time.sleep(0.1)
            extended_text = self.clipboard_manager.get_clipboard_content()

            if extended_text and len(extended_text) > len(selected_text):
                # Find position of original selected text in extended context
                selected_pos = extended_text.lower().find(selected_text.lower())
                if selected_pos != -1:
                    # Restore original clipboard
                    self._restore_clipboard(original_clipboard)
                    return extended_text, selected_pos

            # Restore original clipboard
            self._restore_clipboard(original_clipboard)
            return None

        except Exception as e:
            self.logger.debug(f"Extended selection strategy failed: {e}")
            self._restore_clipboard(original_clipboard)
            return None

    def _strategy_paragraph_selection(self, selected_text: str) -> Optional[tuple[str, int]]:
        """Strategy 2: Try to select the entire paragraph."""
        original_clipboard = self.clipboard_manager.get_clipboard_content() or ""

        try:
            # Try Ctrl+A to select all text in current text field/paragraph
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.press('a')
                self.keyboard_controller.release('a')

            time.sleep(0.1)

            # Copy the selection
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.press('c')
                self.keyboard_controller.release('c')

            time.sleep(0.1)
            paragraph_text = self.clipboard_manager.get_clipboard_content()

            if paragraph_text and len(paragraph_text) > len(selected_text):
                # Find position of original selected text
                selected_pos = paragraph_text.lower().find(selected_text.lower())
                if selected_pos != -1:
                    # Limit context length
                    if len(paragraph_text) > self.max_context_length:
                        # Trim context while keeping selected text centered
                        start_pos = max(0, selected_pos - self.max_context_length // 2)
                        end_pos = min(len(paragraph_text), start_pos + self.max_context_length)
                        trimmed_text = paragraph_text[start_pos:end_pos]
                        adjusted_pos = selected_pos - start_pos
                        paragraph_text = trimmed_text
                        selected_pos = adjusted_pos

                    # Restore original clipboard
                    self._restore_clipboard(original_clipboard)
                    return paragraph_text, selected_pos

            # Restore original clipboard
            self._restore_clipboard(original_clipboard)
            return None

        except Exception as e:
            self.logger.debug(f"Paragraph selection strategy failed: {e}")
            self._restore_clipboard(original_clipboard)
            return None

    def _strategy_line_selection(self, selected_text: str) -> Optional[tuple[str, int]]:
        """Strategy 3: Try to select the current line."""
        original_clipboard = self.clipboard_manager.get_clipboard_content() or ""

        try:
            # Home key to go to beginning of line
            self.keyboard_controller.press(Key.home)
            self.keyboard_controller.release(Key.home)
            time.sleep(0.05)

            # Shift+End to select to end of line
            with self.keyboard_controller.pressed(Key.shift):
                self.keyboard_controller.press(Key.end)
                self.keyboard_controller.release(Key.end)

            time.sleep(0.05)

            # Copy the line
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.press('c')
                self.keyboard_controller.release('c')

            time.sleep(0.1)
            line_text = self.clipboard_manager.get_clipboard_content()

            if line_text and len(line_text) > len(selected_text):
                # Find position of original selected text
                selected_pos = line_text.lower().find(selected_text.lower())
                if selected_pos != -1:
                    # Restore original clipboard
                    self._restore_clipboard(original_clipboard)
                    return line_text, selected_pos

            # Restore original clipboard
            self._restore_clipboard(original_clipboard)
            return None

        except Exception as e:
            self.logger.debug(f"Line selection strategy failed: {e}")
            self._restore_clipboard(original_clipboard)
            return None

    def _extract_surrounding_context(
        self, full_text: str, selected_text: str, selected_pos: int
    ) -> tuple[str, str]:
        """Extract context before and after the selected text."""
        try:
            before_text = full_text[:selected_pos]
            after_text = full_text[selected_pos + len(selected_text) :]

            context_before = self._extract_sentence_context(before_text, reverse=True)
            context_after = self._extract_sentence_context(after_text, reverse=False)

            return context_before, context_after

        except Exception as e:
            self.logger.debug(f"Error extracting surrounding context: {e}")
            return "", ""

    def _extract_sentence_context(self, text: str, reverse: bool = False) -> str:
        """Extract sentence context from text."""
        if not text.strip():
            return ""

        sentence_endings = ['.', '!', '?', '\n', '\r']

        if reverse:
            sentences = []
            current_sentence = ""
            for char in reversed(text):
                current_sentence = char + current_sentence
                if char in sentence_endings:
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
                        if len(sentences) >= self.context_sentences_before:
                            break
                    current_sentence = ""
            if current_sentence.strip() and len(sentences) < self.context_sentences_before:
                sentences.append(current_sentence.strip())
            return " ".join(reversed(sentences[-self.context_sentences_before :]))
        else:
            sentences = []
            current_sentence = ""
            for char in text:
                current_sentence += char
                if char in sentence_endings:
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
                        if len(sentences) >= self.context_sentences_after:
                            break
                    current_sentence = ""
            if current_sentence.strip() and len(sentences) < self.context_sentences_after:
                sentences.append(current_sentence.strip())
            return " ".join(sentences[: self.context_sentences_after])

    def _attempt_copy_selection(self) -> Optional[str]:
        """Attempt to copy selected text with multiple retries."""
        for attempt in range(self.config.COPY_ATTEMPTS):
            try:
                # Send Ctrl+C
                with self.keyboard_controller.pressed(Key.ctrl):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
                # Wait with progressive delay
                time.sleep(self.config.COPY_DELAY * (attempt + 1))
                # Get clipboard content
                new_text = self.clipboard_manager.get_clipboard_content()
                if new_text and new_text.strip():
                    return new_text
            except Exception as e:
                self.logger.warning(f"Copy attempt {attempt + 1} failed: {e}")
        return None

    def _restore_clipboard(self, original_content: str) -> None:
        """Restore original clipboard content."""
        try:
            if original_content:
                self.clipboard_manager.set_clipboard_content(original_content)
            else:
                self.clipboard_manager.clear_clipboard()
        except Exception as e:
            self.logger.warning(f"Failed to restore clipboard: {e}")
