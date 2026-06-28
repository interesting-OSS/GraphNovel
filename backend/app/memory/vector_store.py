"""Vector store — ChromaDB + BAAI/bge-small-zh-v1.5 for Chinese semantic search.

Key improvements over the original:
  - Manual SentenceTransformer loading with offline-first strategy
  - Class-level shared model (one model for all projects)
  - Per-project collection isolation via SHA256 hash
  - Batch encoding + batch write (5-10x faster)
  - Similarity-filtered search
  - Async wrappers via asyncio.to_thread() for non-blocking usage in FastAPI
"""
import asyncio
import hashlib
import uuid
import logging
from pathlib import Path
from typing import List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


def _find_model_cache_dir() -> str:
    """Locate the embedding model cache directory.

    Priority:
      1. SENTENCE_TRANSFORMERS_HOME env var
      2. Project-root /backend/embedding/
      3. chroma_persist_dir / embedding_models/ (auto-created)
    """
    import os
    env_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME")
    if env_dir and Path(env_dir).exists():
        return env_dir
    project_embedding = Path(settings.chroma_persist_dir).parent / "embedding"
    if project_embedding.exists():
        return str(project_embedding)
    fallback = Path(settings.chroma_persist_dir) / "embedding_models"
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback)


class VectorStore:
    """ChromaDB-backed vector store with Chinese-optimized embeddings.

    - Uses BAAI/bge-small-zh-v1.5 for Chinese semantic retrieval
    - Each project gets its own ChromaDB collection (physical isolation)
    - Embedding model is shared at class level (load once, use everywhere)
    """

    _shared_model: Optional[SentenceTransformer] = None
    _shared_model_name: Optional[str] = None

    def __init__(
        self,
        project_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.project_id = project_id
        self._model_name = model_name or settings.embedding_model
        self._collection_name = (
            self._make_collection_name(project_id) if project_id
            else "novel_memory"
        )
        self._collection = None

    # ── Collection naming ────────────────────────────────────────────────

    @staticmethod
    def _make_collection_name(project_id: str) -> str:
        """SHA256 hash → 12 hex chars to keep ChromaDB names short."""
        h = hashlib.sha256(project_id.encode()).hexdigest()[:12]
        return f"novel_{h}"

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(self._collection_name)
            except Exception:
                self._collection = self.client.create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("Created ChromaDB collection: %s", self._collection_name)
        return self._collection

    # ── Embedding model (class-level shared, lazy-loaded) ────────────────

    @classmethod
    def _load_model(cls, model_name: str) -> SentenceTransformer:
        """Load embedding model — offline first, online fallback."""
        if cls._shared_model is not None and cls._shared_model_name == model_name:
            return cls._shared_model

        cache_dir = _find_model_cache_dir()
        logger.info("Loading embedding model: %s (cache: %s)", model_name, cache_dir)

        try:
            cls._shared_model = SentenceTransformer(
                model_name, cache_folder=cache_dir,
                device="cpu", local_files_only=True,
            )
            logger.info("Embedding model loaded (offline)")
        except Exception:
            logger.info("Offline load failed, downloading...")
            cls._shared_model = SentenceTransformer(
                model_name, cache_folder=cache_dir,
                device="cpu", local_files_only=False,
            )
            logger.info("Embedding model loaded (online)")

        cls._shared_model_name = model_name
        return cls._shared_model

    @property
    def model(self) -> SentenceTransformer:
        return self._load_model(self._model_name)

    def encode(self, text: str) -> list[float]:
        """Encode a single text to embedding vector."""
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode texts (much faster than one-by-one)."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    # ── CRUD ─────────────────────────────────────────────────────────────

    def add_memory(
        self, text: str, metadata: dict,
        embedding_id: Optional[str] = None,
    ) -> str:
        """Add a single memory with explicit embedding."""
        eid = embedding_id or str(uuid.uuid4())
        embedding = self.encode(text)
        self.collection.add(
            documents=[text], embeddings=[embedding],
            metadatas=[metadata], ids=[eid],
        )
        return eid

    def add_memories_batch(
        self, texts: list[str], metadatas: list[dict],
        ids: Optional[list[str]] = None,
    ):
        """Batch add memories — one encode + one write (5-10x faster)."""
        if not texts:
            return
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        embeddings = self.encode_batch(texts)
        self.collection.add(
            documents=texts, embeddings=embeddings,
            metadatas=metadatas, ids=ids,
        )
        logger.info("Batch added %d memories", len(texts))

    # ── Search ───────────────────────────────────────────────────────────

    def search(
        self, query: str, n_results: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> dict:
        """Semantic search with explicit query embedding."""
        query_embedding = self.encode(query)
        kwargs = {"query_embeddings": [query_embedding], "n_results": n_results}
        if filter_metadata:
            kwargs["where"] = filter_metadata
        return self.collection.query(**kwargs)

    def search_with_scores(
        self, query: str, n_results: int = 10,
        filter_metadata: Optional[dict] = None,
        min_similarity: float = 0.6,
    ) -> list[tuple[str, float]]:
        """Search returning (document, similarity) filtered by threshold."""
        query_embedding = self.encode(query)
        kwargs = {"query_embeddings": [query_embedding], "n_results": n_results}
        if filter_metadata:
            kwargs["where"] = filter_metadata
        result = self.collection.query(**kwargs)

        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]

        scored = []
        for doc, dist in zip(documents, distances):
            similarity = 1.0 - float(dist)
            if similarity >= min_similarity:
                scored.append((doc, similarity))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ── Management ───────────────────────────────────────────────────────

    def delete(self, embedding_id: str):
        self.collection.delete(ids=[embedding_id])

    def delete_by_project(self, project_id: str):
        self.collection.delete(where={"project_id": project_id})

    def count(self) -> int:
        return self.collection.count()

    def get_stats(self) -> dict:
        """Get collection statistics for observability."""
        return {
            "collection_name": self._collection_name,
            "project_id": self.project_id,
            "count": self.count(),
            "model_name": self._model_name,
        }

    # ── Async wrappers (non-blocking in FastAPI event loop) ─────────────

    async def add_memory_async(self, text: str, metadata: dict,
                                embedding_id: Optional[str] = None) -> str:
        """Async: add a single memory via thread pool."""
        return await asyncio.to_thread(self.add_memory, text, metadata, embedding_id)

    async def add_memories_batch_async(self, texts: list[str], metadatas: list[dict],
                                        ids: Optional[list[str]] = None):
        """Async: batch add memories via thread pool."""
        return await asyncio.to_thread(self.add_memories_batch, texts, metadatas, ids)

    async def search_async(self, query: str, n_results: int = 10,
                            filter_metadata: Optional[dict] = None) -> dict:
        """Async: semantic search via thread pool."""
        return await asyncio.to_thread(self.search, query, n_results, filter_metadata)

    async def search_with_scores_async(self, query: str, n_results: int = 10,
                                        filter_metadata: Optional[dict] = None,
                                        min_similarity: float = 0.6) -> list[tuple[str, float]]:
        """Async: scored search via thread pool."""
        return await asyncio.to_thread(
            self.search_with_scores, query, n_results, filter_metadata, min_similarity)

    async def delete_async(self, embedding_id: str):
        """Async: delete by ID via thread pool."""
        return await asyncio.to_thread(self.delete, embedding_id)

    async def delete_by_project_async(self, project_id: str):
        """Async: delete by project via thread pool."""
        return await asyncio.to_thread(self.delete_by_project, project_id)

    async def count_async(self) -> int:
        """Async: get count via thread pool."""
        return await asyncio.to_thread(self.count)
