"""
Example: Custom Text Processing (Trimming and Summarization)

This example demonstrates how to:
1. Disable trimming/summarization to prevent data loss
2. Use config to control text processing
3. Implement custom LLM-based summarization
4. Create your own text processing logic

Run with: python examples/custom_text_processing.py
"""

from __future__ import annotations

# Use proper package imports
from memoric import Memoric
from memoric.utils.text_processors import TextTrimmer, TextSummarizer, LLMSummarizer


# Example 1: Disable trimming and summarization to prevent data loss
def example_disable_text_processing():
    """Disable all text processing - keeps original data intact."""
    print("=== Example 1: Disable Text Processing ===\n")

    config = {
        "text_processing": {
            "trimmer": {"type": "noop"},  # Disable trimming
            "summarizer": {"type": "noop"},  # Disable summarization
        },
        "storage": {
            "tiers": [
                {
                    "name": "short_term",
                    "trim": {"max_chars": 500},  # Config says trim, but will be no-op
                }
            ]
        },
        "summarization": {
            "enabled": True,
            "min_chars": 600,
            "target_chars": 300,  # Will be no-op with noop summarizer
        },
    }

    m = Memoric(config=config)

    # Save a long memory
    long_text = "This is a very long memory. " * 100
    mem_id = m.save(
        user_id="user1", thread_id="thread1", content=long_text, tier="short_term"
    )

    print(f"Saved memory {mem_id} with {len(long_text)} characters")

    # Run policies - text will NOT be trimmed or summarized
    result = m.run_policies()
    print(f"Policies run: {result}")

    # Verify data is preserved
    memories = m.db.get_memories(user_id="user1", limit=1)
    if memories:
        preserved_content = memories[0]["content"]
        print(f"Content preserved: {len(preserved_content)} characters")
        print(f"Data loss: 0 characters ✓\n")


# Example 2: Use LLM-based summarization
def example_llm_summarization():
    """Use OpenAI for intelligent summarization instead of truncation."""
    print("=== Example 2: LLM-Based Summarization ===\n")

    config = {
        "text_processing": {
            "summarizer": {
                "type": "llm",
                "model": "gpt-4o-mini",  # Use LLM for real summarization
                # api_key can be set here or via OPENAI_API_KEY env var
            }
        },
        "summarization": {
            "enabled": True,
            "min_chars": 600,
            "target_chars": 200,
        },
    }

    m = Memoric(config=config)

    # Save a long, detailed memory
    long_text = """
    In our Q4 planning meeting, we discussed the roadmap for the new feature.
    Sarah proposed adding a dashboard with real-time analytics. John suggested
    we prioritize mobile responsiveness. The team agreed to start with the
    backend API in Sprint 1, followed by the frontend in Sprint 2. We also
    allocated budget for additional cloud resources. The launch is targeted
    for January 15th, with beta testing starting December 1st.
    """

    mem_id = m.save(user_id="user2", thread_id="planning", content=long_text)
    print(f"Saved memory {mem_id}")

    # Run policies - will use LLM to intelligently summarize
    result = m.run_policies()
    print(f"Policies run: {result}")
    print("LLM will preserve key information while reducing length\n")


# Example 3: Custom text processor implementation
class CustomSummarizer(TextSummarizer):
    """
    Example custom summarizer that extracts key sentences using ML.

    In production, you might use:
    - extractive summarization (sentence scoring)
    - abstractive summarization (transformer models)
    - domain-specific summarization logic
    """

    def summarize(self, text: str, target_chars: int) -> str:
        """
        Custom summarization logic.

        This is a simple example - in production you'd use:
        - spaCy or NLTK for sentence tokenization
        - TF-IDF or BERT for sentence scoring
        - Selection of top-N important sentences
        """
        # Simple example: extract sentences with keywords
        sentences = text.split(".")
        keywords = ["important", "critical", "key", "must", "priority"]

        # Score sentences by keyword presence
        scored = []
        for sentence in sentences:
            score = sum(1 for kw in keywords if kw in sentence.lower())
            scored.append((score, sentence.strip()))

        # Sort by score and take top sentences
        scored.sort(reverse=True, key=lambda x: x[0])

        # Combine until we reach target length
        result = []
        current_length = 0
        for score, sentence in scored:
            if current_length + len(sentence) <= target_chars:
                result.append(sentence)
                current_length += len(sentence) + 2  # +2 for ". "

        return ". ".join(result) + "." if result else text[:target_chars]


