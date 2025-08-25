import json
import os
from dataclasses import dataclass
from typing import Any

import dotenv

# Load .env from bundle directory when frozen, otherwise from CWD
if getattr(__import__("sys"), 'frozen', False):
    import sys as _sys

    _bundle_dir = os.path.dirname(_sys.executable)
    _dotenv_path = os.path.join(_bundle_dir, '.env')
    dotenv.load_dotenv(_dotenv_path)
else:
    dotenv.load_dotenv()

CONFIG_FILE = "settings.json"


@dataclass
class Config:
    """Application configuration"""

    API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-1.5-flash")
    BASE_URL: str = os.getenv("BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

    MAX_DEFINITION_LENGTH: int = int(os.getenv("MAX_DEFINITION_LENGTH", 50))
    POPUP_WIDTH: int = 400
    COPY_ATTEMPTS: int = 3
    COPY_DELAY: float = 0.1
    FONT_SIZE: int = 11
    FONT_FAMILY: str = "Segoe UI"

    # UI Configuration
    WINDOW_WIDTH: int = 800
    WINDOW_HEIGHT: int = 600
    WINDOW_TITLE: str = "AI Wand"
    PRIMARY_COLOR: str = "#444444"
    SECONDARY_COLOR: str = "#4CAF50"
    INACTIVE_COLOR: str = "#9E9E9E"
    ERROR_COLOR: str = "#F44336"
    BACKGROUND_COLOR: str = "#F5F5F7"
    CARD_BACKGROUND: str = "#FFFFFF"
    BORDER_RADIUS: int = 8
    ANIMATION_DURATION: int = 300
    ICON_SIZE: int = 24
    PADDING: int = 15
    LOG_MAX_LINES: int = 1000

    # Dark mode
    DARK_PRIMARY_COLOR: str = "#444444"
    DARK_SECONDARY_COLOR: str = "#4CAF50"
    DARK_BACKGROUND_COLOR: str = "#212121"
    DARK_CARD_BACKGROUND: str = "#333333"
    DARK_TEXT_COLOR: str = "#FFFFFF"
    DARK_INACTIVE_COLOR: str = "#757575"

    def to_dict(self) -> dict[str, Any]:
        return {
            key: getattr(self, key)
            for key in self.__annotations__
            if isinstance(getattr(self, key), (str, int, float))
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        # Normalize keys (case-insensitive) and support legacy spellings
        normalized = {k.lower(): v for k, v in data.items()}
        aliases = {
            "max_definition_length": "MAX_DEFINITION_LENGTH",
            "maxdefinitionlength": "MAX_DEFINITION_LENGTH",
            "max_definition_len": "MAX_DEFINITION_LENGTH",
        }

        resolved: dict[str, Any] = {}
        for field, typ in cls.__annotations__.items():
            key_lower = field.lower()
            val = None
            if key_lower in normalized:
                val = normalized[key_lower]
            else:
                # Try alias
                for alias_lower, target in aliases.items():
                    if target == field and alias_lower in normalized:
                        val = normalized[alias_lower]
                        break
            if val is not None:
                try:
                    if typ is int:
                        resolved[field] = int(val)
                    elif typ is float:
                        resolved[field] = float(val)
                    elif typ is str:
                        resolved[field] = str(val)
                    else:
                        resolved[field] = val
                except Exception:
                    resolved[field] = val

        return cls(**resolved)

    def __post_init__(self):
        # Defensive type coercion for runtime-created instances
        try:
            self.MAX_DEFINITION_LENGTH = int(self.MAX_DEFINITION_LENGTH)
            self.POPUP_WIDTH = int(self.POPUP_WIDTH)
            self.COPY_ATTEMPTS = int(self.COPY_ATTEMPTS)
            self.COPY_DELAY = float(self.COPY_DELAY)
            self.FONT_SIZE = int(self.FONT_SIZE)
        except Exception:
            pass

    def save(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls, file_path: str) -> "Config":
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                return cls.from_dict(data)
        return cls()
