"""
Text processing abstractions for trimming and summarization.

This module provides base classes that allow users to:
1. Disable text processing entirely
2. Use built-in simple processors
3. Implement custom processors (e.g., LLM-based)

This prevents data loss by making text processing configurable and pluggable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TextTrimmer(ABC):
    """Abstract base class for text trimming strategies."""

    @abstractmethod
    def trim(self, text: str, max_chars: int) -> str:
        """Trim text to maximum characters.

        Args:
            text: Text to trim
            max_chars: Maximum characters to keep

        Returns:
            Trimmed text
        """
        pass


class TextSummarizer(ABC):
    """Abstract base class for text summarization strategies."""

    @abstractmethod
    def summarize(self, text: str, target_chars: int) -> str:
        """Summarize text to target length.

        Args:
            text: Text to summarize
            target_chars: Target character length

        Returns:
            Summarized text
        """
        pass


class NoOpTrimmer(TextTrimmer):
    """Trimmer that does nothing - preserves all data."""

    def trim(self, text: str, max_chars: int) -> str:
        """Return text unchanged (no trimming).

        Args:
            text: Text to trim
            max_chars: Ignored

        Returns:
            Original text unchanged
        """
        return text


class NoOpSummarizer(TextSummarizer):
    """Summarizer that does nothing - preserves all data."""

    def summarize(self, text: str, target_chars: int) -> str:
        """Return text unchanged (no summarization).

        Args:
            text: Text to summarize
            target_chars: Ignored

        Returns:
            Original text unchanged
        """
        return text


class SimpleTrimmer(TextTrimmer):
    """Simple truncation-based trimmer with ellipsis."""

    def trim(self, text: str, max_chars: int) -> str:
        """Truncate text to maximum character length with ellipsis.

        Args:
            text: Text to trim
            max_chars: Maximum characters to keep

        Returns:
            Trimmed text with ellipsis if truncated
        """
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        trimmed = text[: max(0, max_chars - 1)].rstrip()
        if not trimmed:
            return text[:max_chars]
        return trimmed + "…"


class SimpleSummarizer(TextSummarizer):
    """Simple heuristic-based summarizer (sentence-aware truncation).

    Note: This is NOT true summarization - it's a naive heuristic:
    - If first sentence fits, return it
    - Otherwise, truncate with ellipsis

    For production, consider implementing LLMSummarizer below.
    """

    def __init__(self, trimmer: Optional[TextTrimmer] = None):
        """Initialize summarizer.

        Args:
            trimmer: Trimmer to use for fallback. Defaults to SimpleTrimmer.
        """
        self.trimmer = trimmer or SimpleTrimmer()

    def summarize(self, text: str, target_chars: int) -> str:
        """Summarize using first sentence or truncation.

        Args:
            text: Text to summarize
            target_chars: Target character length

        Returns:
            First sentence if it fits, otherwise truncated text
        """
        if target_chars <= 0:
            return ""
        if len(text) <= target_chars:
            return text

        # Try to find first sentence
        period = text.find(".")
        if 0 < period <= target_chars:
            return text[: period + 1]

        # Fallback to trimming
        return self.trimmer.trim(text, target_chars)


class LLMSummarizer(TextSummarizer):
    """LLM-based summarization using OpenAI or compatible API.

    Example of how users can implement their own LLM-based summarization
    to avoid data loss through intelligent compression.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        fallback: Optional[TextSummarizer] = None,
    ):
        """Initialize LLM summarizer.

        Args:
            model: OpenAI model to use
            api_key: OpenAI API key (or None to use env var)
            fallback: Fallback summarizer if LLM fails
        """
        self.model = model
        self.fallback = fallback or SimpleSummarizer()

        try:
            from openai import OpenAI  # type: ignore

            self.client = OpenAI(api_key=api_key) if api_key or True else None
        except Exception:
            self.client = None

    def summarize(self, text: str, target_chars: int) -> str:
        """Summarize text using LLM.

        Args:
            text: Text to summarize
            target_chars: Target character length (approximate)

        Returns:
            LLM-generated summary, or fallback if LLM unavailable
        """
        if not self.client:
            return self.fallback.summarize(text, target_chars)

        try:
            # Request summary from LLM
            prompt = (
                f"Summarize the following text in approximately {target_chars} characters. "
                f"Preserve key information and context:\n\n{text}"
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=int(target_chars / 3),  # Rough token estimate
            )

            summary = response.choices[0].message.content or ""
            return summary.strip()

        except Exception:
            # Fallback on any error
            return self.fallback.summarize(text, target_chars)


# Factory function for easy instantiation from config
def create_trimmer(config: dict) -> TextTrimmer:
    """Create a trimmer from configuration.

    Args:
        config: Configuration dict with 'type' key

    Returns:
        TextTrimmer instance

    Example config:
        {"type": "simple"}  # Default
        {"type": "noop"}    # Disable trimming
    """
    trimmer_type = config.get("type", "simple").lower()

    if trimmer_type == "noop" or trimmer_type == "disabled":
        return NoOpTrimmer()
    elif trimmer_type == "simple":
        return SimpleTrimmer()
    else:
        # Default to simple trimmer
        return SimpleTrimmer()


def create_summarizer(config: dict) -> TextSummarizer:
    """Create a summarizer from configuration.

    Args:
        config: Configuration dict with 'type' and optional params

    Returns:
        TextSummarizer instance

    Example config:
        {"type": "simple"}                              # Default heuristic
        {"type": "noop"}                                # Disable summarization
        {"type": "llm", "model": "gpt-4o-mini"}        # LLM-based
    """
    summarizer_type = config.get("type", "simple").lower()

    if summarizer_type == "noop" or summarizer_type == "disabled":
        return NoOpSummarizer()
    elif summarizer_type == "llm":
        model = config.get("model", "gpt-4o-mini")
        api_key = config.get("api_key")
        return LLMSummarizer(model=model, api_key=api_key)
    elif summarizer_type == "simple":
        return SimpleSummarizer()
    else:
        # Default to simple summarizer
        return SimpleSummarizer()
