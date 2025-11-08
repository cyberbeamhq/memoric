"""
Simple Memory Management for AI Agents

This is the main entry point - everything you need in one class.

Example:
    from memoric import Memory

    # Initialize
    memory = Memory()

    # Save memories
    memory.add("User prefers email over phone calls")
    memory.add("User's favorite color is blue")

    # Search by meaning
    results = memory.search("How does user like to communicate?")
    # Returns: ["User prefers email over phone calls"]

    # Get formatted context for AI
    context = memory.get_context("User asked about communication preferences")
    # Returns: Formatted string ready for LLM
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os

from .db.postgres_connector import PostgresConnector
from .core.semantic_search import SemanticSearchEngine, OpenAIEmbedding, LocalEmbedding
from .providers.vector_stores import PineconeVectorStore, QdrantVectorStore, InMemoryVectorStore
from .utils.logger import get_logger

logger = get_logger(__name__)


class Memory:
    """
    Simple memory management for AI agents.

    Handles everything: storage, embeddings, semantic search, and context retrieval.
    """

    def __init__(
        self,
        *,
        user_id: str = "default",
        db_path: Optional[str] = None,
        vector_store: Optional[str] = None,
        vector_store_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize memory system.

        Args:
            user_id: Unique identifier for this user/agent (for memory isolation)
            db_path: Path to SQLite database (default: ./memoric.db)
            vector_store: Vector store type ("pinecone", "qdrant", or None for in-memory)
            vector_store_config: Configuration for vector store (API keys, etc.)

        Examples:
            # Simple (in-memory, for development)
            memory = Memory()

            # Production with Pinecone
            memory = Memory(
                user_id="agent_123",
                vector_store="pinecone",
                vector_store_config={
                    "api_key": "your-key",
                    "environment": "us-east-1",
                    "index_name": "memories"
                }
            )
        """
        self.user_id = user_id
        self.db_path = db_path or os.environ.get("MEMORIC_DB_PATH", "memoric.db")

        # Initialize PostgreSQL/SQLite
        self.db = PostgresConnector(dsn=f"sqlite:///{self.db_path}")
        self.db.create_schema_if_not_exists()

        # Initialize vector store
        self._vector_store = self._init_vector_store(vector_store, vector_store_config or {})

        # Initialize semantic search
        self._semantic = SemanticSearchEngine(
            db=self.db,
            vector_store=self._vector_store,
            embedding_provider=self._init_embedder()
        )

        logger.info(
            f"Memory initialized for user '{user_id}'",
            extra={"vector_store": vector_store or "in-memory"}
        )

    def _init_vector_store(self, store_type: Optional[str], config: Dict[str, Any]) -> Any:
        """Initialize vector store based on type."""
        if store_type == "pinecone":
            return PineconeVectorStore(**config)
        elif store_type == "qdrant":
            return QdrantVectorStore(**config)
        else:
            # Default: in-memory (good for development/testing)
            logger.info("Using in-memory vector store (not for production)")
            return InMemoryVectorStore()

    def _init_embedder(self) -> Any:
        """Initialize embedding provider (auto-detect based on API keys)."""
        if os.environ.get("OPENAI_API_KEY"):
            return OpenAIEmbedding()
        else:
            logger.warning("No OPENAI_API_KEY found, using local embeddings (lower quality)")
            return LocalEmbedding()

    def add(
        self,
        content: str,
        *,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: str = "medium",
    ) -> int:
        """
        Add a memory.

        Args:
            content: What to remember (text)
            thread_id: Optional conversation thread ID
            metadata: Optional metadata (tags, etc.)
            importance: Importance level ("low", "medium", "high", "critical")

        Returns:
            Memory ID

        Example:
            memory_id = memory.add(
                "User mentioned they have a dog named Max",
                thread_id="conv_123",
                importance="high"
            )
        """
        # Prepare metadata
        full_metadata = {
            "importance": importance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }

        # Save to database
        memory_id = self.db.insert_memory(
            user_id=self.user_id,
            content=content,
            thread_id=thread_id,
            metadata=full_metadata
        )

        # Generate and store embedding (async in background)
        try:
            embed_metadata = {
                "user_id": self.user_id,
                "thread_id": thread_id,
                "content_preview": content[:100]
            }
            self._semantic.embed_and_store(memory_id, content, metadata=embed_metadata)
        except Exception as e:
            logger.warning(f"Failed to generate embedding (search may be limited): {e}")

        logger.debug(f"Added memory {memory_id}: '{content[:50]}...'")
        return memory_id

    def search(
        self,
        query: str,
        *,
        thread_id: Optional[str] = None,
        limit: int = 5,
        min_relevance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by meaning.

        Uses hybrid search (semantic similarity + keyword matching + recency).

        Args:
            query: What to search for (natural language)
            thread_id: Optional filter by conversation thread
            limit: Maximum results to return
            min_relevance: Minimum relevance score (0.0 to 1.0)

        Returns:
            List of relevant memories, sorted by relevance

        Example:
            results = memory.search("What pets does the user have?", limit=3)
            for mem in results:
                print(f"[{mem['_score']:.2f}] {mem['content']}")
        """
        # Use semantic search with hybrid scoring
        results = self._semantic.search(
            query=query,
            user_id=self.user_id,
            thread_id=thread_id,
            top_k=limit,
            hybrid_alpha=0.6,  # 60% semantic, 40% keyword
            min_similarity=min_relevance
        )

        # Add readable score
        for result in results:
            result['_score'] = result.get('_hybrid_score', 0.0)

        return results

    def get_context(
        self,
        query: str,
        *,
        thread_id: Optional[str] = None,
        max_memories: int = 10,
        format: str = "text",
    ) -> str | Dict[str, Any]:
        """
        Get formatted context for AI consumption.

        This is what you pass to your LLM as context/history.

        Args:
            query: Current user query or task
            thread_id: Current conversation thread
            max_memories: Maximum memories to include
            format: Output format ("text" or "json")

        Returns:
            Formatted context string (or dict if format="json")

        Example:
            context = memory.get_context(
                "User asked about their dog",
                thread_id="conv_123"
            )

            # Pass to your LLM:
            response = llm.complete(f"{context}\n\nUser: {user_message}")
        """
        # Get relevant memories
        memories = self.search(query, thread_id=thread_id, limit=max_memories)

        if format == "json":
            return {
                "query": query,
                "memories": [
                    {
                        "content": m["content"],
                        "relevance": m.get("_score", 0),
                        "timestamp": m.get("created_at"),
                        "thread_id": m.get("thread_id"),
                    }
                    for m in memories
                ],
                "total": len(memories),
            }
        else:
            # Format as text for LLM
            if not memories:
                return "No relevant memories found."

            lines = ["=== RELEVANT CONTEXT ===\n"]
            for i, mem in enumerate(memories, 1):
                score = mem.get("_score", 0)
                content = mem["content"]
                timestamp = mem.get("created_at", "")
                lines.append(f"{i}. [{score:.2f}] {content}")
                if timestamp:
                    lines.append(f"   (from {timestamp})")

            lines.append("\n=== END CONTEXT ===")
            return "\n".join(lines)

    def get_thread(self, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get full conversation thread in chronological order.

        Args:
            thread_id: Thread ID
            limit: Maximum messages

        Returns:
            List of memories in chronological order

        Example:
            history = memory.get_thread("conv_123")
            for msg in history:
                print(f"{msg['metadata']['role']}: {msg['content']}")
        """
        memories = self.db.get_memories(
            user_id=self.user_id,
            thread_id=thread_id,
            limit=limit
        )

        # Sort by timestamp
        memories.sort(key=lambda m: m.get("created_at") or datetime.min.replace(tzinfo=timezone.utc))
        return memories

    def delete(self, memory_id: int) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        success = self.db.delete_memory(memory_id)
        if success:
            # Also delete from vector store
            try:
                self._vector_store.delete(str(memory_id))
            except Exception as e:
                logger.warning(f"Failed to delete from vector store: {e}")
        return success

    def clear(self, thread_id: Optional[str] = None) -> int:
        """
        Clear memories for this user (optionally filtered by thread).

        Args:
            thread_id: If provided, only clear this thread

        Returns:
            Number of memories deleted

        Example:
            # Clear entire user's memory
            count = memory.clear()

            # Clear just one conversation
            count = memory.clear(thread_id="conv_123")
        """
        memories = self.db.get_memories(
            user_id=self.user_id,
            thread_id=thread_id,
            limit=10000
        )

        count = 0
        for mem in memories:
            if self.delete(mem["id"]):
                count += 1

        logger.info(f"Cleared {count} memories for user '{self.user_id}'")
        return count

    def stats(self) -> Dict[str, Any]:
        """
        Get memory statistics for this user.

        Returns:
            Dictionary with stats (total memories, threads, etc.)

        Example:
            stats = memory.stats()
            print(f"Total memories: {stats['total_memories']}")
        """
        memories = self.db.get_memories(user_id=self.user_id, limit=100000)

        threads = set(m.get("thread_id") for m in memories if m.get("thread_id"))

        return {
            "user_id": self.user_id,
            "total_memories": len(memories),
            "total_threads": len(threads),
            "vector_store": type(self._vector_store).__name__,
            "embedding_provider": type(self._semantic.embedder).__name__,
        }


__all__ = ["Memory"]
