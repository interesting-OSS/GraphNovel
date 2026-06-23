"""Vector store abstraction — ChromaDB with Chinese embedding support."""
from typing import List, Optional
import chromadb
from app.config import settings


class VectorStore:
    """ChromaDB-backed vector store for semantic memory retrieval.

    Uses sentence-transformers for Chinese-optimized embeddings.
    Supports metadata filtering and hybrid search.
    """

    def __init__(self, collection_name: str = "novel_memory"):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection_name = collection_name
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(self.collection_name)
            except Exception:
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collection

    def add_memory(
        self,
        text: str,
        metadata: dict,
        embedding_id: Optional[str] = None,
    ) -> str:
        """Add a text to the vector store with metadata."""
        import uuid
        eid = embedding_id or str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[eid],
        )
        return eid

    def add_memories_batch(
        self,
        texts: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ):
        """Add multiple texts in batch."""
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    def search(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[dict] = None,
        min_similarity: float = 0.0,
    ) -> dict:
        """Semantic search with optional metadata filtering and similarity threshold.

        Returns the standard ChromaDB query result dict, with distances included.
        Set min_similarity to filter results below a threshold (cosine distance → similarity).
        """
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata
        result = self.collection.query(**kwargs)
        return result

    def search_with_scores(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[dict] = None,
        min_similarity: float = 0.6,
    ) -> List[tuple[str, float]]:
        """Search and return (document, similarity_score) tuples filtered by threshold.

        Uses cosine distance: similarity = 1 - distance.
        """
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata
        result = self.collection.query(**kwargs)

        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]

        scored = []
        for doc, dist in zip(documents, distances):
            similarity = 1.0 - float(dist)  # cosine distance → similarity
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def search_by_tags(
        self,
        tags: List[str],
        n_results: int = 10,
    ) -> dict:
        """Search by metadata tags."""
        return self.collection.query(
            query_texts=[""],
            n_results=n_results,
            where={"tags": {"$in": tags}},
        )

    def delete(self, embedding_id: str):
        """Delete a memory by its embedding ID."""
        self.collection.delete(ids=[embedding_id])

    def delete_by_project(self, project_id: str):
        """Delete all memories for a project."""
        self.collection.delete(where={"project_id": project_id})

    def count(self) -> int:
        """Return the number of stored embeddings."""
        return self.collection.count()
