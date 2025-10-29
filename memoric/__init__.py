"""
Memoric - A tiered, policy-driven memory management system.

Quick Start:
    from memoric import Memoric

    m = Memoric()
    m.save(user_id="user1", content="Meeting notes...")
    results = m.retrieve(user_id="user1", query="meetings")

Advanced Usage:
    from memoric.core import MemoryManager, Retriever
    from memoric.utils import LLMSummarizer, create_trimmer
    from memoric.db import PostgresConnector
    from memoric.agents import MetadataAgent

Configuration:
    See config/default_config.yaml for all available options.
"""

from __future__ import annotations

# Legacy import (backward compatibility)
from .core.memory_manager import Memoric

# Modern imports (recommended)
from .core import MemoryManager
from .core import Retriever, PolicyExecutor, SimpleClustering, Cluster
from .db import PostgresConnector
from .agents import MetadataAgent
from .utils import (
    TextTrimmer,
    TextSummarizer,
    LLMSummarizer,
    ScoringEngine,
    ScoringWeights,
)

__version__ = "0.1.0"

__all__ = [
    # Legacy (backward compatibility)
    "Memoric",
    # Modern API (recommended)
    "MemoryManager",
    "Retriever",
    "PolicyExecutor",
    "SimpleClustering",
    "Cluster",
    "PostgresConnector",
    "MetadataAgent",
    "TextTrimmer",
    "TextSummarizer",
    "LLMSummarizer",
    "ScoringEngine",
    "ScoringWeights",
]

# CLI entry point (for console_scripts)
def cli_main():
    """Entry point for memoric CLI command."""
    from cli import main
    main()
