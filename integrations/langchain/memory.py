from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from langchain.memory.chat_memory import BaseChatMemory  # type: ignore
except Exception:  # pragma: no cover
    BaseChatMemory = object  # type: ignore

from ...core.memory_manager import Memoric


class MemoricMemory(BaseChatMemory):  # type: ignore[misc]
    def __init__(self, *, user_id: str, thread_id: str, memoric: Optional[Memoric] = None, k: int = 10) -> None:
        super().__init__()
        self.user_id = user_id
        self.thread_id = thread_id
        self.mem = memoric or Memoric()
        self.k = k

    @property
    def memory_variables(self):  # type: ignore[override]
        return ["history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        records = self.mem.retrieve(user_id=self.user_id, thread_id=self.thread_id, top_k=self.k)
        history = "\n".join([r.get("content", "") for r in records])
        return {"history": history}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:  # type: ignore[override]
        text = str(outputs.get("response") or outputs.get("output") or "")
        if text:
            self.mem.save(user_id=self.user_id, thread_id=self.thread_id, content=text)

    def clear(self) -> None:  # type: ignore[override]
        # no-op; clearing would be destructive to Memoric's store
        return None


