from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover - optional dep
    FastAPI = None  # type: ignore

from ..core.memory_manager import Memoric


def create_app(mem: Optional[Memoric] = None):
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Please `pip install fastapi uvicorn`. ")

    app = FastAPI(title="Memoric API")
    m = mem or Memoric()

    @app.get("/memories")
    def list_memories(user_id: Optional[str] = None, thread_id: Optional[str] = None, top_k: int = 20):
        return m.retrieve(user_id=user_id, thread_id=thread_id, top_k=top_k)

    @app.post("/memories")
    def add_memory(payload: Dict[str, Any]):
        new_id = m.save(
            user_id=str(payload.get("user_id")),
            thread_id=payload.get("thread_id"),
            content=str(payload.get("content") or payload.get("message") or ""),
            metadata=payload.get("metadata"),
        )
        return {"id": new_id}

    @app.get("/clusters")
    def list_clusters(topic: Optional[str] = None, limit: int = 50):
        return m.db.get_clusters(topic=topic, limit=limit)

    return app


