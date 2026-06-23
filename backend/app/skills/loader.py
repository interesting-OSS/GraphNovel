"""SkillLoader — parses SKILL.md files into executable Skill objects.

Each skill directory contains a SKILL.md with:
  - YAML frontmatter: name, display_name, category, description, triggers
  - Markdown body: the actual prompt/instructions injected into system prompts

Usage:
    loader = SkillLoader()
    skill = loader.load("story-long-write")
    system_prompt = skill.get_injected_prompt(base_prompt="你是AI小说助手。")
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A loaded skill with parsed metadata and executable prompt content.

    Attributes:
        name: Unique skill identifier (e.g. 'story-long-write')
        display_name: Human-readable name (e.g. '长篇故事创作')
        category: 'writing' | 'analysis' | 'development'
        description: One-line description of what the skill does
        triggers: Keywords that trigger this skill in user queries
        content: The raw markdown body — injected as system instructions
    """
    name: str
    display_name: str
    category: str
    description: str
    triggers: list[str] = field(default_factory=list)
    content: str = ""

    def get_injected_prompt(self, base_prompt: str = "") -> str:
        """Build a complete system prompt by combining the skill content with a base.

        The skill content is prepended as the primary instruction layer.
        The base_prompt serves as secondary context.
        """
        parts = []
        if self.content:
            parts.append(f"## 当前技能: {self.display_name}\n{self.content}")
        if base_prompt:
            parts.append(f"## 基础指令\n{base_prompt}")
        return "\n\n".join(parts) if parts else base_prompt

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "triggers": self.triggers,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
        }

    def __repr__(self) -> str:
        return f"Skill({self.name!r}, category={self.category!r})"


class SkillLoader:
    """Loads and caches skills from the filesystem.

    Singleton-safe; multiple instantiations share the same cache.
    """

    _cache: dict[str, Skill] = {}

    def __init__(self, skills_root: Optional[Path] = None):
        if skills_root is None:
            skills_root = Path(__file__).parent
        self.skills_root = Path(skills_root)

    # ── public API ──

    def load(self, skill_name: str) -> Optional[Skill]:
        """Load a skill by name. Returns None if not found."""
        if skill_name in self._cache:
            return self._cache[skill_name]

        skill_dir = self.skills_root / skill_name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            logger.warning("Skill '%s' not found at %s", skill_name, skill_file)
            return None

        try:
            raw = skill_file.read_text(encoding="utf-8")
            skill = self._parse(raw)
            self._cache[skill_name] = skill
            return skill
        except Exception as exc:
            logger.error("Failed to parse skill '%s': %s", skill_name, exc)
            return None

    def load_all(self) -> list[Skill]:
        """Load all skills from the filesystem."""
        skills = []
        if not self.skills_root.exists():
            return skills

        for entry in sorted(self.skills_root.iterdir()):
            if not entry.is_dir():
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.exists():
                continue
            skill = self.load(entry.name)
            if skill:
                skills.append(skill)
        return skills

    def match(self, query: str) -> Optional[Skill]:
        """Find the best-matching skill for a user query.

        Scoring: exact trigger match = 100, substring match in name/triggers = 10,
        keyword in description = 5, keyword in content = 3.
        """
        if not query:
            return None

        query_lower = query.lower()
        best_score = 0
        best_skill: Optional[Skill] = None

        for skill in self.load_all():
            score = 0
            # trigger exact match
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 30
                elif any(word in query_lower for word in trigger.lower().split()):
                    score += 10

            # name match
            if skill.name.lower() in query_lower:
                score += 20
            if skill.display_name in query:
                score += 15

            # description keyword match
            desc_words = set(skill.description.lower().split())
            query_words = set(query_lower.split())
            common = desc_words & query_words
            score += len(common) * 3

            if score > best_score:
                best_score = score
                best_skill = skill

        # Require at least a minimal match score
        return best_skill if best_score >= 5 else None

    def clear_cache(self):
        """Clear the skill cache to force re-reading from disk."""
        self._cache.clear()

    def list_skills(self) -> list[dict]:
        """List all available skills as lightweight dicts."""
        return [s.to_dict() for s in self.load_all()]

    # ── internals ──

    _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    @staticmethod
    def _parse(raw: str) -> Skill:
        """Parse a SKILL.md file into a Skill object."""
        frontmatter: dict = {}
        body = raw

        m = SkillLoader._FRONTMATTER_RE.match(raw)
        if m:
            body = raw[m.end():].strip()
            frontmatter = SkillLoader._parse_yaml_lite(m.group(1))

        triggers = frontmatter.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [t.strip() for t in triggers.split(",") if t.strip()]

        return Skill(
            name=frontmatter.get("name", ""),
            display_name=frontmatter.get("display_name", frontmatter.get("name", "")),
            category=frontmatter.get("category", "通用"),
            description=frontmatter.get("description", ""),
            triggers=triggers if isinstance(triggers, list) else [],
            content=body,
        )

    @staticmethod
    def _parse_yaml_lite(text: str) -> dict:
        """Parse a simplified YAML frontmatter (key: value pairs, list items).

        Handles the subset used in SKILL.md frontmatter without a full YAML parser.
        """
        result: dict = {}
        current_key: Optional[str] = None
        current_list: list = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # list continuation: "  - value"
            if stripped.startswith("- ") and current_key:
                current_list.append(stripped[2:].strip())
                continue

            # key: value
            if ":" in stripped and not stripped.startswith("-"):
                # flush previous list
                if current_key and current_list:
                    result[current_key] = current_list
                    current_list = []

                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    result[key] = value
                    current_key = None
                else:
                    current_key = key
            elif stripped and current_key:
                # value on next line
                result[current_key] = stripped.strip('"').strip("'")
                current_key = None

        # flush final list
        if current_key and current_list:
            result[current_key] = current_list

        return result


# Module-level convenience instance
_default_loader: Optional[SkillLoader] = None


def get_skill_loader() -> SkillLoader:
    """Get the default SkillLoader singleton."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SkillLoader()
    return _default_loader
