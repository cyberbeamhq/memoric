"""
Vector Store Implementations - Plug-and-play vector database providers.

Memoric outsources vector search to specialized databases.
Choose the one that fits your needs:

- Pinecone: Managed, scalable, easy (recommended for production)
- Qdrant: Open-source, self-hosted, fast
- Weaviate: Open-source, GraphQL API, feature-rich
- Chroma: Open-source, lightweight, local-first
- pgvector: PostgreSQL extension, use existing DB

Each provider implements the VectorStoreProvider interface.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .interfaces import VectorStoreProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PineconeVectorStore(VectorStoreProvider):
    """
    Pinecone vector database provider.

    Managed service, highly scalable, production-ready.

    Setup:
        pip install pinecone-client
        export PINECONE_API_KEY=your-key
        export PINECONE_ENVIRONMENT=your-environment

    Example:
        store = PineconeVectorStore(
            index_name="memoric-vectors",
            dimension=1536  # OpenAI embedding dimension
        )
    """

    def __init__(
        self,
        *,
        index_name: str,
        dimension: int = 1536,
        metric: str = "cosine",
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        """
        Initialize Pinecone vector store.

        Args:
            index_name: Name of Pinecone index
            dimension: Vector dimension
            metric: Distance metric ("cosine", "euclidean", "dotproduct")
            api_key: Pinecone API key (uses PINECONE_API_KEY env var if None)
            environment: Pinecone environment (uses PINECONE_ENVIRONMENT if None)
        """
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric

        try:
            import pinecone
            self.pinecone = pinecone
        except ImportError:
            raise ImportError(
                "Pinecone not installed. Run: pip install pinecone-client"
            )

        api_key = api_key or os.getenv("PINECONE_API_KEY")
        environment = environment or os.getenv("PINECONE_ENVIRONMENT")

        if not api_key or not environment:
            raise ValueError(
                "Pinecone API key and environment required. "
                "Set PINECONE_API_KEY and PINECONE_ENVIRONMENT environment variables."
            )

        # Initialize Pinecone
        pinecone.init(api_key=api_key, environment=environment)

        # Create index if it doesn't exist
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric
            )
            logger.info(f"Created Pinecone index: {index_name}")

        self.index = pinecone.Index(index_name)
        logger.info(f"Pinecone vector store initialized: {index_name}")

    def upsert(
        self,
        *,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Insert or update vector in Pinecone."""
        try:
            self.index.upsert(vectors=[(id, vector, metadata or {})])
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector to Pinecone: {e}")
            return False

    def search(
        self,
        *,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Pinecone."""
        try:
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                filter=filter,
                include_metadata=True
            )

            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata,
                }
                for match in results.matches
            ]
        except Exception as e:
            logger.error(f"Failed to search Pinecone: {e}")
            return []

    def delete(self, id: str) -> bool:
        """Delete vector from Pinecone."""
        try:
            self.index.delete(ids=[id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Pinecone: {e}")
            return False

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get vector from Pinecone."""
        try:
            result = self.index.fetch(ids=[id])
            if id in result.vectors:
                vec = result.vectors[id]
                return {
                    "id": id,
                    "vector": vec.values,
                    "metadata": vec.metadata,
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get from Pinecone: {e}")
            return None

    def health_check(self) -> bool:
        """Check Pinecone health."""
        try:
            self.index.describe_index_stats()
            return True
        except Exception:
            return False


class QdrantVectorStore(VectorStoreProvider):
    """
    Qdrant vector database provider.

    Open-source, self-hosted, optimized for speed.

    Setup:
        pip install qdrant-client
        # Run Qdrant locally:
        docker run -p 6333:6333 qdrant/qdrant

    Example:
        store = QdrantVectorStore(
            collection_name="memoric_vectors",
            dimension=1536,
            url="http://localhost:6333"
        )
    """

    def __init__(
        self,
        *,
        collection_name: str,
        dimension: int = 1536,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            collection_name: Name of Qdrant collection
            dimension: Vector dimension
            url: Qdrant URL
            api_key: Optional API key for Qdrant Cloud
        """
        self.collection_name = collection_name
        self.dimension = dimension

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self.Distance = Distance
            self.VectorParams = VectorParams
        except ImportError:
            raise ImportError(
                "Qdrant client not installed. Run: pip install qdrant-client"
            )

        self.client = QdrantClient(url=url, api_key=api_key)

        # Create collection if it doesn't exist
        collections = self.client.get_collections().collections
        if collection_name not in [c.name for c in collections]:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

        logger.info(f"Qdrant vector store initialized: {collection_name}")

    def upsert(
        self,
        *,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Insert or update vector in Qdrant."""
        try:
            from qdrant_client.models import PointStruct

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=id,
                        vector=vector,
                        payload=metadata or {}
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert to Qdrant: {e}")
            return False

    def search(
        self,
        *,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        try:
            # Convert filter to Qdrant format if provided
            query_filter = None
            if filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                query_filter = Filter(must=conditions)

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=top_k,
                query_filter=query_filter
            )

            return [
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "metadata": hit.payload,
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Failed to search Qdrant: {e}")
            return []

    def delete(self, id: str) -> bool:
        """Delete vector from Qdrant."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")
            return False

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get vector from Qdrant."""
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id],
                with_vectors=True
            )

            if results:
                point = results[0]
                return {
                    "id": str(point.id),
                    "vector": point.vector,
                    "metadata": point.payload,
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get from Qdrant: {e}")
            return None

    def health_check(self) -> bool:
        """Check Qdrant health."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False


class InMemoryVectorStore(VectorStoreProvider):
    """
    In-memory vector store for development/testing.

    NOT for production - data is lost on restart.
    Useful for:
    - Local development
    - Testing
    - Prototyping

    Example:
        store = InMemoryVectorStore()
    """

    def __init__(self):
        """Initialize in-memory vector store."""
        self.vectors: Dict[str, Dict[str, Any]] = {}
        logger.info("In-memory vector store initialized (development only)")

    def upsert(
        self,
        *,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store vector in memory."""
        self.vectors[id] = {
            "vector": vector,
            "metadata": metadata or {}
        }
        return True

    def search(
        self,
        *,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors using cosine similarity."""
        import numpy as np

        results = []
        query_vec = np.array(vector)

        for id, data in self.vectors.items():
            # Apply filter if provided
            if filter:
                metadata = data["metadata"]
                if not all(metadata.get(k) == v for k, v in filter.items()):
                    continue

            # Compute cosine similarity
            stored_vec = np.array(data["vector"])
            similarity = np.dot(query_vec, stored_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
            )

            results.append({
                "id": id,
                "score": float(similarity),
                "metadata": data["metadata"],
            })

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete(self, id: str) -> bool:
        """Delete vector from memory."""
        if id in self.vectors:
            del self.vectors[id]
            return True
        return False

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get vector from memory."""
        if id in self.vectors:
            data = self.vectors[id]
            return {
                "id": id,
                "vector": data["vector"],
                "metadata": data["metadata"],
            }
        return None

    def health_check(self) -> bool:
        """Always healthy for in-memory store."""
        return True


__all__ = [
    "PineconeVectorStore",
    "QdrantVectorStore",
    "InMemoryVectorStore",
]
