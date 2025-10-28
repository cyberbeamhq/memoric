from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base, returning a new dict.

    - Lists are replaced by override lists
    - Scalars are replaced by override values
    - Dicts are merged recursively
    """
    result: Dict[str, Any] = dict(base)
    for key, override_value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(result[key], override_value)
        else:
            result[key] = override_value
    return result


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML at {path} must be a mapping at the top level")
        return data


class ConfigLoader:
    """Loads and merges configuration from default YAML, user YAML, and runtime overrides."""

    def __init__(
        self,
        default_path: Optional[Path] = None,
        user_path: Optional[Path] = None,
        runtime_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.default_path = default_path or Path(__file__).resolve().parents[1] / "config" / "default.yaml"
        self.user_path = user_path
        self.runtime_overrides = runtime_overrides or {}

    def load(self) -> Dict[str, Any]:
        default_cfg = load_yaml(self.default_path)
        user_cfg = load_yaml(self.user_path) if self.user_path else {}
        merged = _deep_merge(default_cfg, user_cfg)
        if self.runtime_overrides:
            merged = _deep_merge(merged, self.runtime_overrides)
        return merged


