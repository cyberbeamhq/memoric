from __future__ import annotations

# Unified SDK entrypoint
from .core.memory_manager import Memoric as Memoric  # re-export

# Advanced users may import these as needed
from .agents.metadata_agent import MetadataAgent as MetadataAgent  # noqa: F401
from .core.retriever import Retriever as Retriever  # noqa: F401
from .db.postgres_connector import PostgresConnector as PostgresConnector  # noqa: F401

__all__ = [
    "Memoric",
    "MetadataAgent",
    "Retriever",
    "PostgresConnector",
]


