"""
LlamaIndex integration for Memoric.

This module provides integration with LlamaIndex, allowing Memoric
to be used as a storage backend for LlamaIndex applications.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.memory_manager import Memoric


class MemoricStorageContext:
    """
    Storage context adapter for LlamaIndex.

    This class wraps Memoric to provide a LlamaIndex-compatible
    storage interface.
    """

    def __init__(self, memoric: Memoric, user_id: Optional[str] = None):
        """
        Initialize MemoricStorageContext.

        Args:
            memoric: Memoric instance to wrap
            user_id: Default user ID for operations
        """
        self.memoric = memoric
        self.user_id = user_id or "llamaindex-default"

    def store_document(
        self,
        document: Any,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Store a document in Memoric.

        Args:
            document: Document object from LlamaIndex
            thread_id: Optional thread identifier
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        # Extract text from document
        if hasattr(document, "text"):
            content = document.text
        elif hasattr(document, "get_content"):
            content = document.get_content()
        else:
            content = str(document)

        # Extract document metadata
        doc_metadata = metadata or {}
        if hasattr(document, "metadata"):
            doc_metadata.update(document.metadata)

        # Store in Memoric
        return self.memoric.save(
            user_id=self.user_id,
            thread_id=thread_id,
            content=content,
            metadata=doc_metadata,
        )

    def retrieve_documents(
        self,
        query: Optional[str] = None,
        thread_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from Memoric.

        Args:
            query: Search query
            thread_id: Thread filter
            top_k: Maximum results

        Returns:
            List of memory dictionaries
        """
        return self.memoric.retrieve(
            user_id=self.user_id,
            thread_id=thread_id,
            query=query,
            top_k=top_k,
        )

    def as_dict(self) -> Dict[str, Any]:
        """Get storage context configuration."""
        return {
            "type": "memoric",
            "user_id": self.user_id,
        }


# Convenience function
def create_storage_context(
    memoric: Optional[Memoric] = None,
    user_id: Optional[str] = None,
) -> MemoricStorageContext:
    """
    Create a Memoric storage context for LlamaIndex.

    Args:
        memoric: Memoric instance (creates new if None)
        user_id: Default user ID

    Returns:
        MemoricStorageContext instance

    Example:
        >>> from memoric.integrations.llamaindex import create_storage_context
        >>> storage = create_storage_context(user_id="my-app")
        >>> # Use with LlamaIndex
    """
    if memoric is None:
        from ..core.memory_manager import Memoric
        memoric = Memoric()

    return MemoricStorageContext(memoric=memoric, user_id=user_id)
