"""
Conversation Manager for AI Agents - DEPRECATED

⚠️ DEPRECATION WARNING:
This class is deprecated and will be removed in a future version.
Please use the simpler Memory class instead:

Old way (deprecated):
    from memoric.agents import ConversationManager
    manager = ConversationManager(agent_id="bot")
    manager.add_message(content="...", role="user")
    context = manager.get_context(query="...")

New way (recommended):
    from memoric import Memory
    memory = Memory(user_id="bot")
    memory.add("...")
    context = memory.get_context("...")

The new Memory class is simpler, faster, and easier to use.
See examples/simple.py for migration guide.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.memory_manager import Memoric
from ..core.hybrid_retriever import HybridRetriever
from .smart_summarizer import SmartSummarizer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """
    High-level conversation manager for AI agents.

    Provides simple API for storing messages and retrieving relevant context,
    with automatic optimization for AI agent use cases.
    """

    def __init__(
        self,
        *,
        agent_id: str,
        memoric: Optional[Memoric] = None,
        vector_store: Optional[Any] = None,
        enable_semantic_search: bool = True,
        enable_summarization: bool = True,
        default_strategy: str = "balanced",
        async_embeddings: bool = True,
    ):
        """
        Initialize conversation manager.

        Args:
            agent_id: Unique identifier for this AI agent
            memoric: Memoric instance (creates new if None)
            vector_store: Vector store provider (Pinecone, Qdrant, etc.)
            enable_semantic_search: Enable semantic/vector search
            enable_summarization: Enable smart summarization
            default_strategy: Default retrieval strategy
            async_embeddings: Generate embeddings asynchronously (non-blocking)
        """
        self.agent_id = agent_id
        self.memoric = memoric or Memoric()
        self.async_embeddings = async_embeddings

        # Ensure database is initialized
        self.memoric._ensure_initialized()

        # Initialize hybrid retriever with vector store
        self.retriever = HybridRetriever(
            db=self.memoric.db,
            vector_store=vector_store,
            enable_semantic=enable_semantic_search
        )

        # Initialize summarizer
        self.summarizer = SmartSummarizer() if enable_summarization else None

        self.default_strategy = default_strategy

        # Thread pool for async embedding generation
        if async_embeddings and enable_semantic_search:
            from concurrent.futures import ThreadPoolExecutor
            self._embedding_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embedding")
        else:
            self._embedding_executor = None

        # Deprecation warning
        import warnings
        warnings.warn(
            "ConversationManager is deprecated and will be removed in a future version. "
            "Please use the simpler Memory class instead: from memoric import Memory",
            DeprecationWarning,
            stacklevel=2
        )

        logger.info(
            f"Conversation manager initialized for agent '{agent_id}'",
            extra={
                'semantic_search': enable_semantic_search,
                'summarization': enable_summarization,
                'async_embeddings': async_embeddings,
            }
        )

    def add_message(
        self,
        *,
        content: str,
        role: str = "user",
        thread_id: Optional[str] = None,
        importance: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add a message to the conversation history.

        Args:
            content: Message content
            role: Message role ("user", "assistant", "system")
            thread_id: Conversation thread ID
            importance: Importance level ("low", "medium", "high", "critical")
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        # Merge metadata
        full_metadata = {
            "role": role,
            "importance": importance,
            **(metadata or {})
        }

        # Save to database
        memory_id = self.memoric.save(
            user_id=self.agent_id,
            content=content,
            thread_id=thread_id,
            metadata=full_metadata
        )

        logger.debug(
            f"Added message to thread {thread_id}",
            extra={
                'memory_id': memory_id,
                'role': role,
                'content_length': len(content),
            }
        )

        # Generate embedding for semantic search
        if self.retriever.semantic_enabled:
            metadata_for_embed = {
                "user_id": self.agent_id,
                "thread_id": thread_id,
                "content_preview": content[:100]
            }

            if self._embedding_executor:
                # Async: Submit to background thread (non-blocking)
                def embed_in_background():
                    try:
                        self.retriever.semantic.embed_and_store(
                            memory_id,
                            content,
                            metadata=metadata_for_embed
                        )
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding in background: {e}")

                self._embedding_executor.submit(embed_in_background)
            else:
                # Sync: Generate immediately (blocking)
                try:
                    self.retriever.semantic.embed_and_store(
                        memory_id,
                        content,
                        metadata=metadata_for_embed
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")

        return memory_id

    def get_context(
        self,
        *,
        query: str,
        thread_id: Optional[str] = None,
        max_tokens: int = 2000,
        strategy: Optional[str] = None,
        include_summary: bool = True,
    ) -> Dict[str, Any]:
        """
        Get relevant context for AI agent.

        This is the main method AI agents use to get conversation context
        before generating a response.

        Args:
            query: Current query or prompt
            thread_id: Current conversation thread
            max_tokens: Maximum tokens for context (for LLM context window)
            strategy: Retrieval strategy (uses default if None)
            include_summary: Include summarization for old messages

        Returns:
            Dict with 'text' (formatted context), 'memories' (raw), and 'metadata'
        """
        strategy = strategy or self.default_strategy

        # Retrieve relevant memories
        results = self.retriever.retrieve_for_agent(
            query=query,
            user_id=self.agent_id,
            thread_id=thread_id,
            strategy=strategy,
            top_k=20,  # Get more candidates for potential summarization
            include_context=True
        )

        memories = results['memories']

        # Apply summarization if enabled and needed
        if include_summary and self.summarizer and len(memories) > 10:
            memories = self.summarizer.compress_for_context_window(
                memories=memories,
                max_tokens=max_tokens,
                preserve_recent=5  # Keep 5 most recent uncompressed
            )

        # Format for AI agent
        context_text = self._format_context_for_agent(memories, query, thread_id)

        return {
            'text': context_text,
            'memories': memories,
            'metadata': {
                'total_memories': len(memories),
                'strategy': strategy,
                'retrieval_time_ms': results.get('retrieval_time_ms', 0),
                'thread_id': thread_id,
            }
        }

    def get_thread_history(
        self,
        thread_id: str,
        max_messages: int = 50,
        summarize_old: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get full conversation history for a thread.

        Args:
            thread_id: Thread ID
            max_messages: Maximum messages to return
            summarize_old: Summarize old messages if count exceeds max

        Returns:
            List of messages in chronological order
        """
        # Get all messages from thread
        memories = self.memoric.db.get_memories(
            user_id=self.agent_id,
            thread_id=thread_id,
            limit=1000
        )

        # Sort chronologically
        memories.sort(
            key=lambda m: m.get('created_at') or datetime.min.replace(tzinfo=timezone.utc)
        )

        # Summarize if too many messages
        if summarize_old and len(memories) > max_messages:
            if self.summarizer:
                memories = self.summarizer.compress_for_context_window(
                    memories=memories,
                    max_tokens=max_messages * 100,  # Rough estimate
                    preserve_recent=max_messages // 2
                )

        return memories[:max_messages]

    def search_across_threads(
        self,
        *,
        query: str,
        top_k: int = 10,
        strategy: str = "semantic_heavy",
    ) -> List[Dict[str, Any]]:
        """
        Search across all conversations for this agent.

        Useful for finding previous discussions on a topic.

        Args:
            query: Search query
            top_k: Number of results
            strategy: Retrieval strategy

        Returns:
            List of relevant memories from any thread
        """
        results = self.retriever.retrieve_for_agent(
            query=query,
            user_id=self.agent_id,
            thread_id=None,  # Search all threads
            strategy=strategy,
            top_k=top_k,
            include_context=False
        )

        return results['memories']

    def start_new_thread(
        self,
        *,
        thread_id: str,
        initial_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new conversation thread.

        Args:
            thread_id: Thread ID for new conversation
            initial_message: Optional first message
            metadata: Thread metadata

        Returns:
            Thread ID
        """
        if initial_message:
            self.add_message(
                content=initial_message,
                role="system",
                thread_id=thread_id,
                metadata={
                    **(metadata or {}),
                    'thread_start': True
                }
            )

        logger.info(f"Started new thread: {thread_id}")
        return thread_id

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about agent's conversation history.

        Returns:
            Dict with memory stats
        """
        all_memories = self.memoric.db.get_memories(
            user_id=self.agent_id,
            limit=10000
        )

        # Count threads
        threads = set(m.get('thread_id') for m in all_memories if m.get('thread_id'))

        # Count by role
        role_counts = {}
        for mem in all_memories:
            role = mem.get('metadata', {}).get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            'total_memories': len(all_memories),
            'total_threads': len(threads),
            'messages_by_role': role_counts,
            'agent_id': self.agent_id,
        }

    def _format_context_for_agent(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        thread_id: Optional[str],
    ) -> str:
        """
        Format memories into text for AI agent.

        Args:
            memories: Retrieved memories
            query: Original query
            thread_id: Current thread

        Returns:
            Formatted context string
        """
        # Separate current thread from related knowledge
        thread_memories = []
        related_memories = []

        for mem in memories:
            if thread_id and mem.get('thread_id') == thread_id:
                thread_memories.append(mem)
            else:
                related_memories.append(mem)

        parts = []

        # Current conversation
        if thread_memories:
            parts.append("=== Current Conversation ===")
            for mem in thread_memories:
                role = mem.get('metadata', {}).get('role', 'unknown')
                content = mem.get('content', '')
                parts.append(f"{role.capitalize()}: {content}")

        # Related knowledge
        if related_memories:
            parts.append("\n=== Related Context ===")
            for mem in related_memories:
                content = mem.get('content', '')
                source = mem.get('thread_id', 'unknown')
                parts.append(f"[From {source}] {content}")

        return "\n".join(parts)


__all__ = ["ConversationManager"]
