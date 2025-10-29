"""
Core memory management components.

This module provides the main classes for using Memoric:
- MemoryManager: Main interface for memory operations
- Retriever: Memory retrieval with scope support
- PolicyExecutor: Policy execution engine
"""

from __future__ import annotations

# Use relative imports (standard for package structure)
from .memory_manager import Memoric as MemoryManager
from .retriever import Retriever
from .policy_executor import PolicyExecutor
from .clustering import SimpleClustering, Cluster

__all__ = [
    "MemoryManager",
    "Retriever",
    "PolicyExecutor",
    "SimpleClustering",
    "Cluster",
]
