"""
Agent implementations for metadata enrichment and processing.

Provides:
- MetadataAgent: OpenAI-powered metadata extraction
"""

from __future__ import annotations

# Use relative imports (standard for package structure)
from .metadata_agent import MetadataAgent

__all__ = [
    "MetadataAgent",
]
