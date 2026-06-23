"""Memory Manager — layered memory system for long-form novel writing."""
from typing import List, Optional
from app.memory.vector_store import VectorStore


class MemoryManager:
    """Manages the layered memory architecture for novel creation.

    Three layers:
    - Short-term: Current chapter full context
    - Mid-term: Current volume plot summaries
    - Long-term: Full-text key event index + character state changes

    All layers backed by ChromaDB vector store for semantic retrieval.
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()

    async def add_chapter_memory(
        self,
        project_id: str,
        chapter_id: str,
        chapter_index: int,
        content: str,
        summary: str,
        plot_points: List[dict],
        character_changes: List[dict],
        foreshadows: List[dict],
    ) -> List[str]:
        """Add a chapter's content and analysis to the memory system.

        Creates multiple embeddings at different memory layers.
        Returns list of embedding IDs.
        """
        embedding_ids = []

        # Short-term: Full chapter key excerpts
        if content:
            excerpts = self._split_content(content, max_chars=2000)
            for i, excerpt in enumerate(excerpts):
                eid = self.vector_store.add_memory(
                    text=excerpt,
                    metadata={
                        "project_id": project_id,
                        "chapter_id": chapter_id,
                        "chapter_index": chapter_index,
                        "memory_layer": "short_term",
                        "type": "chapter_excerpt",
                        "part": i,
                    },
                )
                embedding_ids.append(eid)

        # Mid-term: Chapter summary
        if summary:
            eid = self.vector_store.add_memory(
                text=summary,
                metadata={
                    "project_id": project_id,
                    "chapter_id": chapter_id,
                    "chapter_index": chapter_index,
                    "memory_layer": "mid_term",
                    "type": "chapter_summary",
                },
            )
            embedding_ids.append(eid)

        # Long-term: Plot points
        for point in plot_points:
            eid = self.vector_store.add_memory(
                text=point.get("description", ""),
                metadata={
                    "project_id": project_id,
                    "chapter_id": chapter_id,
                    "chapter_index": chapter_index,
                    "memory_layer": "long_term",
                    "type": "plot_point",
                    "importance": point.get("importance", 0.5),
                },
            )
            embedding_ids.append(eid)

        # Character state changes
        for change in character_changes:
            eid = self.vector_store.add_memory(
                text=change.get("description", ""),
                metadata={
                    "project_id": project_id,
                    "chapter_id": chapter_id,
                    "chapter_index": chapter_index,
                    "memory_layer": "long_term",
                    "type": "character_change",
                    "character_id": change.get("character_id", ""),
                },
            )
            embedding_ids.append(eid)

        # Foreshadows
        for fs in foreshadows:
            eid = self.vector_store.add_memory(
                text=fs.get("description", ""),
                metadata={
                    "project_id": project_id,
                    "chapter_id": chapter_id,
                    "chapter_index": chapter_index,
                    "memory_layer": "long_term",
                    "type": "foreshadow",
                    "foreshadow_id": fs.get("id", ""),
                    "status": fs.get("status", "pending"),
                },
            )
            embedding_ids.append(eid)

        return embedding_ids

    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        n_results: int = 10,
    ) -> dict:
        """Retrieve relevant memories for the current writing context."""
        results = self.vector_store.search(
            query=query,
            n_results=n_results,
            filter_metadata={"project_id": project_id},
        )
        return results

    async def retrieve_context_with_scores(
        self,
        project_id: str,
        query: str,
        n_results: int = 10,
        min_similarity: float = 0.6,
    ) -> list:
        """Retrieve memories with similarity scores, filtered by threshold.

        Returns list of (document, similarity_score) tuples.
        """
        return self.vector_store.search_with_scores(
            query=query,
            n_results=n_results,
            filter_metadata={"project_id": project_id},
            min_similarity=min_similarity,
        )

    async def retrieve_by_layer(
        self,
        project_id: str,
        query: str,
        layer: str,
        n_results: int = 10,
    ) -> dict:
        """Retrieve memories from a specific layer (short_term/mid_term/long_term)."""
        return self.vector_store.search(
            query=query,
            n_results=n_results,
            filter_metadata={
                "project_id": project_id,
                "memory_layer": layer,
            },
        )

    async def delete_project_memories(self, project_id: str):
        """Delete all memories for a project."""
        self.vector_store.delete_by_project(project_id)

    @staticmethod
    def _split_content(text: str, max_chars: int = 2000) -> List[str]:
        """Split long text into chunks."""
        if len(text) <= max_chars:
            return [text]
        chunks = []
        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars]
            if chunk:
                chunks.append(chunk)
        return chunks
