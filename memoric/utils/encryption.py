"""
Content encryption utilities using Fernet symmetric encryption.

This module provides field-level encryption for sensitive data storage.
Encryption keys should be stored in a secure key management system (KMS)
like AWS KMS, HashiCorp Vault, or environment variables for development.

Example:
    from memoric.utils.encryption import EncryptionService

    # Initialize with key
    encryptor = EncryptionService(encryption_key="your-key-here")

    # Encrypt data
    encrypted = encryptor.encrypt("sensitive data")

    # Decrypt data
    original = encryptor.decrypt(encrypted)
"""

from __future__ import annotations

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting content using Fernet symmetric encryption.

    Fernet guarantees that a message encrypted using it cannot be manipulated or read
    without the key. It uses AES 128 in CBC mode with PKCS7 padding, and HMAC using SHA256.

    Attributes:
        enabled: Whether encryption is enabled
        cipher: Fernet cipher instance (None if encryption disabled)
    """

    def __init__(self, *, encryption_key: Optional[str] = None, enabled: bool = True):
        """
        Initialize the encryption service.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, tries to load from
                          MEMORIC_ENCRYPTION_KEY environment variable.
            enabled: Whether encryption is enabled. If False, data passes through unchanged.

        Raises:
            ValueError: If encryption is enabled but no valid key provided.
        """
        self.enabled = enabled

        if not self.enabled:
            self.cipher = None
            logger.warning("Encryption is DISABLED. Data will be stored in plaintext.")
            return

        # Try to get key from parameter or environment
        key = encryption_key or os.getenv("MEMORIC_ENCRYPTION_KEY")

        if not key:
            logger.error(
                "Encryption enabled but no key provided. "
                "Set MEMORIC_ENCRYPTION_KEY environment variable or pass encryption_key parameter."
            )
            raise ValueError(
                "Encryption key required when encryption is enabled. "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            # Validate key format
            key_bytes = key.encode() if isinstance(key, str) else key
            self.cipher = Fernet(key_bytes)
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string (or original if encryption disabled)

        Raises:
            ValueError: If plaintext is None
        """
        if plaintext is None:
            raise ValueError("Cannot encrypt None value")

        if not self.enabled or self.cipher is None:
            return plaintext

        try:
            plaintext_bytes = plaintext.encode("utf-8")
            encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
            # Return base64-encoded string for database storage
            return base64.b64encode(encrypted_bytes).decode("ascii")
        except Exception as e:
            logger.error(f"Encryption failed: {e}", extra={"error": str(e)})
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Original plaintext string (or ciphertext if encryption disabled)

        Raises:
            ValueError: If ciphertext is None or invalid
        """
        if ciphertext is None:
            raise ValueError("Cannot decrypt None value")

        if not self.enabled or self.cipher is None:
            return ciphertext

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(ciphertext.encode("ascii"))
            plaintext_bytes = self.cipher.decrypt(encrypted_bytes)
            return plaintext_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or wrong key")
            raise ValueError("Decryption failed: Invalid ciphertext or wrong key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}", extra={"error": str(e)})
            raise

    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing data to encrypt
            fields: List of field names to encrypt

        Returns:
            New dictionary with specified fields encrypted

        Example:
            >>> data = {"content": "secret", "user_id": "123"}
            >>> encrypted = encryptor.encrypt_dict(data, ["content"])
            >>> encrypted["content"]  # Encrypted
            >>> encrypted["user_id"]  # Unchanged
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field] is not None:
                result[field] = self.encrypt(str(result[field]))
        return result

    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt

        Returns:
            New dictionary with specified fields decrypted
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field] is not None:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except ValueError:
                    # Field might not be encrypted (migration scenario)
                    logger.warning(
                        f"Failed to decrypt field '{field}', using as-is",
                        extra={"field": field},
                    )
        return result

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key suitable for use with EncryptionService

        Example:
            >>> key = EncryptionService.generate_key()
            >>> print(f"MEMORIC_ENCRYPTION_KEY={key}")
            >>> # Save this key securely!
        """
        return Fernet.generate_key().decode("ascii")


# Convenience function for generating keys
def generate_encryption_key() -> str:
    """
    Generate a new encryption key.

    Returns:
        Base64-encoded Fernet key

    Example:
        python -c "from memoric.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
    """
    return EncryptionService.generate_key()


__all__ = ["EncryptionService", "generate_encryption_key"]
