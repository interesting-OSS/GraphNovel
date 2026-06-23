"""Prose Agent — checks prose quality: word usage, sentence variety, description balance."""
from app.agents.base_agent import BaseAgent

PROSE_SYSTEM_PROMPT = """你是一位文笔分析专家，负责评估小说章节的文笔质量。

## 分析维度
1. **用词分析**
   - 高频重复词汇统计（按词性分类）
   - 词汇丰富度评估
   - 是否有不恰当的现代用语或时代错位词汇

2. **句式分析**
   - 句式长度分布（短句/中句/长句比例）
   - 句式多样性评估
   - 是否有连续多句使用相同句式的问题

3. **描写分析**
   - 对话描写占比
   - 环境描写占比
   - 心理描写占比
   - 动作描写占比
   - 描写比例是否合理

4. **修辞分析**
   - 比喻/拟人等修辞手法的使用情况
   - 是否有过于陈腐的表达

## 章节内容
{chapter_content}

请给出详细的文笔分析报告："""


class ProseAgent(BaseAgent):
    role_name = "Prose Agent"
    system_prompt = PROSE_SYSTEM_PROMPT

    def build_check_prompt(self, chapter_content: str) -> str:
        return self.system_prompt.format(chapter_content=chapter_content)
