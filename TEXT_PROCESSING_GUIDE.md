# Text Processing Guide - Memoric

**Preventing Data Loss Through Configurable Text Processing**

---

## Overview

Memoric processes text in two ways during policy execution:
1. **Trimming**: Shortening long content in specific tiers
2. **Summarization**: Condensing verbose memories

**Important**: By default, these operations use simple heuristics (truncation) which can cause data loss. This guide shows you how to:
- Disable processing to preserve all data
- Use LLM-based intelligent summarization
- Implement custom processing logic

---

## Quick Start: Prevent Data Loss

### Option 1: Disable All Text Processing

```python
from memoric.core.memory_manager import Memoric

config = {
    "text_processing": {
        "trimmer": {"type": "noop"},      # Disable trimming
        "summarizer": {"type": "noop"}    # Disable summarization
    }
}

m = Memoric(config=config)
# All text will be preserved exactly as provided
```

### Option 2: Use LLM-Based Summarization

```python
config = {
    "text_processing": {
        "summarizer": {
            "type": "llm",
            "model": "gpt-4o-mini",
            # API key from env var OPENAI_API_KEY or specify here:
            # "api_key": "sk-..."
        }
    }
}

m = Memoric(config=config)
# Text will be intelligently summarized, preserving key information
```

---

## Configuration Options

### Text Processing Configuration Structure

```yaml
text_processing:
  trimmer:
    type: simple | noop | custom
    # Additional options depend on type

  summarizer:
    type: simple | noop | llm | custom
    # Additional options depend on type
```

### Trimmer Types

#### 1. `noop` - No Operation (Recommended for Data Preservation)

```python
"trimmer": {"type": "noop"}
```

**Behavior**: Does nothing - preserves all text unchanged.

**Use When**:
- You want to preserve all data
- Storage is not a concern
- You handle trimming elsewhere

#### 2. `simple` - Simple Truncation (Default)

```python
"trimmer": {"type": "simple"}
```

**Behavior**: Truncates text at max_chars with ellipsis (…).

**Pros**:
- Fast and simple
- Predictable behavior

**Cons**:
- **Data loss**: Text is cut off
- May break mid-sentence
- No intelligence

**Example**:
```python
Input:  "This is a very long sentence that needs to be trimmed."
Output: "This is a very long sen…"  # at 25 chars
```

### Summarizer Types

#### 1. `noop` - No Operation (Recommended for Data Preservation)

```python
"summarizer": {"type": "noop"}
```

**Behavior**: Does nothing - preserves all text unchanged.

**Use When**:
- You want to preserve all data
- You don't want automatic summarization

#### 2. `simple` - Heuristic Summarization (Default)

```python
"summarizer": {"type": "simple"}
```

**Behavior**: Returns first sentence if it fits, otherwise truncates.

**Pros**:
- Fast
- No external dependencies

**Cons**:
- **Not real summarization** - just truncation
- Loses important information
- No semantic understanding

**Warning**: This is **not** AI-powered summarization. Use `llm` type for real summarization.

#### 3. `llm` - LLM-Based Summarization (Recommended)

```python
"summarizer": {
    "type": "llm",
    "model": "gpt-4o-mini",  # or "gpt-4", "gpt-3.5-turbo"
    "api_key": "sk-..."      # optional, uses OPENAI_API_KEY env var
}
```

**Behavior**: Uses OpenAI API to intelligently summarize text.

**Pros**:
- **Real summarization** - preserves key information
- Semantic understanding
- Maintains context and important details

**Cons**:
- Requires OpenAI API key
- Costs money (small amount per call)
- Slower than simple methods

**Example**:
```python
Input: """
In our Q4 meeting, we discussed the roadmap. Sarah proposed a dashboard
with real-time analytics. John suggested mobile responsiveness. We agreed
to start with backend API in Sprint 1, frontend in Sprint 2. Launch
targeted for January 15th.
"""

Output: "Q4 roadmap: Dashboard with analytics (Sarah), mobile responsiveness
(John). Backend Sprint 1, frontend Sprint 2. Launch Jan 15."
```

---

## Custom Implementation

### Creating a Custom Trimmer

```python
from memoric.utils.text_processors import TextTrimmer

class SmartTrimmer(TextTrimmer):
    """Trims at sentence boundaries to preserve meaning."""

    def trim(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text

        # Find last complete sentence within limit
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")

        if last_period > 0:
            return text[:last_period + 1]
        else:
            return truncated.rstrip() + "…"

# Use it
from memoric.core.policy_executor import PolicyExecutor

executor = PolicyExecutor(
    db=db,
    config=config,
    trimmer=SmartTrimmer()  # Inject custom trimmer
)
```

