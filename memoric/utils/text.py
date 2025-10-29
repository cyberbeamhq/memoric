from __future__ import annotations


def trim_text(text: str, max_chars: int) -> str:
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


def summarize_simple(text: str, target_chars: int) -> str:
    """Simple heuristic-based text summarization (truncation with sentence awareness).

    Note: This is NOT true summarization - it uses a naive heuristic:
    - If the first sentence fits within target_chars, return it
    - Otherwise, truncate to target_chars

    For production use, consider using an LLM-based summarization approach.

    Args:
        text: Text to summarize
        target_chars: Target character length

    Returns:
        "Summarized" (truncated) text
    """
    if target_chars <= 0:
        return ""
    if len(text) <= target_chars:
        return text
    # Naive: take first sentence up to target, otherwise trim
    period = text.find(".")
    if 0 < period <= target_chars:
        return text[: period + 1]
    return trim_text(text, target_chars)
