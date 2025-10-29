"""
Utility modules for Memoric.

Provides:
- Text processing (trimming, summarization)
- Scoring utilities
- Logging and metrics
"""

from __future__ import annotations

# Use relative imports (standard for package structure)
from .text_processors import (
    TextTrimmer,
    TextSummarizer,
    NoOpTrimmer,
    NoOpSummarizer,
    SimpleTrimmer,
    SimpleSummarizer,
    LLMSummarizer,
    create_trimmer,
    create_summarizer,
)
from .scoring import (
    ScoringEngine,
    ScoringWeights,
    create_topic_boost_rule,
    create_entity_match_rule,
    IMPORTANCE_LEVELS,
)

__all__ = [
    # Text processors
    "TextTrimmer",
    "TextSummarizer",
    "NoOpTrimmer",
    "NoOpSummarizer",
    "SimpleTrimmer",
    "SimpleSummarizer",
    "LLMSummarizer",
    "create_trimmer",
    "create_summarizer",
    # Scoring
    "ScoringEngine",
    "ScoringWeights",
    "create_topic_boost_rule",
    "create_entity_match_rule",
    "IMPORTANCE_LEVELS",
]
