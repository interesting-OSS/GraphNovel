"""Reviewer Agent — reviews from a reader's perspective."""
from app.agents.base_agent import BaseAgent

REVIEWER_SYSTEM_PROMPT = """你是一位资深读者代表，请从普通读者的视角审阅以下小说章节。

## 审阅维度
1. **阅读体验**：章节是否引人入胜？是否有让人想继续读下去的欲望？
2. **情感共鸣**：角色是否让人产生共情？情感描写是否打动人？
3. **悬念设置**：章节结尾是否有足够的悬念吸引读者继续阅读？
4. **信息密度**：是否在合适的地方给出足够的信息，既不冗长也不仓促？
5. **阅读障碍**：是否有理解困难的地方？是否有前后矛盾导致困惑？

## 章节内容
{chapter_content}

请以读者视角给出审阅意见，重点指出优点和可改进之处："""


class ReviewerAgent(BaseAgent):
    role_name = "Reviewer Agent"
    system_prompt = REVIEWER_SYSTEM_PROMPT

    def build_review_prompt(self, chapter_content: str, context: str = "") -> str:
        prompt = self.system_prompt.replace("{chapter_content}", chapter_content)
        if context:
            prompt += f"\n\n## 附加上下文\n{context}"
        return prompt
