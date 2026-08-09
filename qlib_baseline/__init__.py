"""Lightweight engineering foundation for the qlib-baseline research project."""

from .settings import ProjectSettings, SettingsError, load_settings

__all__ = ["ProjectSettings", "SettingsError", "load_settings"]
__version__ = "0.1.0"
