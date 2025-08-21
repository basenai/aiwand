from enum import Enum


class AppState(Enum):
    """Application state enumeration shared across modules"""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PROCESSING = "processing"