### Creating a Custom Summarizer

```python
from memoric.utils.text_processors import TextSummarizer

class KeywordSummarizer(TextSummarizer):
    """Extracts sentences with important keywords."""

    def __init__(self, keywords=None):
        self.keywords = keywords or ["important", "critical", "key"]

    def summarize(self, text: str, target_chars: int) -> str:
        sentences = text.split(".")

        # Score by keyword presence
        scored = []
        for s in sentences:
            score = sum(1 for kw in self.keywords if kw in s.lower())
            scored.append((score, s.strip()))

        # Take top sentences
        scored.sort(reverse=True, key=lambda x: x[0])
        result = []
        length = 0

        for score, sentence in scored:
            if length + len(sentence) <= target_chars:
                result.append(sentence)
                length += len(sentence)

        return ". ".join(result) + "."

# Use it
executor = PolicyExecutor(
    db=db,
    config=config,
    summarizer=KeywordSummarizer(keywords=["urgent", "deadline", "critical"])
)
```

### Using Third-Party Libraries

```python
from memoric.utils.text_processors import TextSummarizer

class TransformerSummarizer(TextSummarizer):
    """Uses Hugging Face transformers for summarization."""

    def __init__(self, model_name="facebook/bart-large-cnn"):
        from transformers import pipeline
        self.summarizer = pipeline("summarization", model=model_name)

    def summarize(self, text: str, target_chars: int) -> str:
        # Calculate approximate max_length in tokens
        max_length = target_chars // 4  # rough estimate

        result = self.summarizer(
            text,
            max_length=max_length,
            min_length=max_length // 2,
            do_sample=False
        )

        return result[0]['summary_text']

# Use it
executor = PolicyExecutor(
    db=db,
    config=config,
    summarizer=TransformerSummarizer()
)
```

---

## Configuration Examples

### Example 1: Production Setup (Preserve Data)

```yaml
# config.yaml
text_processing:
  trimmer:
    type: noop  # Never trim - storage is cheap

  summarizer:
    type: llm
    model: gpt-4o-mini
    # Uses OPENAI_API_KEY from environment

storage:
  tiers:
    - name: short_term
      # Trim config present but will be no-op
      trim:
        max_chars: 5000

summarization:
  enabled: true
  min_chars: 1000
  target_chars: 500
```

### Example 2: Cost-Optimized (Simple Processing)

```yaml
# config.yaml
text_processing:
  trimmer:
    type: simple  # Use simple truncation

  summarizer:
    type: simple  # Use heuristic (no API costs)

storage:
  tiers:
    - name: mid_term
      trim:
        max_chars: 2000

summarization:
  enabled: true
  min_chars: 600
  target_chars: 300
```

### Example 3: Hybrid Approach

```yaml
# config.yaml
text_processing:
  trimmer:
    type: noop  # Never trim

  summarizer:
    type: llm  # Use LLM for summarization only
    model: gpt-4o-mini

# This preserves trimmed content but intelligently summarizes
```

---

## Policy Configuration Impact

### Tier Trim Policy

```yaml
storage:
  tiers:
    - name: mid_term
      trim:
        max_chars: 2000
```

When policies run:
- Memories in `mid_term` tier are checked
- If content > 2000 chars, `trimmer.trim(content, 2000)` is called
- Result depends on your trimmer type

### Global Summarization Policy

```yaml
summarization:
  enabled: true
  min_chars: 600
  target_chars: 300
  mark_summarized: true
```

When policies run:
- All memories with content >= 600 chars are processed
- `summarizer.summarize(content, 300)` is called
- Memories are marked as summarized to avoid re-processing

---

## Best Practices

### 1. **Default to No-Op for Production**

```python
# Start with preservation, add processing later if needed
config = {
    "text_processing": {
        "trimmer": {"type": "noop"},
        "summarizer": {"type": "noop"}
    }
}
```

**Why**: You can always summarize later, but you can't recover lost data.

### 2. **Use LLM Summarization if Enabled**

```python
# If you must summarize, use intelligent methods
config = {
    "text_processing": {
        "summarizer": {
            "type": "llm",
            "model": "gpt-4o-mini"
        }
    }
}
```

**Why**: Preserves more information than truncation.

### 3. **Test Processing on Sample Data**

```python
# Test your processors before production
trimmer = create_trimmer(config["text_processing"]["trimmer"])
sample = "Your sample text here..."
result = trimmer.trim(sample, 100)
print(f"Original: {len(sample)} chars → Result: {len(result)} chars")
print(f"Data preserved: {result}")
```

