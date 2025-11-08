"""
Smart Summarization for AI Agents - Compress memories to maximize context.

This module provides intelligent summarization capabilities for AI agents,
helping them fit more relevant information into limited context windows.

Features:
- Conversation summarization (compress multi-turn dialogues)
- Knowledge extraction (pull out key facts)
- Progressive summarization (summarize older memories more aggressively)
- Token-aware compression (respect context window limits)
- Importance preservation (keep critical details)

Example:
    from memoric import Memoric
    from memoric.agents.smart_summarizer import SmartSummarizer

    m = Memoric()
    summarizer = SmartSummarizer()

    # Summarize old conversation
    summary = summarizer.summarize_thread(
        memories=old_thread_memories,
        style="conversational",  # or "bullet_points", "key_facts"
        max_tokens=500
    )

    # Progressive summarization for context window
    compressed = summarizer.compress_for_context_window(
        memories=all_memories,
        max_tokens=4000,
        preserve_recent=10  # Keep recent messages uncompressed
    )
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SmartSummarizer:
    """
    Intelligent summarization for AI agent memory management.

    Compresses old memories while preserving important information,
    enabling agents to maintain longer conversation context within
    fixed context window limits.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        fallback_to_simple: bool = True,
    ):
        """
        Initialize smart summarizer.

        Args:
            model: OpenAI model for summarization
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if None)
            fallback_to_simple: Use simple summarization if LLM unavailable
        """
        self.model = model
        self.fallback_to_simple = fallback_to_simple
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"Smart summarizer initialized with {model}")
            except ImportError:
                logger.warning("OpenAI not available, using simple summarization")
                self.client = None
        else:
            logger.warning("No OpenAI API key, using simple summarization")
            self.client = None

    def summarize_thread(
        self,
        *,
        memories: List[Dict[str, Any]],
        style: str = "conversational",
        max_tokens: int = 500,
        preserve_names: bool = True,
    ) -> str:
        """
        Summarize a conversation thread.

        Args:
            memories: List of memories from a thread (chronological order)
            style: Summarization style ("conversational", "bullet_points", "key_facts")
            max_tokens: Maximum tokens in summary
            preserve_names: Keep person/entity names in summary

        Returns:
            Summarized text
        """
        if not memories:
            return ""

        # Use LLM summarization if available
        if self.client:
            return self._llm_summarize(memories, style, max_tokens, preserve_names)
        elif self.fallback_to_simple:
            return self._simple_summarize(memories, style, max_tokens)
        else:
            logger.warning("Summarization unavailable")
            return ""

    def _llm_summarize(
        self,
        memories: List[Dict[str, Any]],
        style: str,
        max_tokens: int,
        preserve_names: bool,
    ) -> str:
        """LLM-based summarization."""
        # Build conversation text
        conversation = self._format_for_summarization(memories)

        # Create prompt based on style
        system_prompt = self._get_system_prompt(style, preserve_names)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation}
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for factual summarization
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            if self.fallback_to_simple:
                return self._simple_summarize(memories, style, max_tokens)
            return ""

    def _simple_summarize(
        self,
        memories: List[Dict[str, Any]],
        style: str,
        max_tokens: int,
    ) -> str:
        """Simple extractive summarization (no LLM needed)."""
        # Extract key sentences based on importance and position
        sentences = []

        for mem in memories:
            content = mem.get('content', '')
            importance = mem.get('metadata', {}).get('importance', 'medium')

            # Split into sentences
            mem_sentences = [s.strip() for s in content.split('.') if s.strip()]

            # Weight by importance
            importance_weight = {
                'critical': 1.0,
                'high': 0.7,
                'medium': 0.4,
                'low': 0.1,
            }.get(importance, 0.4)

            for sent in mem_sentences:
                if len(sent) > 20:  # Filter very short sentences
                    sentences.append((sent, importance_weight))

        # Sort by importance and take top sentences
        sentences.sort(key=lambda x: x[1], reverse=True)

        # Build summary respecting token limit (rough estimate: 4 chars = 1 token)
        char_limit = max_tokens * 4
        summary_parts = []
        current_length = 0

        for sent, weight in sentences:
            if current_length + len(sent) > char_limit:
                break
            summary_parts.append(sent)
            current_length += len(sent) + 2  # +2 for ". "

        if style == "bullet_points":
            return "\n• " + "\n• ".join(summary_parts)
        else:
            return ". ".join(summary_parts) + "."

    def compress_for_context_window(
        self,
        *,
        memories: List[Dict[str, Any]],
        max_tokens: int = 4000,
        preserve_recent: int = 10,
        progressive: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Compress memories to fit within context window.

        Uses progressive summarization: older memories are compressed more
        aggressively, while recent memories are preserved in full.

        Args:
            memories: List of memories (should be sorted by time)
            max_tokens: Maximum total tokens for all memories
            preserve_recent: Number of recent memories to keep uncompressed
            progressive: Use progressive compression (older = more compressed)

        Returns:
            List of memories with compressed content
        """
        if not memories:
            return []

        # Sort by timestamp (oldest first)
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get('created_at') or datetime.min.replace(tzinfo=timezone.utc)
        )

        total_memories = len(sorted_memories)

        # Keep recent memories uncompressed
        if total_memories <= preserve_recent:
            return sorted_memories

        # Split into old (to compress) and recent (to preserve)
        old_memories = sorted_memories[:-preserve_recent]
        recent_memories = sorted_memories[-preserve_recent:]

        # Progressive compression
        if progressive:
            compressed_old = self._progressive_compress(old_memories, max_tokens // 2)
        else:
            # Uniform compression
            summary = self.summarize_thread(
                memories=old_memories,
                style="conversational",
                max_tokens=max_tokens // 2
            )
            compressed_old = [{
                'content': summary,
                'metadata': {
                    'summarized': True,
                    'original_count': len(old_memories),
                    'compression_ratio': len(summary) / sum(len(m.get('content', '')) for m in old_memories)
                }
            }]

        # Combine compressed old + uncompressed recent
        result = compressed_old + recent_memories

        logger.info(
            f"Compressed {total_memories} memories to {len(result)} entries",
            extra={
                'original': total_memories,
                'compressed': len(compressed_old),
                'preserved': len(recent_memories),
            }
        )

        return result

    def _progressive_compress(
        self,
        memories: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        Progressive compression: group old memories into buckets and summarize.

        Older buckets get more aggressive compression.
        """
        if not memories:
            return []

        # Group into time buckets (e.g., by week)
        buckets = self._group_by_time(memories, bucket_size_days=7)

        compressed = []
        tokens_used = 0
        token_budget_per_bucket = max_tokens // len(buckets) if buckets else max_tokens

        for i, bucket in enumerate(buckets):
            # Older buckets get smaller budget (more compression)
            bucket_budget = int(token_budget_per_bucket * (1 - i / len(buckets) * 0.5))

            if len(bucket) == 1:
                # Single memory, keep as is (unless very old)
                if i < len(buckets) // 2:  # First half (older) - compress
                    summary = self._simple_summarize(bucket, "conversational", bucket_budget)
                    compressed.append({
                        'content': summary,
                        'metadata': {'summarized': True, 'bucket': i}
                    })
                else:
                    compressed.append(bucket[0])
            else:
                # Multiple memories, summarize bucket
                summary = self.summarize_thread(
                    memories=bucket,
                    style="conversational",
                    max_tokens=bucket_budget
                )
                compressed.append({
                    'content': summary,
                    'metadata': {
                        'summarized': True,
                        'bucket': i,
                        'original_count': len(bucket)
                    }
                })

            tokens_used += bucket_budget

        return compressed

    def _group_by_time(
        self,
        memories: List[Dict[str, Any]],
        bucket_size_days: int = 7,
    ) -> List[List[Dict[str, Any]]]:
        """Group memories into time-based buckets."""
        if not memories:
            return []

        # Get earliest timestamp
        earliest = min(
            m.get('created_at') or datetime.max.replace(tzinfo=timezone.utc)
            for m in memories
        )

        # Create buckets
        buckets: Dict[int, List[Dict[str, Any]]] = {}

        for mem in memories:
            timestamp = mem.get('created_at') or datetime.now(timezone.utc)
            days_since_earliest = (timestamp - earliest).days
            bucket_idx = days_since_earliest // bucket_size_days

            if bucket_idx not in buckets:
                buckets[bucket_idx] = []
            buckets[bucket_idx].append(mem)

        # Return buckets in chronological order
        return [buckets[i] for i in sorted(buckets.keys())]

    def _format_for_summarization(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for summarization input."""
        lines = []
        for mem in memories:
            content = mem.get('content', '')
            metadata = mem.get('metadata', {})
            role = metadata.get('role', 'user')

            lines.append(f"{role.capitalize()}: {content}")

        return "\n".join(lines)

    def _get_system_prompt(self, style: str, preserve_names: bool) -> str:
        """Get system prompt for LLM summarization."""
        base = "You are an expert at summarizing conversations for AI agents. "

        if style == "conversational":
            base += "Create a natural, flowing summary that captures the key points and context of the conversation. "
        elif style == "bullet_points":
            base += "Create a concise bullet-point summary of the key topics and decisions. "
        elif style == "key_facts":
            base += "Extract and list only the most important facts, decisions, and action items. "

        if preserve_names:
            base += "Always preserve person names, dates, and specific details. "

        base += "Be concise but comprehensive. Focus on information that would help an AI agent understand the conversation context."

        return base


__all__ = ["SmartSummarizer"]
