"""RTCO Context Builder — priority-layered context assembly with token budget.

Implements the Readiness-To-Content-Optimization (RTCO) framework:

  P0（核心 ≈40% budget）: 当前章节大纲 + 上一章全文(衔接锚点) + 字数要求
  P1（重要 ≈35% budget）: 相关角色卡(含职业/关系/心理) + 情感基调
  P2（参考 ≈25% budget）: 向量记忆(相似度>0.6) + 伏笔提醒(按紧急度排序)

当 token 预算紧张时，低优先级内容会被截断而非全部丢弃，
确保核心写作信息永不丢失。
"""
from enum import Enum
from typing import List, Optional


class ContextPriority(Enum):
    P0_CORE = 0       # Must not truncate
    P1_IMPORTANT = 1  # Can lightly truncate
    P2_REFERENCE = 2  # Can heavily truncate / drop


# Rough estimate: 1 Chinese character ≈ 1.5 tokens
_CHAR_TO_TOKEN_RATIO = 1.5
_DEFAULT_TOKEN_BUDGET = 24000  # Reserve ~24K tokens for context (out of 128K window)


def _estimate_tokens(text: str) -> int:
    """Rough token count for Chinese text (char-based)."""
    return int(len(text) * _CHAR_TO_TOKEN_RATIO)


def _trim_text(text: str, max_chars: int) -> str:
    """Trim text to max_chars, keeping whole sentences where possible."""
    if len(text) <= max_chars:
        return text
    # Find last sentence break within limit
    cut = text.rfind("。", max(0, max_chars - 200), max_chars)
    if cut == -1:
        cut = text.rfind("\n", max(0, max_chars - 200), max_chars)
    if cut == -1:
        cut = max_chars
    return text[:cut] + "…[已截断]"