### 4. **Monitor Data Loss**

```python
# Log when trimming/summarization occurs
original_length = len(original_content)
processed = trimmer.trim(original_content, max_chars)
processed_length = len(processed)

if processed_length < original_length:
    logger.warning(
        f"Trimmed memory {memory_id}: {original_length} → {processed_length} chars "
        f"({original_length - processed_length} chars lost)"
    )
```

### 5. **Provide User Control**

```python
# Let users choose their processing preference
user_preference = get_user_config(user_id)

if user_preference.get("preserve_data"):
    config["text_processing"]["trimmer"] = {"type": "noop"}
    config["text_processing"]["summarizer"] = {"type": "noop"}
```

---

## API Reference

### TextTrimmer Abstract Class

```python
class TextTrimmer(ABC):
    @abstractmethod
    def trim(self, text: str, max_chars: int) -> str:
        """Trim text to maximum characters."""
        pass
```

**Implementations**:
- `NoOpTrimmer` - Does nothing
- `SimpleTrimmer` - Truncates with ellipsis

### TextSummarizer Abstract Class

```python
class TextSummarizer(ABC):
    @abstractmethod
    def summarize(self, text: str, target_chars: int) -> str:
        """Summarize text to target length."""
        pass
```

**Implementations**:
- `NoOpSummarizer` - Does nothing
- `SimpleSummarizer` - First sentence or truncation
- `LLMSummarizer` - OpenAI-based summarization

### Factory Functions

```python
def create_trimmer(config: dict) -> TextTrimmer:
    """Create trimmer from config dict."""

def create_summarizer(config: dict) -> TextSummarizer:
    """Create summarizer from config dict."""
```

---

## Examples

See [examples/custom_text_processing.py](examples/custom_text_processing.py) for complete runnable examples:

1. Disabling text processing
2. LLM-based summarization
3. Custom processor implementation
4. Smart sentence-boundary trimming

---

## Migration Guide

### Upgrading from Simple Processing

**Before** (data loss):
```python
# Old config - uses simple truncation
config = {
    "storage": {
        "tiers": [
            {"name": "mid_term", "trim": {"max_chars": 1000}}
        ]
    }
}
```

**After** (data preserved):
```python
# New config - explicit no-op
config = {
    "text_processing": {
        "trimmer": {"type": "noop"}  # Add this!
    },
    "storage": {
        "tiers": [
            {"name": "mid_term", "trim": {"max_chars": 1000}}
        ]
    }
}
```

### Adding LLM Summarization

```python
# Add to existing config
config["text_processing"] = {
    "summarizer": {
        "type": "llm",
        "model": "gpt-4o-mini"
    }
}

# Set OPENAI_API_KEY environment variable
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

---

## FAQ

**Q: What happens if I don't specify text_processing config?**

A: Default behavior uses `SimpleTrimmer` and `SimpleSummarizer` (simple truncation). **This may cause data loss**.

**Q: Can I disable trimming but keep summarization?**

A: Yes!
```python
config = {
    "text_processing": {
        "trimmer": {"type": "noop"},      # Disable
        "summarizer": {"type": "llm"}     # Enable
    }
}
```

**Q: How much does LLM summarization cost?**

A: With `gpt-4o-mini`:
- ~$0.15 per 1M input tokens
- ~$0.60 per 1M output tokens
- A 1000-char summary costs ~$0.0003

**Q: Can I use my own LLM endpoint?**

A: Yes! Implement `TextSummarizer` and call your endpoint in `summarize()`.

**Q: What if OpenAI API is unavailable?**

A: `LLMSummarizer` automatically falls back to `SimpleSummarizer` on errors.

**Q: Can I change processing per user?**

A: Yes! Create different `PolicyExecutor` instances with different processors per user.

---

## Summary

🎯 **Key Takeaways**:

1. **Default behavior may lose data** - use `noop` type to prevent this
2. **LLM summarization preserves information** - use `llm` type for production
3. **Everything is pluggable** - implement custom `TextTrimmer`/`TextSummarizer`
4. **Config-driven** - change behavior without code changes
5. **User choice** - let users control their data processing

✅ **Recommended Setup**:

```python
config = {
    "text_processing": {
        "trimmer": {"type": "noop"},        # Never lose data
        "summarizer": {
            "type": "llm",                   # Intelligent compression
            "model": "gpt-4o-mini"
        }
    }
}
```

---

**Questions?** See [examples/custom_text_processing.py](examples/custom_text_processing.py) for working code.
