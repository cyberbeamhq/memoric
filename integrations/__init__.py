"""
Memoric integrations with popular AI frameworks.

Available integrations:
- LangChain: Drop-in memory replacement for LangChain chains
"""

from __future__ import annotations

# LangChain integration
try:
    from .langchain_adapter import (
        MemoricChatMemory,
        MemoricConversationBufferMemory,
        create_langchain_memory,
    )

    __all__ = [
        "MemoricChatMemory",
        "MemoricConversationBufferMemory",
        "create_langchain_memory",
    ]
except ImportError:
    # LangChain not installed
    __all__ = []
