# ─── core/config.py ───
"""Application configuration loader.

Loads YAML configuration files and merges them with environment settings.
"""

from pathlib import Path
from typing import Any

import yaml

from .settings import settings


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML configuration file from the config/ directory."""
    filepath = _CONFIG_DIR / filename
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_app_config() -> dict[str, Any]:
    """Return merged application configuration."""
    return load_yaml("app.yaml")


def get_models_config() -> dict[str, Any]:
    """Return model configuration."""
    return load_yaml("models.yaml")
