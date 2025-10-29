from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI
    from fastapi.responses import Response
except Exception:  # pragma: no cover - optional dep
    FastAPI = Response = None  # type: ignore

from ..core.memory_manager import Memoric

# Try to import Prometheus client
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = CONTENT_TYPE_LATEST = None


def create_app(mem: Optional[Memoric] = None, enable_metrics: bool = True):
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Please `pip install fastapi uvicorn`. ")

    app = FastAPI(title="Memoric API")
    m = mem or Memoric()

    @app.get("/")
    def root():
        """Health check endpoint."""
        return {"status": "ok", "service": "memoric-api"}

    @app.get("/memories")
    def list_memories(
        user_id: Optional[str] = None, thread_id: Optional[str] = None, top_k: int = 20
    ):
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
    def list_clusters(user_id: str, topic: Optional[str] = None, limit: int = 50):
        """List clusters for a specific user.

        Args:
            user_id: User ID (required for privacy/isolation)
            topic: Optional topic filter
            limit: Maximum number of clusters to return

        Returns:
            List of clusters for the user
        """
        return m.db.get_clusters(user_id=user_id, topic=topic, limit=limit)

    @app.post("/policies/run")
    def run_policies():
        """Execute all configured memory policies."""
        results = m.run_policies()
        return results

    # Prometheus metrics endpoint
    if enable_metrics and PROMETHEUS_AVAILABLE:
        @app.get("/metrics")
        def metrics():
            """Prometheus metrics endpoint."""
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )

    return app


# Default app instance
app = create_app()
