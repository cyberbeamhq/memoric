"""
Context Assembler - Formats retrieved memories into structured context.

This module provides functionality to transform raw memory retrieval results
into structured, LLM-ready context with thread-specific and related history.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ContextAssembler:
    """Assembles structured context from retrieved memories."""

    def __init__(self, include_metadata: bool = True, include_scores: bool = False):
        """
        Initialize ContextAssembler.

        Args:
            include_metadata: Include metadata in output
            include_scores: Include relevance scores in output
        """
        self.include_metadata = include_metadata
        self.include_scores = include_scores

    def assemble(
        self,
        memories: List[Dict[str, Any]],
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        format_type: str = "structured",
    ) -> Dict[str, Any]:
        """
        Assemble memories into structured context.

        Args:
            memories: List of memory dictionaries from retriever
            thread_id: Current thread ID to separate thread vs related context
            user_id: User ID for metadata
            format_type: Output format - 'structured', 'simple', or 'chat'

        Returns:
            Structured context dictionary with thread_context and related_history
        """
        if format_type == "structured":
            return self._assemble_structured(memories, thread_id, user_id)
        elif format_type == "simple":
            return self._assemble_simple(memories)
        elif format_type == "chat":
            return self._assemble_chat(memories, thread_id)
        else:
            return self._assemble_structured(memories, thread_id, user_id)

    def _assemble_structured(
        self,
        memories: List[Dict[str, Any]],
        thread_id: Optional[str],
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """Assemble structured context with thread_context and related_history."""
        # Separate current thread from related memories
        thread_memories = []
        related_memories = []

        for mem in memories:
            if thread_id and mem.get("thread_id") == thread_id:
                thread_memories.append(mem)
            else:
                related_memories.append(mem)

        # Format thread context
        thread_context = [self._format_memory(m) for m in thread_memories]

        # Format related history
        related_history = [self._format_memory(m) for m in related_memories]

        # Extract common metadata
        metadata = self._extract_metadata(memories, thread_id, user_id)

        result = {
            "thread_context": thread_context,
            "related_history": related_history,
            "metadata": metadata,
        }

        if self.include_scores:
            result["scores"] = {
                "thread_avg": self._avg_score(thread_memories),
                "related_avg": self._avg_score(related_memories),
            }

        return result

    def _assemble_simple(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple list format."""
        return {
            "memories": [self._format_memory(m) for m in memories],
            "count": len(memories),
        }

    def _assemble_chat(
        self, memories: List[Dict[str, Any]], thread_id: Optional[str]
    ) -> Dict[str, Any]:
        """Chat-style format with role labels."""
        messages = []
        for mem in memories:
            role = mem.get("metadata", {}).get("role", "user")
            content = mem.get("content", "")
            messages.append({"role": role, "content": content})

        return {
            "messages": messages,
            "thread_id": thread_id,
            "count": len(messages),
        }

    def _format_memory(self, memory: Dict[str, Any]) -> str:
        """Format a single memory for display."""
        content = memory.get("content", "")
        metadata = memory.get("metadata", {})

        # Check if there's a role
        role = metadata.get("role")
        if role:
            # Format as chat message
            role_label = role.capitalize()
            return f"{role_label}: {content}"
        else:
            # Just return content
            return content

    def _extract_metadata(
        self,
        memories: List[Dict[str, Any]],
        thread_id: Optional[str],
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """Extract common metadata from memories."""
        if not memories or not self.include_metadata:
            return {}

        # Find most common topic, category, importance
        topics = []
        categories = []
        importances = []

        for mem in memories:
            meta = mem.get("metadata", {})
            if "topic" in meta:
                topics.append(meta["topic"])
            if "category" in meta:
                categories.append(meta["category"])
            if "importance" in meta:
                importances.append(meta["importance"])

        result = {}
        if thread_id:
            result["thread_id"] = thread_id
        if user_id:
            result["user_id"] = user_id

        # Most common values
        if topics:
            result["topic"] = max(set(topics), key=topics.count)
        if categories:
            result["category"] = max(set(categories), key=categories.count)
        if importances:
            result["importance"] = max(set(importances), key=importances.count)

        return result

    def _avg_score(self, memories: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate average score."""
        if not memories:
            return None
        scores = [m.get("_score", 0) for m in memories]
        return sum(scores) / len(scores) if scores else None

    def format_for_llm(
        self,
        context: Dict[str, Any],
        format_style: str = "conversational",
    ) -> str:
        """
        Format structured context as string for LLM input.

        Args:
            context: Structured context from assemble()
            format_style: 'conversational', 'bullet', or 'compact'

        Returns:
            Formatted string ready for LLM context window
        """
        if format_style == "conversational":
            return self._format_conversational(context)
        elif format_style == "bullet":
            return self._format_bullet(context)
        elif format_style == "compact":
            return self._format_compact(context)
        else:
            return self._format_conversational(context)

    def _format_conversational(self, context: Dict[str, Any]) -> str:
        """Format as natural conversation."""
        parts = []

        thread_context = context.get("thread_context", [])
        if thread_context:
            parts.append("Current Conversation:")
            for msg in thread_context:
                parts.append(f"  {msg}")

        related_history = context.get("related_history", [])
        if related_history:
            parts.append("\nRelated Context:")
            for msg in related_history:
                parts.append(f"  {msg}")

        return "\n".join(parts)

    def _format_bullet(self, context: Dict[str, Any]) -> str:
        """Format as bullet points."""
        parts = []

        thread_context = context.get("thread_context", [])
        if thread_context:
            parts.append("• Current Thread:")
            for msg in thread_context:
                parts.append(f"  - {msg}")

        related_history = context.get("related_history", [])
        if related_history:
            parts.append("• Related History:")
            for msg in related_history:
                parts.append(f"  - {msg}")

        return "\n".join(parts)

    def _format_compact(self, context: Dict[str, Any]) -> str:
        """Compact single-line format."""
        thread_context = context.get("thread_context", [])
        related_history = context.get("related_history", [])

        all_messages = thread_context + related_history
        return " | ".join(all_messages[:10])  # Limit to 10 for compactness
