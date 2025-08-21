"""Text-to-speech service using pyttsx3.
Extracted from main.py for modularization.
"""

from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue

# Optional dependency: pyttsx3
try:  # pragma: no cover - env dependent
    import pyttsx3

    HAS_TTS = True
except Exception:  # pragma: no cover
    pyttsx3 = None
    HAS_TTS = False


class TextToSpeech:
    """Text-to-speech functionality for speaking selected text"""

    def __init__(self):
        self.engine = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialize_engine()
        self.is_speaking = False
        self.current_thread = None  # kept for backward compatibility; unused after refactor
        self.MAX_TEXT_LENGTH = 1000  # Maximum length of text to speak

        # Add a callback for when speech is done
        self.on_speech_complete = None

        # Store available voices
        self.available_voices = []
        # Concurrency and notification guards
        self._lock = threading.RLock()
        self._stopping = False
        self._notified = False

        # Command queue and worker to serialize engine operations
        self._queue: Queue = Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        self._cancel_requested = False

    def _initialize_engine(self):
        """Initialize the TTS engine with proper error handling"""
        if not HAS_TTS:
            self.logger.info("Text-to-speech library not available")
            return

        try:
            self.engine = pyttsx3.init()
            # Set properties
            self.engine.setProperty("rate", 150)  # Speed of speech
            self.engine.setProperty("volume", 1.0)  # Volume (0.0 to 1.0)

            # Get available voices
            voices = self.engine.getProperty("voices")
            self.available_voices = voices

            if voices:
                # Try to find a more natural female voice (often better quality)
                female_voice = None
                for voice in voices:
                    if (
                        getattr(voice, "gender", None) == "female"
                        or "female" in voice.name.lower()
                        or "zira" in voice.name.lower()
                    ):
                        female_voice = voice
                        break

                # If found a female voice, use it, otherwise use the first available voice
                if female_voice:
                    self.engine.setProperty("voice", female_voice.id)
                    print(f"Using voice: {female_voice.name}")
                else:
                    # Try to find the best available voice
                    best_voice = None
                    for voice in voices:
                        # Look for high-quality voices like David, Mark, or Samantha
                        if any(
                            name in voice.name.lower()
                            for name in ["david", "mark", "samantha", "alex"]
                        ):
                            best_voice = voice
                            break

                    if best_voice:
                        self.engine.setProperty("voice", best_voice.id)
                        print(f"Using voice: {best_voice.name}")
                    else:
                        # Default to first voice
                        self.engine.setProperty("voice", voices[0].id)
                        print(f"Using default voice: {voices[0].name}")

            # Connect to the engine's events
            self.engine.connect("finished-utterance", self._on_speech_finished)

            self.logger.info("Text-to-speech engine initialized successfully")

        except Exception as e:  # pragma: no cover - depends on system voices
            self.logger.warning(f"Failed to initialize text-to-speech engine: {e}")
            self.engine = None

    def _on_speech_finished(self, name, completed):
        """Callback when speech is finished"""
        self.is_speaking = False
        if self.on_speech_complete:
            self.on_speech_complete()

    def is_available(self) -> bool:
        """Check if TTS is available"""
        return HAS_TTS and self.engine is not None

    def speak(self, text: str) -> bool:
        """Speak the given text"""
        if not self.is_available():
            self.logger.info("Text-to-speech not available")
            return False

        if not text or not text.strip():
            self.logger.warning("No text provided for speech")
            return False

        # Stop any current speech first (outside of lock to avoid reentrancy deadlock)
        self.stop()

        try:
            # Limit text length for performance
            text = text.strip()[: self.MAX_TEXT_LENGTH]  # Limit to 1000 chars

            with self._lock:
                self._notified = False
                self.is_speaking = True
                self._cancel_requested = False
                # Enqueue say command for worker thread
                self._queue.put(("say", text))
            return True

        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {e}")
            with self._lock:
                self.is_speaking = False
            return False

    def _worker_loop(self):
        """Worker loop that serializes all pyttsx3 operations."""
        while True:
            try:
                cmd = self._queue.get()
                if not cmd:
                    continue
                action = cmd[0]
                if action == "say":
                    text = cmd[1]
                    try:
                        # Queue the utterance
                        engine = self.engine
                        if engine is None:
                            # Engine not available; finalize state and continue
                            with self._lock:
                                self.is_speaking = False
                                self._cancel_requested = False
                                if self.on_speech_complete and not self._notified:
                                    self._notified = True
                                    try:
                                        self.on_speech_complete()
                                    except Exception as e:
                                        self.logger.error(f"Error invoking on_speech_complete: {e}")
                            continue
                        engine.say(text)
                        # Start a non-blocking loop so we can react to stop requests immediately
                        try:
                            engine.startLoop(False)
                        except Exception:
                            # startLoop may raise if already started; continue to iterate
                            pass

                        while True:
                            # Check for stop requests without blocking
                            try:
                                inner_cmd = self._queue.get_nowait()
                                if inner_cmd and inner_cmd[0] == "stop":
                                    self._cancel_requested = True
                            except Empty:
                                pass

                            if self._cancel_requested:
                                try:
                                    engine.stop()
                                except Exception as e:
                                    self.logger.error(f"Error stopping engine in iterate loop: {e}")

                            # Iterate the engine loop once
                            try:
                                engine.iterate()
                            except Exception:
                                # Break on any driver loop errors
                                break

                            # Exit if engine finished speaking
                            try:
                                busy = engine.isBusy()
                            except Exception:
                                busy = False
                            if not busy:
                                break

                            time.sleep(0.01)

                        # Ensure loop is ended
                        try:
                            engine.endLoop()
                        except Exception:
                            pass

                    except Exception as e:
                        self.logger.error(f"Error in speech thread: {e}")
                    finally:
                        with self._lock:
                            self.is_speaking = False
                            self._cancel_requested = False
                            if self.on_speech_complete and not self._notified:
                                self._notified = True
                                try:
                                    self.on_speech_complete()
                                except Exception as e:
                                    self.logger.error(f"Error invoking on_speech_complete: {e}")
                elif action == "stop":
                    try:
                        self._cancel_requested = True
                        engine = self.engine
                        if engine is not None:
                            # If loop is active, stop will end current utterance
                            engine.stop()
                    except Exception as e:
                        self.logger.error(f"Error with engine.stop() in worker: {e}")
                    finally:
                        with self._lock:
                            self.is_speaking = False
                            if self.on_speech_complete and not self._notified:
                                self._notified = True
                                try:
                                    self.on_speech_complete()
                                except Exception as e:
                                    self.logger.error(f"Error invoking on_speech_complete: {e}")
                elif action == "shutdown":
                    # Reserved for future cleanup
                    break
            except Exception as e:
                self.logger.error(f"Worker loop error: {e}")

    def stop(self):
        """Stop current speech more forcefully"""
        with self._lock:
            if not self.is_speaking:
                return True
            self._stopping = True
            try:
                # Drain any pending commands so stop is processed ASAP
                try:
                    while True:
                        self._queue.get_nowait()
                except Empty:
                    pass
                # Ask worker to stop; it will serialize against any ongoing runAndWait
                self._queue.put(("stop",))
                return True
            finally:
                self._stopping = False
