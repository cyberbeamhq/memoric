from __future__ import annotations

def trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    trimmed = text[: max(0, max_chars - 1)].rstrip()
    if not trimmed:
        return text[:max_chars]
    return trimmed + "…"


def summarize_simple(text: str, target_chars: int) -> str:
    if target_chars <= 0:
        return ""
    if len(text) <= target_chars:
        return text
    # Naive: take first sentence up to target, otherwise trim
    period = text.find(".")
    if 0 < period <= target_chars:
        return text[: period + 1]
    return trim_text(text, target_chars)


