"""
Memoric - Simple Memory Management for AI Agents

Quick Start (Recommended):
    from memoric import Memory

    # Initialize
    memory = Memory(user_id="my_agent")

    # Save memories
    memory.add("User prefers email communication")

    # Search by meaning
    results = memory.search("How does user like to communicate?")

    # Get formatted context for AI
    context = memory.get_context("User asked about communication")

Advanced Usage (for custom needs):
    from memoric.core import MemoryManager, Retriever
    from memoric.providers import PineconeVectorStore, QdrantVectorStore
    from memoric.db import PostgresConnector

Configuration:
    See examples/ directory for common patterns.
"""

from __future__ import annotations

# Simple API (recommended for most users)
from .memory import Memory

# Legacy imports (backward compatibility)
from .core.memory_manager import Memoric
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
    # Simple API (recommended - start here!)
    "Memory",
    # Legacy (backward compatibility)
    "Memoric",
    "MemoryManager",
    # Advanced (for custom needs)
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
    from .cli import main
    main()
