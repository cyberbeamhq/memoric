"""
Hybrid Retriever for AI Agents - DEPRECATED

⚠️ DEPRECATION WARNING:
This class is deprecated. Use the simpler Memory class instead:

Old way (deprecated):
    from memoric.core.hybrid_retriever import HybridRetriever
    retriever = HybridRetriever(db=db)
    results = retriever.retrieve_for_agent(query="...", user_id="...")

New way (recommended):
    from memoric import Memory
    memory = Memory(user_id="...")
    results = memory.search("...")

The Memory class includes hybrid retrieval by default.
See examples/simple.py for migration guide.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..db.postgres_connector import PostgresConnector
from ..utils.scoring import ScoringEngine
from ..utils.logger import get_logger
from .semantic_search import SemanticSearchEngine, OpenAIEmbedding, LocalEmbedding

logger = get_logger(__name__)


class RetrievalStrategy:
    """Predefined retrieval strategies for different AI agent use cases."""

    # Balanced: Equal weight to semantic, keyword, and recency
    BALANCED = {
        "semantic_weight": 0.4,
        "keyword_weight": 0.3,
        "recency_weight": 0.2,
        "importance_weight": 0.1,
    }

    # Semantic-heavy: Best for conceptual queries
    SEMANTIC_HEAVY = {
        "semantic_weight": 0.6,
        "keyword_weight": 0.2,
        "recency_weight": 0.1,
        "importance_weight": 0.1,
    }

    # Keyword-heavy: Best for fact retrieval
    KEYWORD_HEAVY = {
        "semantic_weight": 0.2,
        "keyword_weight": 0.5,
        "recency_weight": 0.2,
        "importance_weight": 0.1,
    }

    # Recent-first: Best for conversation continuity
    RECENT_FIRST = {
        "semantic_weight": 0.2,
        "keyword_weight": 0.2,
        "recency_weight": 0.5,
        "importance_weight": 0.1,
    }

    # Important-first: Best for critical information
    IMPORTANT_FIRST = {
        "semantic_weight": 0.2,
        "keyword_weight": 0.2,
        "recency_weight": 0.1,
        "importance_weight": 0.5,
    }


class HybridRetriever:
    """
    Hybrid retrieval system combining semantic search, keyword matching,
    and temporal/importance scoring for optimal AI agent context.
    """

    def __init__(
        self,
        *,
        db: PostgresConnector,
        vector_store: Optional[Any] = None,
        scoring_config: Optional[dict] = None,
        enable_semantic: bool = True,
        embedding_provider: Optional[str] = None,  # "openai", "local", or None for auto
    ):
        """
        Initialize hybrid retriever.

        Args:
            db: Database connector
            vector_store: Vector store provider (Pinecone, Qdrant, etc.)
            scoring_config: Configuration for scoring engine
            enable_semantic: Enable semantic search (requires embeddings)
            embedding_provider: Which embedding provider to use
        """
        self.db = db
        self.scorer = ScoringEngine(config=scoring_config)

        # Initialize semantic search if enabled
        self.semantic_enabled = enable_semantic
        if enable_semantic:
            if embedding_provider == "openai":
                provider = OpenAIEmbedding()
            elif embedding_provider == "local":
                provider = LocalEmbedding()
            else:
                provider = None  # Auto-detect

            self.semantic = SemanticSearchEngine(
                db=db,
                vector_store=vector_store,  # Pass vector store through
                embedding_provider=provider
            )
        else:
            self.semantic = None

        # Deprecation warning
        import warnings
        warnings.warn(
            "HybridRetriever is deprecated and will be removed in a future version. "
            "Please use the simpler Memory class instead: from memoric import Memory",
            DeprecationWarning,
            stacklevel=2
        )

        logger.info(f"Hybrid retriever initialized (semantic: {enable_semantic})")

    def retrieve_for_agent(
        self,
        *,
        query: str,
        user_id: str,
        thread_id: Optional[str] = None,
        strategy: str = "balanced",
        top_k: int = 10,
        include_context: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve optimal memories for an AI agent.

        This is the main entry point for AI agents to get relevant context.
        It combines multiple retrieval methods and returns structured results.

        Args:
            query: Natural language query from the AI agent
            user_id: User/agent ID for memory isolation
            thread_id: Current conversation thread
            strategy: Retrieval strategy ("balanced", "semantic_heavy", etc.)
            top_k: Number of memories to return
            include_context: Include full context assembly

        Returns:
            Dict with 'memories' (ranked list) and optional 'context' (formatted)
        """
        start_time = time.time()

        # Get strategy weights
        weights = self._get_strategy_weights(strategy)

        # Retrieve using multiple methods
        results = []

        # 1. Semantic search (if enabled and query is meaningful)
        if self.semantic_enabled and self.semantic and len(query.split()) > 2:
            try:
                semantic_results = self.semantic.search(
                    query=query,
                    user_id=user_id,
                    thread_id=thread_id,
                    top_k=top_k * 2,  # Get more candidates
                    hybrid_alpha=0.7,  # Favor semantic in semantic search
                )
                for mem in semantic_results:
                    mem['_retrieval_method'] = 'semantic'
                    results.extend(semantic_results)
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")

        # 2. Keyword/metadata search
        keyword_results = self.db.get_memories(
            user_id=user_id,
            thread_id=thread_id,
            limit=top_k * 2
        )
        for mem in keyword_results:
            mem['_retrieval_method'] = 'keyword'
        results.extend(keyword_results)

        # 3. Recency search (recent memories from this user)
        recent_results = self.db.get_memories(
            user_id=user_id,
            limit=min(20, top_k * 2)
        )
        for mem in recent_results:
            if not any(m['id'] == mem['id'] for m in results):
                mem['_retrieval_method'] = 'recency'
                results.append(mem)

        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for mem in results:
            if mem['id'] not in seen_ids:
                seen_ids.add(mem['id'])
                unique_results.append(mem)

        # Hybrid scoring
        scored_results = []
        for mem in unique_results:
            # Get scores from different sources
            semantic_score = mem.get('_semantic_score', 0.0)
            keyword_score = mem.get('_keyword_score', 0.0)
            recency_score = self.scorer.compute(mem) / 100.0  # Normalize to 0-1
            importance_score = self._get_importance_score(mem)

            # Combine using strategy weights
            hybrid_score = (
                weights['semantic_weight'] * semantic_score +
                weights['keyword_weight'] * keyword_score +
                weights['recency_weight'] * recency_score +
                weights['importance_weight'] * importance_score
            )

            mem['_hybrid_score'] = hybrid_score
            mem['_score_breakdown'] = {
                'semantic': semantic_score,
                'keyword': keyword_score,
                'recency': recency_score,
                'importance': importance_score,
            }
            scored_results.append(mem)

        # Sort by hybrid score and take top_k
        scored_results.sort(key=lambda m: m['_hybrid_score'], reverse=True)
        final_results = scored_results[:top_k]

        # Build response
        response = {
            'memories': final_results,
            'count': len(final_results),
            'strategy': strategy,
            'retrieval_time_ms': (time.time() - start_time) * 1000,
        }

        # Add context assembly if requested
        if include_context:
            response['context'] = self._assemble_agent_context(
                final_results,
                query,
                thread_id
            )

        logger.info(
            f"Hybrid retrieval completed",
            extra={
                'user_id': user_id,
                'query_length': len(query),
                'results': len(final_results),
                'strategy': strategy,
                'time_ms': response['retrieval_time_ms'],
            }
        )

        return response

    def _get_strategy_weights(self, strategy: str) -> Dict[str, float]:
        """Get weights for a named strategy."""
        strategy_map = {
            'balanced': RetrievalStrategy.BALANCED,
            'semantic_heavy': RetrievalStrategy.SEMANTIC_HEAVY,
            'keyword_heavy': RetrievalStrategy.KEYWORD_HEAVY,
            'recent_first': RetrievalStrategy.RECENT_FIRST,
            'important_first': RetrievalStrategy.IMPORTANT_FIRST,
        }

        return strategy_map.get(strategy.lower(), RetrievalStrategy.BALANCED)

    def _get_importance_score(self, memory: Dict[str, Any]) -> float:
        """Get normalized importance score from memory metadata."""
        metadata = memory.get('metadata', {})
        importance = metadata.get('importance', 'medium')

        importance_map = {
            'low': 0.25,
            'medium': 0.5,
            'high': 0.75,
            'critical': 1.0,
        }

        return importance_map.get(importance, 0.5)

    def _assemble_agent_context(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        thread_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Assemble memories into agent-friendly context.

        Args:
            memories: Retrieved memories
            query: Original query
            thread_id: Current thread

        Returns:
            Structured context optimized for AI agents
        """
        # Separate by thread
        thread_memories = []
        related_memories = []

        for mem in memories:
            if thread_id and mem.get('thread_id') == thread_id:
                thread_memories.append(mem)
            else:
                related_memories.append(mem)

        # Format for agent consumption
        context = {
            'query': query,
            'current_conversation': [
                {
                    'content': m['content'],
                    'timestamp': m.get('created_at'),
                    'relevance': m.get('_hybrid_score', 0),
                }
                for m in thread_memories
            ],
            'related_knowledge': [
                {
                    'content': m['content'],
                    'source': m.get('thread_id', 'unknown'),
                    'relevance': m.get('_hybrid_score', 0),
                    'why_relevant': self._explain_relevance(m),
                }
                for m in related_memories
            ],
            'summary': {
                'total_memories': len(memories),
                'from_current_thread': len(thread_memories),
                'from_related_threads': len(related_memories),
                'avg_relevance': sum(m.get('_hybrid_score', 0) for m in memories) / len(memories) if memories else 0,
            }
        }

        return context

    def _explain_relevance(self, memory: Dict[str, Any]) -> str:
        """Generate human-readable explanation of why this memory is relevant."""
        scores = memory.get('_score_breakdown', {})
        method = memory.get('_retrieval_method', 'unknown')

        reasons = []

        if scores.get('semantic', 0) > 0.5:
            reasons.append("semantically similar")
        if scores.get('keyword', 0) > 0.3:
            reasons.append("keyword match")
        if scores.get('recency', 0) > 0.7:
            reasons.append("recent")
        if scores.get('importance', 0) > 0.7:
            reasons.append("marked as important")

        if not reasons:
            reasons.append(f"retrieved via {method}")

        return ", ".join(reasons)


__all__ = ["HybridRetriever", "RetrievalStrategy"]