class ContextBuilder:
    """Assembles a priority-layered context window for chapter generation.

    Usage:
        ctx = ContextBuilder()
        result = ctx.build_prioritized_context(
            world_setting=...,
            characters=...,
            outlines=...,
            current_chapter_index=5,
            active_foreshadows=...,
            previous_chapter_content=...,
            retrieved_memories_with_scores=...,
            token_budget=20000,
        )
    """

    def __init__(self, memory_similarity_threshold: float = 0.6):
        self.similarity_threshold = memory_similarity_threshold

    # ── P0 Core builders (must not truncate) ──────────────────────────

    @staticmethod
    def build_outline_context(outlines: List[dict], current_index: int) -> str:
        """P0: Current outline + immediate neighbors."""
        if not outlines:
            return "暂无大纲"

        lines = []
        start = max(0, current_index - 2)
        end = min(len(outlines), current_index + 3)

        for i in range(start, end):
            ol = outlines[i]
            marker = " → 【当前】" if i == current_index else ""
            lines.append(
                f"第{ol.get('volume', 1)}卷 第{ol.get('chapter_index', ol.get('chapter_num', i + 1))}章 "
                f"《{ol.get('title', '未命名')}》{marker}\n"
                f"  摘要: {ol.get('summary', '无')}\n"
                f"  要点: {ol.get('key_points', '无')}\n"
                f"  目标字数: {ol.get('target_words', 3000)}字"
            )
        return "\n\n".join(lines)

    @staticmethod
    def build_previous_chapter_context(content: Optional[str]) -> str:
        """P0: Previous chapter as continuity anchor (up to 8K tokens)."""
        if not content:
            return "这是第一章，无前文"
        # Keep last ~5000 chars for Chinese text ≈ 7.5K tokens
        return _trim_text(content, 5000)

    # ── P1 Important builders (can lightly truncate) ─────────────────

    @staticmethod
    def build_characters_context(
        characters: List[dict],
        relevant_ids: Optional[List[str]] = None,
        max_chars_per_character: int = 300,
    ) -> str:
        """P1: Scene-relevant characters with career + relationships + mental state."""
        if not characters:
            return "暂无角色信息"

        filtered = characters
        if relevant_ids:
            filtered = [c for c in characters if c.get("id") in relevant_ids]

        if not filtered:
            filtered = characters[:5]

        lines = []
        for char in filtered:
            career_info = ""
            if char.get("career_id"):
                career_info = f" | 职业ID: {char.get('career_id')}"
            org_info = ""
            if char.get("organization_id"):
                org_info = f" | 组织ID: {char.get('organization_id')}"

            lines.append(
                f"- {char.get('name', '未知')}（{char.get('role_type', '配角')}）"
                f" | 性别: {char.get('gender', '未知')}"
                f" | 性格: {char.get('personality', '未知')}"
                f" | 心理: {char.get('mental_state', '正常')}"
                f"{career_info}{org_info}"
                f" | 目标: {char.get('goals', '无')}"
            )

            bg = char.get("background", "")
            if bg:
                lines.append(f"  背景: {_trim_text(bg, max_chars_per_character)}")

            secrets = char.get("secrets", "")
            if secrets:
                lines.append(f"  秘密: {_trim_text(secrets, 150)}")

        return "\n".join(lines)

    @staticmethod
    def build_world_summary(world_setting: dict) -> str:
        """P1: Compact world setting summary."""
        if not world_setting:
            return "暂无世界观设定"

        parts = []
        mapping = {
            "time_period": "时代背景",
            "geography": "地理版图",
            "power_system": "力量体系",
            "factions": "势力格局",
            "culture": "文化风俗",
            "rules": "世界规则",
        }
        for key, label in mapping.items():
            value = world_setting.get(key, "")
            if value:
                parts.append(f"【{label}】{_trim_text(value, 200)}")
        return "\n".join(parts) if parts else "暂无世界观设定"

    # ── P2 Reference builders (can heavily truncate / drop) ──────────

    def build_retrieved_memories_context(
        self,
        memories_with_scores: Optional[List[tuple[str, float]]] = None,
        max_items: int = 8,
    ) -> str:
        """P2: Vector-retrieved memories filtered by similarity threshold.

        Args:
            memories_with_scores: List of (text, similarity_score) tuples.
            max_items: Max number of memories to include.
        """
        if not memories_with_scores:
            return "无相关历史记忆"

        # Filter by similarity threshold
        qualified = [
            (text, score) for text, score in memories_with_scores
            if score >= self.similarity_threshold
        ]

        if not qualified:
            return "无足够相关的历史记忆（均低于相似度阈值）"

        # Sort by score descending, take top N
        qualified.sort(key=lambda x: x[1], reverse=True)
        qualified = qualified[:max_items]

        lines = []
        for i, (text, score) in enumerate(qualified):
            trimmed = _trim_text(text, 300)
            lines.append(f"[记忆{i + 1}|相关度{score:.2f}] {trimmed}")

        return "\n".join(lines)

    @staticmethod
    def build_foreshadow_context(
        foreshadows: List[dict],
        current_chapter_index: int,
    ) -> str:
        """P2: Urgency-prioritized foreshadow reminders.

        Urgency tiers:
          1. Overdue (target < current) → highest urgency
          2. Due this chapter (target == current)
          3. Upcoming (target <= current + 5)
          4. Active but distant
        """
        if not foreshadows:
            return "暂无活跃伏笔"

        active = [f for f in foreshadows if f.get("status") in ("set", "pending")]
        if not active:
            return "暂无活跃伏笔"

        # Classify by urgency
        overdue = []
        due_now = []
        upcoming = []
        distant = []

        for fs in active:
            target = fs.get("target_chapter_index") or fs.get("remind_deadline")
            if target is None:
                distant.append(fs)
            elif target < current_chapter_index:
                overdue.append(fs)
            elif target == current_chapter_index:
                due_now.append(fs)
            elif target <= current_chapter_index + 5:
                upcoming.append(fs)
            else:
                distant.append(fs)

        lines = []

        if overdue:
            lines.append("⚠️ 已过期（需在本章回收）：")
            for fs in overdue:
                lines.append(f"  - [{fs.get('category', '未分类')}] {fs.get('description', '')} "
                            f"(预计第{fs.get('target_chapter_index', '?')}章)")
            lines.append("")

        if due_now:
            lines.append("🔴 本章必须回收：")
            for fs in due_now:
                lines.append(f"  - [{fs.get('category', '未分类')}] {fs.get('description', '')}")
            lines.append("")

        if upcoming:
            lines.append("🟡 近期伏笔：")
            for fs in upcoming[:5]:
                lines.append(f"  - [{fs.get('category', '未分类')}] {fs.get('description', '')} "
                            f"(第{fs.get('target_chapter_index', '?')}章)")
            lines.append("")

        if distant and len(lines) < 15:
            lines.append("🔵 活跃伏笔：")
            for fs in distant[:8]:
                lines.append(f"  - [{fs.get('category', '未分类')}] {fs.get('description', '')}")

        return "\n".join(lines) if lines else "暂无活跃伏笔"

    # ── Prioritized assembly ───────────────────────────────────────────

    def build_prioritized_context(
        self,
        world_setting: dict,
        characters: List[dict],
        outlines: List[dict],
        current_chapter_index: int,
        active_foreshadows: List[dict],
        previous_chapter_content: Optional[str] = None,
        retrieved_memories_with_scores: Optional[List[tuple[str, float]]] = None,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
    ) -> dict:
        """Build the complete context payload with priority-based budget allocation.

        Token budget distribution:
          P0 (40%): outline context + previous chapter
          P1 (35%): characters + world setting
          P2 (25%): vector memories + foreshadow reminders

        When budget is exceeded, lower-priority content is truncated first.
        """
        used = 0
        result = {}

        # ── P0: Core (40% budget) ──
        p0_budget = int(token_budget * 0.40)

        outline_ctx = self.build_outline_context(outlines, current_chapter_index)
        prev_ctx = self.build_previous_chapter_context(previous_chapter_content)

        outline_tokens = _estimate_tokens(outline_ctx)
        prev_tokens = _estimate_tokens(prev_ctx)

        # If P0 exceeds budget, trim previous chapter (keep at least last 1000 chars)
        if outline_tokens + prev_tokens > p0_budget:
            avail = max(1000, int((p0_budget - outline_tokens) / _CHAR_TO_TOKEN_RATIO))
            prev_ctx = _trim_text(previous_chapter_content or "", avail)

        result["outline_context"] = outline_ctx
        result["previous_chapter"] = prev_ctx
        used += _estimate_tokens(outline_ctx) + _estimate_tokens(prev_ctx)

        # ── P1: Important (35% budget) ──
        p1_budget = int(token_budget * 0.35)
        p1_start = used

        chars_ctx = self.build_characters_context(characters)
        world_ctx = self.build_world_summary(world_setting)

        chars_tokens = _estimate_tokens(chars_ctx)
        world_tokens = _estimate_tokens(world_ctx)

        # If P1 exceeds budget, trim character backgrounds
        if chars_tokens + world_tokens > p1_budget:
            avail = max(500, int((p1_budget - world_tokens) / _CHAR_TO_TOKEN_RATIO))
            chars_ctx = self.build_characters_context(
                characters,
                max_chars_per_character=max(50, int(avail / max(1, len(characters)))),
            )

        result["characters_context"] = chars_ctx
        result["world_summary"] = world_ctx
        used += _estimate_tokens(chars_ctx) + _estimate_tokens(world_ctx)

        # ── P2: Reference (remaining budget) ──
        p2_budget = token_budget - used
        p2_start = used

        # Memories take ~60% of P2 budget, foreshadows ~40%
        memory_budget_chars = int(p2_budget * 0.6 / _CHAR_TO_TOKEN_RATIO)
        foreshadow_budget_tokens = int(p2_budget * 0.4)

        mem_ctx = self.build_retrieved_memories_context(retrieved_memories_with_scores)
        fs_ctx = self.build_foreshadow_context(active_foreshadows, current_chapter_index)

        # Truncate memories if needed
        if _estimate_tokens(mem_ctx) > memory_budget_chars * _CHAR_TO_TOKEN_RATIO:
            mem_ctx = _trim_text(mem_ctx, memory_budget_chars)

        # Truncate foreshadows if needed (keep urgent ones)
        if _estimate_tokens(fs_ctx) > foreshadow_budget_tokens:
            fs_ctx = _trim_text(fs_ctx, int(foreshadow_budget_tokens / _CHAR_TO_TOKEN_RATIO))

        result["retrieved_memories"] = mem_ctx
        result["foreshadow_context"] = fs_ctx
        used += _estimate_tokens(mem_ctx) + _estimate_tokens(fs_ctx)

        # ── Metadata ──
        result["_budget"] = {
            "token_budget": token_budget,
            "used_tokens": used,
            "p0_used": _estimate_tokens(result["outline_context"]) + _estimate_tokens(result["previous_chapter"]),
            "p1_used": _estimate_tokens(result["characters_context"]) + _estimate_tokens(result["world_summary"]),
            "p2_used": _estimate_tokens(result["retrieved_memories"]) + _estimate_tokens(result["foreshadow_context"]),
            "similarity_threshold": self.similarity_threshold,
        }

        return result

    # ── Backward-compatible flat builder ────────────────────────────────

    @staticmethod
    def build_full_context(
        world_setting: dict,
        characters: List[dict],
        outlines: List[dict],
        current_chapter_index: int,
        active_foreshadows: List[dict],
        previous_chapter_content: Optional[str] = None,
        retrieved_memories: Optional[List[str]] = None,
    ) -> dict:
        """Flat context builder (backward-compatible). Prefer build_prioritized_context()."""
        builder = ContextBuilder()

        # Wrap memories with dummy scores for compatibility
        scored = None
        if retrieved_memories:
            scored = [(m, 0.8) for m in retrieved_memories]

        return builder.build_prioritized_context(
            world_setting=world_setting,
            characters=characters,
            outlines=outlines,
            current_chapter_index=current_chapter_index,
            active_foreshadows=active_foreshadows,
            previous_chapter_content=previous_chapter_content,
            retrieved_memories_with_scores=scored,
        )
