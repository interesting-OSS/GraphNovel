"""RetrievalNode — RAG memory retrieval and context injection for LangGraph.

Injects relevant long-term memories into the current writing context before
chapter generation.  Uses ChromaDB-backed vector search with metadata filtering.

Usage:
    from app.graphs.nodes import RetrievalNode
    builder.add_node("retrieve_context", RetrievalNode())
"""
from __future__ import annotations
from typing import Optional
from app.graphs.state import NovelState
from app.memory.vector_store import VectorStore
from app.memory.memory_manager import MemoryManager
from app.logger import get_logger
import json

logger = get_logger(__name__)


class RetrievalNode:
    """LangGraph node that retrieves relevant memories for the current writing context.

    Parameters
    ----------
    memory_manager : MemoryManager, optional
        Pre-configured MemoryManager.  Creates one with default VectorStore if omitted.
    n_results : int
        Number of top-K memories to retrieve (default 10).
    query_builder : callable, optional
        (state) → str.  Builds the search query from state.
        Default: combines current chapter outline + character names.
    layers : list[str], optional
        Which memory layers to search.  Default: all layers.
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        n_results: int = 10,
        query_builder: Optional[callable] = None,
        layers: Optional[list[str]] = None,
    ):
        self._manager = memory_manager
        self.n_results = n_results
        self._query_builder = query_builder
        self.layers = layers

    @property
    def manager(self) -> MemoryManager:
        if self._manager is None:
            self._manager = MemoryManager(VectorStore())
        return self._manager

    async def __call__(self, state: NovelState) -> dict:
        """Execute retrieval and inject results into state.

        Returns state updates with ``_retrieved_memories`` key containing
        the matched memory texts and metadata.
        """
        project_id = state.get("project_id", "")
        if not project_id:
            return {"_retrieved_memories": [], "current_phase": "retrieval_skipped"}

        query = self._build_query(state)
        if not query:
            return {"_retrieved_memories": [], "current_phase": "retrieval_empty_query"}

        all_results = []

        if self.layers:
            # Search each layer independently
            for layer in self.layers:
                try:
                    layer_results = await self.manager.retrieve_by_layer(
                        project_id=project_id,
                        query=query,
                        layer=layer,
                        n_results=max(1, self.n_results // len(self.layers)),
                    )
                    all_results.extend(self._flatten_results(layer_results))
                except Exception as exc:
                    logger.warning("Retrieval from layer '%s' failed: %s", layer, exc)
        else:
            try:
                results = await self.manager.retrieve_context(
                    project_id=project_id,
                    query=query,
                    n_results=self.n_results,
                )
                all_results = self._flatten_results(results)
            except Exception as exc:
                logger.warning("Retrieval failed: %s", exc)

        # Deduplicate and sort by relevance
        seen = set()
        unique = []
        for item in all_results:
            key = item.get("content", "")[:100]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        unique = unique[:self.n_results]

        logger.info("Retrieved %d unique memories for project %s", len(unique), project_id)
        return {
            "_retrieved_memories": unique,
            "current_phase": "retrieval_complete",
        }

    # ── internals ──

    def _build_query(self, state: NovelState) -> str:
        """Build a search query from the current state."""
        if self._query_builder:
            return self._query_builder(state)

        parts = []

        # Current chapter outline
        outlines = state.get("outlines", [])
        idx = state.get("current_chapter_index", 0)
        if 0 <= idx < len(outlines):
            ol = outlines[idx]
            parts.append(ol.get("title", ""))
            parts.append(ol.get("summary", ""))
            parts.append(ol.get("key_points", ""))

        # Character names
        characters = state.get("characters", [])
        if characters:
            parts.append(" ".join(c.get("name", "") for c in characters[:5]))

        # Active foreshadows
        foreshadows = state.get("foreshadows", [])
        active_fs = [f.get("description", "") for f in foreshadows if f.get("status") == "set"]
        if active_fs:
            parts.append(" ".join(active_fs[:5]))

        query = " ".join(p for p in parts if p)
        return query[:1000]  # Limit query length

    @staticmethod
    def _flatten_results(results: dict) -> list[dict]:
        """Flatten ChromaDB query result dict into a list of {content, metadata, score} dicts."""
        flat = []
        if not results or "documents" not in results:
            return flat

        for i, doc_list in enumerate(results.get("documents", [])):
            for j, doc in enumerate(doc_list):
                meta = {}
                if results.get("metadatas") and i < len(results["metadatas"]):
                    if j < len(results["metadatas"][i]):
                        meta = results["metadatas"][i][j] or {}
                score = 1.0
                if results.get("distances") and i < len(results["distances"]):
                    if j < len(results["distances"][i]):
                        score = results["distances"][i][j]

                flat.append({
                    "content": (doc or "")[:1000],
                    "metadata": meta,
                    "score": score,
                })
        return flat


class ContextInjectionNode(RetrievalNode):
    """Extended RetrievalNode that injects results directly into the writing context.

    Instead of returning raw memory lists, this node formats retrieved
    memories as a ready-to-use prompt context string under ``_memory_context``.
    """

    async def __call__(self, state: NovelState) -> dict:
        result = await super().__call__(state)
        memories = result.get("_retrieved_memories", [])

        if not memories:
            result["_memory_context"] = "无相关历史记忆"
            return result

        lines = ["## 相关历史记忆（自动检索）"]
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", "")
            meta = mem.get("metadata", {})
            mem_type = meta.get("type", "未知")
            chapter = meta.get("chapter_index", "?")
            lines.append(
                f"{i}. [第{chapter}章 / {mem_type}] "
                f"{content[:300]}{'...' if len(content) > 300 else ''}"
            )

        result["_memory_context"] = "\n".join(lines)
        return result
