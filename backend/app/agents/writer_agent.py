"""Writer Agent — generates chapter content with context awareness."""
from app.agents.base_agent import BaseAgent

WRITER_SYSTEM_PROMPT = """你是一位专业的小说作家，擅长{genre}类小说的创作。

## 写作要求
1. 严格遵循大纲要点进行创作
2. 保持角色性格和行为的一致性
3. 合理运用伏笔和钩子
4. 控制章节字数在目标范围内
5. 注意对话、描写、叙事的比例平衡
6. 保持与前文的连贯性

## 当前上下文
- 世界观摘要: {world_summary}
- 当前卷大纲: {volume_outline}
- 相关角色: {characters_context}
- 活跃伏笔: {active_foreshadows}
- 上一章内容摘要: {previous_chapter_summary}

## 写作风格
{writing_style}

## 续写模式
{continuation_mode}

请根据以上信息，创作本章节的正文内容。"""


class WriterAgent(BaseAgent):
    role_name = "Writer Agent"
    system_prompt = WRITER_SYSTEM_PROMPT

    def build_writing_prompt(
        self,
        genre: str,
        world_summary: str,
        volume_outline: str,
        characters_context: str,
        active_foreshadows: str,
        previous_chapter_summary: str,
        writing_style: str,
        continuation_mode: str,
        chapter_outline: str,
    ) -> str:
        """Build a complete writing prompt with all context assembled. Uses replace()
        to avoid str.format() KeyError when content contains curly braces."""
        prompt = self.system_prompt
        prompt = prompt.replace("{genre}", genre)
        prompt = prompt.replace("{world_summary}", world_summary)
        prompt = prompt.replace("{volume_outline}", volume_outline)
        prompt = prompt.replace("{characters_context}", characters_context)
        prompt = prompt.replace("{active_foreshadows}", active_foreshadows)
        prompt = prompt.replace("{previous_chapter_summary}", previous_chapter_summary)
        prompt = prompt.replace("{writing_style}", writing_style)
        prompt = prompt.replace("{continuation_mode}", continuation_mode)
        return prompt + f"\n\n## 本章大纲要点\n{chapter_outline}\n\n请开始创作本章正文："
