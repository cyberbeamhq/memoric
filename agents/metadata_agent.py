from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


class MetadataAgent:
    """Extracts lightweight metadata using OpenAI if available; otherwise returns minimal metadata.

    Expects config structure under `metadata.enrichers` and an optional OpenAI key in env.
    """

    def __init__(self, *, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key
        self.client = None
        if OpenAI is not None and api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception:
                self.client = None

    def extract(
        self,
        *,
        text: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not text:
            return {
                "topic": "",
                "category": "",
                "entities": [],
                "importance": "low",
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": session_id,
            }

        if self.client is None:
            # Fallback heuristic
            words = text.split()
            top = words[:3]
            return {
                "topic": (top[0] if top else "general").lower(),
                "category": "general",
                "entities": [],
                "importance": "medium" if len(text) > 60 else "low",
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": session_id,
            }

        prompt = (
            "Extract JSON metadata with fields: topic (string), category (string), "
            "entities (array of strings), importance (low|medium|high)."
            f"\nText: {text}\nReturn JSON only."
        )
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            content = result.choices[0].message.content  # type: ignore[attr-defined]
        except Exception:
            content = "{}"

        # Best effort JSON parse
        import json

        try:
            parsed = json.loads(content or "{}")
        except Exception:
            parsed = {}

        return {
            "topic": parsed.get("topic", "general"),
            "category": parsed.get("category", "general"),
            "entities": parsed.get("entities", []),
            "importance": parsed.get("importance", "medium"),
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_id,
        }