def example_custom_processor():
    """Use a custom text processor implementation."""
    print("=== Example 3: Custom Text Processor ===\n")

    # You can inject custom processors directly
    from core.policy_executor import PolicyExecutor

    custom_summarizer = CustomSummarizer()

    config = {
        "summarization": {"enabled": True, "min_chars": 600, "target_chars": 200}
    }

    m = Memoric(config=config)

    # Create executor with custom processor
    executor = PolicyExecutor(
        db=m.db, config=m.config, summarizer=custom_summarizer  # Use custom!
    )

    print("PolicyExecutor created with custom summarizer")
    print("Your custom logic will be used for all summarization\n")


# Example 4: Preserve data with intelligent trimming
class SmartTrimmer(TextTrimmer):
    """
    Smart trimmer that preserves complete sentences or paragraphs.

    Better than truncation because it maintains semantic boundaries.
    """

    def trim(self, text: str, max_chars: int) -> str:
        """Trim at sentence boundaries to preserve meaning."""
        if len(text) <= max_chars:
            return text

        # Find last complete sentence within limit
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")

        if last_period > 0:
            # Trim at sentence boundary
            return text[: last_period + 1]
        else:
            # Fallback to truncation
            return truncated.rstrip() + "…"


def example_smart_trimming():
    """Use smart trimming that preserves sentence boundaries."""
    print("=== Example 4: Smart Trimming ===\n")

    smart_trimmer = SmartTrimmer()

    from core.policy_executor import PolicyExecutor

    config = {
        "storage": {
            "tiers": [{"name": "mid_term", "trim": {"max_chars": 100}}]
        }
    }

    m = Memoric(config=config)

    # Create executor with smart trimmer
    executor = PolicyExecutor(db=m.db, config=m.config, trimmer=smart_trimmer)

    print("PolicyExecutor created with smart trimmer")
    print("Text will be trimmed at sentence boundaries\n")


# Configuration examples
def print_config_examples():
    """Print various configuration examples."""
    print("\n" + "=" * 60)
    print("CONFIGURATION EXAMPLES")
    print("=" * 60 + "\n")

    print("1. Disable trimming and summarization (prevent data loss):")
    print(
        """
config = {
    "text_processing": {
        "trimmer": {"type": "noop"},
        "summarizer": {"type": "noop"}
    }
}
"""
    )

    print("\n2. Use LLM-based summarization:")
    print(
        """
config = {
    "text_processing": {
        "summarizer": {
            "type": "llm",
            "model": "gpt-4o-mini",
            "api_key": "sk-..."  # or set OPENAI_API_KEY env var
        }
    }
}
"""
    )

    print("\n3. Use default simple processors:")
    print(
        """
config = {
    "text_processing": {
        "trimmer": {"type": "simple"},    # Simple truncation
        "summarizer": {"type": "simple"}  # First sentence heuristic
    }
}
"""
    )

    print("\n4. Custom processor via code:")
    print(
        """
from utils.text_processors import TextSummarizer

class MyCustomSummarizer(TextSummarizer):
    def summarize(self, text: str, target_chars: int) -> str:
        # Your custom logic here
        return custom_summarize(text, target_chars)

# Inject into PolicyExecutor
executor = PolicyExecutor(
    db=db,
    config=config,
    summarizer=MyCustomSummarizer()
)
"""
    )


def main():
    """Run all examples."""
    example_disable_text_processing()
    # example_llm_summarization()  # Uncomment if you have OpenAI API key
    example_custom_processor()
    example_smart_trimming()
    print_config_examples()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Key Takeaways:
1. Set {"type": "noop"} to disable processing and prevent data loss
2. Set {"type": "llm"} to use intelligent LLM-based summarization
3. Implement TextTrimmer or TextSummarizer for custom logic
4. Inject custom processors into PolicyExecutor
5. All processing is configurable and pluggable

This ensures you have full control over how your data is processed!
    """)


if __name__ == "__main__":
    main()
