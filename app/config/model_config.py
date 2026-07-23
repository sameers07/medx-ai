"""Loads app/config/config.yaml — ML/product config (model, training, explainability, reports)."""
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


config = load_config()
