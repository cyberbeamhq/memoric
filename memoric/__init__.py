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
from .core.policy_config import PolicyConfig, TierConfig, ScoringConfig, RetrievalConfig
from .core.context_assembler import ContextAssembler
from .db import PostgresConnector
from .agents import MetadataAgent
from .utils import (
    TextTrimmer,
    TextSummarizer,
    LLMSummarizer,
    ScoringEngine,
    ScoringWeights,
)

# LangChain integration (if available)
try:
    from .integrations.langchain.memory import MemoricMemory
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    MemoricMemory = None  # type: ignore
    _LANGCHAIN_AVAILABLE = False

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
    # New features
    "PolicyConfig",
    "TierConfig",
    "ScoringConfig",
    "RetrievalConfig",
    "ContextAssembler",
]

# Add MemoricMemory if LangChain is available
if _LANGCHAIN_AVAILABLE:
    __all__.append("MemoricMemory")

# CLI entry point (for console_scripts)
def cli_main():
    """Entry point for memoric CLI command."""
    from cli import main
    main()
