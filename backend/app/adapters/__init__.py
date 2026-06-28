"""Web adapters for different frontend platforms."""

from app.adapters.web_adapter import (
    convert_universal_to_web,
    convert_text_to_web,
)

__all__ = [
    "convert_universal_to_web",
    "convert_text_to_web",
]