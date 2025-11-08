from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .config_validator import validate_config


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
        self.default_path = (
            default_path or Path(__file__).resolve().parents[1] / "config" / "default.yaml"
        )
        self.user_path = user_path
        self.runtime_overrides = runtime_overrides or {}

    def load(self, validate: bool = True) -> Dict[str, Any]:
        """
        Load and merge configuration.

        Args:
            validate: Run validation on final config (default: True)

        Returns:
            Merged configuration dictionary
        """
        default_cfg = load_yaml(self.default_path)
        user_cfg = load_yaml(self.user_path) if self.user_path else {}
        merged = _deep_merge(default_cfg, user_cfg)
        if self.runtime_overrides:
            merged = _deep_merge(merged, self.runtime_overrides)

        # Validate configuration
        if validate:
            # Check if validation should be strict
            strict = os.getenv("MEMORIC_STRICT_CONFIG", "false").lower() == "true"

            result = validate_config(merged, strict=strict)

            # Log validation results
            if result.errors:
                import logging
                logger = logging.getLogger(__name__)
                for error in result.errors:
                    logger.error(f"Config error: {error}")

                # Raise on errors
                if strict or not result.is_valid:
                    error_list = "\n  ".join(result.errors)
                    raise ValueError(f"Configuration validation failed:\n  {error_list}")

            if result.warnings:
                import logging
                logger = logging.getLogger(__name__)
                for warning in result.warnings:
                    logger.warning(f"Config warning: {warning}")

        return merged
