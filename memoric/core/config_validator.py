"""
Configuration Validator - Catch config errors early with clear messages.

Validates Memoric configuration to help developers catch mistakes before runtime.
Provides clear, actionable error messages when configuration is invalid.

Example:
    from memoric.core.config_validator import validate_config, ValidationResult

    config = load_config("my_config.yaml")
    result = validate_config(config)

    if not result.is_valid:
        for error in result.errors:
            print(f"Error: {error}")
        for warning in result.warnings:
            print(f"Warning: {warning}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add an info message."""
        self.info.append(message)


class ConfigValidator:
    """Validator for Memoric configuration."""

    # Known valid configuration keys
    VALID_SECTIONS = {
        "database",
        "storage",
        "policies",
        "metadata",
        "recall",
        "scoring",
        "clustering",
        "privacy",
        "observability",
        "api",
        "authentication",
    }

    # Required configuration keys
    REQUIRED_SECTIONS = {
        "database",  # Must have database config
    }

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration.

        Args:
            config: Configuration dictionary

        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult(is_valid=True)

        # Check required sections
        self._validate_required_sections(config, result)

        # Check unknown sections
        self._check_unknown_sections(config, result)

        # Validate individual sections
        self._validate_database(config.get("database", {}), result)
        self._validate_storage(config.get("storage", {}), result)
        self._validate_policies(config.get("policies", {}), result)
        self._validate_privacy(config.get("privacy", {}), result)
        self._validate_scoring(config.get("scoring", {}), result)

        # Log results
        if result.errors:
            logger.error(f"Config validation failed with {len(result.errors)} errors")
        elif result.warnings:
            logger.warning(f"Config has {len(result.warnings)} warnings")
        else:
            logger.info("Config validation passed")

        # In strict mode, warnings become errors
        if self.strict and result.warnings:
            result.errors.extend(result.warnings)
            result.warnings.clear()
            result.is_valid = False

        return result

    def _validate_required_sections(
        self, config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Check that required sections exist."""
        for section in self.REQUIRED_SECTIONS:
            if section not in config:
                result.add_error(
                    f"Missing required config section: '{section}'. "
                    f"Add '{section}:' to your config file."
                )

    def _check_unknown_sections(
        self, config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Warn about unknown configuration sections."""
        unknown = set(config.keys()) - self.VALID_SECTIONS
        for key in unknown:
            result.add_warning(
                f"Unknown config section: '{key}'. "
                f"This might be a typo. Valid sections: {', '.join(sorted(self.VALID_SECTIONS))}"
            )

    def _validate_database(
        self, db_config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate database configuration."""
        if not db_config:
            result.add_info("Using default SQLite database (memoric_dev.db)")
            return

        # Check DSN format
        dsn = db_config.get("dsn")
        if dsn:
            if isinstance(dsn, str):
                if not any(dsn.startswith(prefix) for prefix in ["sqlite:", "postgresql:"]):
                    result.add_error(
                        f"Invalid database DSN: '{dsn}'. "
                        f"Must start with 'sqlite:' or 'postgresql:'"
                    )
            else:
                result.add_error(
                    f"Database DSN must be a string, got {type(dsn).__name__}"
                )

    def _validate_storage(
        self, storage_config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate storage configuration."""
        if not storage_config:
            return

        tiers = storage_config.get("tiers", [])
        if not isinstance(tiers, list):
            result.add_error("storage.tiers must be a list")
            return

        tier_names: Set[str] = set()
        for i, tier in enumerate(tiers):
            if not isinstance(tier, dict):
                result.add_error(f"Tier {i} must be a dictionary")
                continue

            # Check required fields
            name = tier.get("name")
            if not name:
                result.add_error(f"Tier {i} missing required field: 'name'")
                continue

            # Check for duplicate names
            if name in tier_names:
                result.add_error(f"Duplicate tier name: '{name}'")
            tier_names.add(name)

            # Validate expiry_days if present
            if "expiry_days" in tier:
                expiry = tier["expiry_days"]
                if not isinstance(expiry, (int, float)) or expiry < 0:
                    result.add_error(
                        f"Tier '{name}': expiry_days must be a positive number"
                    )

    def _validate_policies(
        self, policies_config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate policies configuration."""
        if not policies_config:
            return

        # Check for deprecated policy names
        if "write_policies" in policies_config:
            result.add_error(
                "Deprecated config key: 'policies.write_policies'. "
                "Use 'policies.write' instead."
            )

        if "migration_policies" in policies_config:
            result.add_warning(
                "policies.migration_policies is not implemented. "
                "Use storage.tiers[].expiry_days for automatic migration."
            )

        if "trimming_policies" in policies_config:
            result.add_warning(
                "policies.trimming_policies is not implemented. "
                "Use storage.tiers[].trim.max_chars instead."
            )

        # Validate write policies
        write_policies = policies_config.get("write", [])
        if write_policies and not isinstance(write_policies, list):
            result.add_error("policies.write must be a list")

    def _validate_privacy(
        self, privacy_config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate privacy configuration."""
        if not privacy_config:
            return

        # Check encryption
        encrypt = privacy_config.get("encrypt_content", False)
        encryption_key = privacy_config.get("encryption_key")

        if encrypt and not encryption_key:
            import os
            if not os.getenv("MEMORIC_ENCRYPTION_KEY"):
                result.add_warning(
                    "encrypt_content is enabled but no encryption_key provided. "
                    "Set encryption_key in config or MEMORIC_ENCRYPTION_KEY environment variable. "
                    "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )

        # Check user_isolation
        user_isolation = privacy_config.get("user_isolation")
        if user_isolation is not None and not isinstance(user_isolation, bool):
            result.add_error(
                f"privacy.user_isolation must be boolean, got {type(user_isolation).__name__}"
            )

    def _validate_scoring(
        self, scoring_config: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate scoring configuration."""
        if not scoring_config:
            return

        weights = scoring_config.get("weights", {})
        if weights:
            # Check weight values sum to ~1.0
            weight_sum = sum(
                v for v in weights.values()
                if isinstance(v, (int, float))
            )

            if abs(weight_sum - 1.0) > 0.15:  # Allow 15% tolerance
                result.add_warning(
                    f"Scoring weights sum to {weight_sum:.2f}, should be close to 1.0. "
                    f"Current weights: {weights}"
                )

            # Check individual weights are valid
            for key, value in weights.items():
                if not isinstance(value, (int, float)):
                    result.add_error(
                        f"scoring.weights.{key} must be a number, got {type(value).__name__}"
                    )
                elif value < 0 or value > 1:
                    result.add_warning(
                        f"scoring.weights.{key} = {value} is outside normal range [0, 1]"
                    )


def validate_config(
    config: Dict[str, Any],
    strict: bool = False,
    raise_on_error: bool = False,
) -> ValidationResult:
    """
    Validate Memoric configuration.

    Args:
        config: Configuration dictionary
        strict: Treat warnings as errors
        raise_on_error: Raise ValueError if validation fails

    Returns:
        ValidationResult

    Raises:
        ValueError: If raise_on_error=True and validation fails
    """
    validator = ConfigValidator(strict=strict)
    result = validator.validate(config)

    if raise_on_error and not result.is_valid:
        error_msg = "\n".join([
            "Configuration validation failed:",
            *[f"  ERROR: {e}" for e in result.errors],
            *[f"  WARNING: {w}" for w in result.warnings],
        ])
        raise ValueError(error_msg)

    return result


__all__ = ["ConfigValidator", "ValidationResult", "validate_config"]
