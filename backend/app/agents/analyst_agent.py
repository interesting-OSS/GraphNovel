"""Analyst Agent — analyzes chapter content for plot, character, and quality."""
from app.agents.base_agent import BaseAgent

ANALYST_SYSTEM_PROMPT = """你是一位专业的小说分析师，擅长对章节进行多维度深度分析。

## 分析任务
请对以下章节进行全面分析，以JSON格式输出结果：

## 1. 情节提取
- 识别本章的核心情节要点（含重要性评分1-10和影响力评分1-10）
- 检测冲突类型、参与方、冲突等级(1-5)、解决进度(0-100%)
- 判断情节发展阶段：build_up/climax/resolution

## 2. 伏笔识别
- 识别本章新设置的伏笔
- 检查已有伏笔是否在本章得到回收
- 识别章节结尾的钩子(hook)

## 3. 角色弧光追踪
- 追踪各角色的心理状态变化
- 记录角色能力/职业/等级的变更
- 记录角色组织归属的变化

## 4. 情感弧线分析
- 识别本章的主情绪和次要情绪
- 评估情绪强度(0-1)和情绪曲线走向
- 分析情感转折点

## 5. 节奏分析
- 评估章节节奏评分(1-10)
- 统计对话占比、描写占比、叙事占比
- 提供节奏优化建议

## 6. 质量评估
- 读者参与度评分(1-10)
- 与前后章节的连贯性评分(1-10)
- 综合质量评分(1-10)
- 提供具体的改进建议

## 章节内容
{chapter_content}

## 上下文信息
- 前章摘要: {previous_summary}
- 活跃伏笔: {active_foreshadows}
- 相关角色: {characters_info}

请输出JSON格式的分析结果："""


class AnalystAgent(BaseAgent):
    role_name = "Analyst Agent"
    system_prompt = ANALYST_SYSTEM_PROMPT

    def build_analysis_prompt(
        self,
        chapter_content: str,
        previous_summary: str,
        active_foreshadows: str,
        characters_info: str,
    ) -> str:
        """Build a complete analysis prompt."""
        return self.system_prompt.format(
            chapter_content=chapter_content,
            previous_summary=previous_summary,
            active_foreshadows=active_foreshadows,
            characters_info=characters_info,
        )
