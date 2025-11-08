"""
Semantic Search for AI Agents - Find memories by meaning, not just keywords.

This module provides semantic/vector search capabilities for Memoric, enabling
AI agents to find relevant memories based on meaning and context rather than
exact keyword matching.

Features:
- Multiple embedding providers (OpenAI, Sentence Transformers, custom)
- Hybrid search (combine semantic similarity + keyword matching + recency)
- Efficient vector storage and similarity computation
- Graceful fallback when embeddings unavailable
- Integration with existing retrieval system

Example:
    from memoric import Memoric
    from memoric.core.semantic_search import SemanticSearchEngine

    # Initialize with semantic search
    m = Memoric()
    semantic = SemanticSearchEngine(db=m.db)

    # Search by meaning
    results = semantic.search(
        query="What did we discuss about the product launch?",
        user_id="agent_1",
        top_k=5,
        hybrid_alpha=0.7  # 70% semantic, 30% keyword
    )
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..db.postgres_connector import PostgresConnector
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingProvider:
    """Base class for embedding providers."""

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Embedding dimension size."""
        raise NotImplementedError


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embeddings.

        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if None)
            model: Embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._dimension = 1536  # text-embedding-3-small dimension

        if not self.api_key:
            logger.warning(
                "OpenAI API key not found. Semantic search will be disabled. "
                "Set OPENAI_API_KEY environment variable to enable."
            )
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI embeddings initialized with model {model}")
            except ImportError:
                logger.warning(
                    "OpenAI package not installed. Run: pip install openai"
                )
                self.client = None

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.client:
            return []

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batched for efficiency)."""
        if not self.client:
            return [[] for _ in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [[] for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class LocalEmbedding(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embeddings.

        Args:
            model_name: Sentence transformer model name
        """
        self.model_name = model_name
        self._dimension = 384  # all-MiniLM-L6-v2 dimension

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Local embeddings initialized with {model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )
            self.model = None

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.model:
            return []

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.model:
            return [[] for _ in texts]

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [[] for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
    """
    if not vec1 or not vec2:
        return 0.0

    arr1 = np.array(vec1)
    arr2 = np.array(vec2)

    dot_product = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


class SemanticSearchEngine:
    """
    Semantic search engine for finding memories by meaning.

    Provides vector/semantic search capabilities using external vector stores
    (Pinecone, Qdrant, etc.) for scalable similarity search.

    This class orchestrates:
    - Embedding generation (OpenAI, local, etc.)
    - Vector storage (via VectorStoreProvider)
    - Similarity search with fallback strategies
    """

    def __init__(
        self,
        *,
        db: PostgresConnector,
        vector_store: Optional[Any] = None,  # VectorStoreProvider
        embedding_provider: Optional[EmbeddingProvider] = None,
        fallback_to_keyword: bool = True,
    ):
        """
        Initialize semantic search engine.

        Args:
            db: Database connector (for fallback keyword search)
            vector_store: Vector store provider (Pinecone, Qdrant, etc.)
                         If None, uses in-memory store (development only)
            embedding_provider: Provider for generating embeddings (auto-detects if None)
            fallback_to_keyword: Fall back to keyword search if embeddings unavailable
        """
        self.db = db
        self.fallback_to_keyword = fallback_to_keyword

        # Initialize vector store
        if vector_store is None:
            logger.warning(
                "No vector store provided. Using in-memory store (NOT for production). "
                "For production, use: PineconeVectorStore or QdrantVectorStore"
            )
            from ..providers.vector_stores import InMemoryVectorStore
            self.vector_store = InMemoryVectorStore()
        else:
            self.vector_store = vector_store

        # Auto-detect embedding provider
        if embedding_provider is None:
            # Try OpenAI first, then local
            if os.getenv("OPENAI_API_KEY"):
                self.embedder = OpenAIEmbedding()
            else:
                logger.warning(
                    "No OpenAI API key found. Using local embeddings (slower, lower quality). "
                    "Set OPENAI_API_KEY for better results."
                )
                self.embedder = LocalEmbedding()
        else:
            self.embedder = embedding_provider

        logger.info(
            f"Semantic search initialized with {type(self.vector_store).__name__} "
            f"and {type(self.embedder).__name__}"
        )

    def embed_and_store(
        self,
        memory_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Generate and store embedding for a memory in vector store.

        Args:
            memory_id: Memory ID
            content: Memory content to embed
            metadata: Optional metadata to store with vector
            force: Force re-embedding even if exists

        Returns:
            True if embedding generated and stored successfully
        """
        try:
            # Check if embedding already exists (unless force=True)
            if not force:
                existing = self.vector_store.get(str(memory_id))
                if existing:
                    logger.debug(f"Embedding already exists for memory {memory_id}")
                    return True

            # Generate embedding
            embedding = self.embedder.embed(content)

            if not embedding:
                logger.warning(f"Failed to generate embedding for memory {memory_id}")
                return False

            # Store in vector database
            success = self.vector_store.upsert(
                id=str(memory_id),
                vector=embedding,
                metadata=metadata or {"content_preview": content[:100]}
            )

            if success:
                logger.debug(f"Stored embedding for memory {memory_id} in vector store")
            else:
                logger.error(f"Failed to store embedding for memory {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Error in embed_and_store for memory {memory_id}: {e}")
            return False

    def search(
        self,
        *,
        query: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        top_k: int = 10,
        hybrid_alpha: float = 0.5,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for memories using vector store.

        Args:
            query: Search query (natural language)
            user_id: Filter by user ID
            thread_id: Filter by thread ID
            top_k: Number of results to return
            hybrid_alpha: Balance between semantic (1.0) and keyword (0.0) search
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of memories ranked by semantic similarity
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)

        if not query_embedding:
            if self.fallback_to_keyword:
                logger.warning("Embedding failed, falling back to keyword search")
                return self._keyword_search(query, user_id, thread_id, top_k)
            else:
                logger.error("Semantic search failed and fallback disabled")
                return []

        # Search vector store for similar embeddings
        try:
            # Build filter for vector store
            vector_filter = {}
            if user_id:
                vector_filter['user_id'] = user_id
            if thread_id:
                vector_filter['thread_id'] = thread_id

            # Search vector store (get more candidates for hybrid ranking)
            vector_results = self.vector_store.search(
                vector=query_embedding,
                top_k=top_k * 3,  # Get 3x candidates for hybrid re-ranking
                filter=vector_filter if vector_filter else None
            )

            if not vector_results:
                logger.info("No results from vector store, trying keyword fallback")
                if self.fallback_to_keyword and hybrid_alpha < 1.0:
                    return self._keyword_search(query, user_id, thread_id, top_k)
                return []

            # Extract memory IDs and scores from vector results
            memory_ids = [int(result['id']) for result in vector_results]
            vector_scores = {int(result['id']): result.get('score', 0.0) for result in vector_results}

            # Fetch full memory details from database
            memories = []
            for memory_id in memory_ids:
                # Get memory from database
                memory_list = self.db.get_memories(memory_id=memory_id, limit=1)
                if memory_list:
                    memories.append(memory_list[0])

            if not memories:
                logger.warning("Vector search succeeded but couldn't fetch memories from DB")
                return []

            # Apply hybrid scoring
            scored_memories = []
            for memory in memories:
                memory_id = memory.get('id')
                semantic_score = vector_scores.get(memory_id, 0.0)

                # Filter by minimum similarity
                if semantic_score < min_similarity:
                    continue

                # Compute keyword score for hybrid ranking
                keyword_score = 0.0
                if hybrid_alpha < 1.0:
                    keyword_score = self._keyword_score(query, memory.get('content', ''))

                # Compute hybrid score
                hybrid_score = (
                    hybrid_alpha * semantic_score +
                    (1 - hybrid_alpha) * keyword_score
                )

                memory['_semantic_score'] = semantic_score
                memory['_keyword_score'] = keyword_score
                memory['_hybrid_score'] = hybrid_score
                scored_memories.append(memory)

            # Sort by hybrid score and return top_k
            scored_memories.sort(key=lambda m: m.get('_hybrid_score', 0), reverse=True)

            return scored_memories[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            if self.fallback_to_keyword:
                logger.info("Falling back to keyword search")
                return self._keyword_search(query, user_id, thread_id, top_k)
            return []

    def _keyword_score(self, query: str, content: str) -> float:
        """
        Simple keyword-based similarity score.

        Args:
            query: Search query
            content: Memory content

        Returns:
            Keyword similarity score 0-1
        """
        if not query or not content:
            return 0.0

        # Simple word overlap scoring
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        overlap = len(query_words & content_words)
        return overlap / len(query_words)

    def _keyword_search(
        self,
        query: str,
        user_id: Optional[str],
        thread_id: Optional[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based search."""
        memories = self.db.get_memories(
            user_id=user_id,
            thread_id=thread_id,
            limit=1000
        )

        scored = []
        for memory in memories:
            score = self._keyword_score(query, memory.get('content', ''))
            memory['_keyword_score'] = score
            scored.append(memory)

        scored.sort(key=lambda m: m.get('_keyword_score', 0), reverse=True)
        return scored[:top_k]


__all__ = [
    "SemanticSearchEngine",
    "EmbeddingProvider",
    "OpenAIEmbedding",
    "LocalEmbedding",
    "cosine_similarity",
]
