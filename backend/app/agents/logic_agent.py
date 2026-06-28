"""Logic Agent — checks plot logic and timeline consistency."""
from app.agents.base_agent import BaseAgent

LOGIC_SYSTEM_PROMPT = """你是一位逻辑分析专家，负责检查小说章节的情节逻辑一致性。

## 检查维度
1. **时间线一致性**：事件发生的时间顺序是否合理？
2. **因果逻辑**：每个事件的发生是否有充分的前因？是否存在逻辑跳跃？
3. **设定一致性**：是否与既定的世界观和力量体系设定相符？
4. **角色行为逻辑**：角色的决策和行动是否符合其性格设定和当前状态？
5. **前后矛盾**：是否存在与之前章节内容相矛盾的地方？

## 已知设定
- 世界观: {world_setting}
- 角色列表: {characters_info}
- 前情摘要: {previous_events}

## 本章内容
{chapter_content}

请逐一检查并指出所有逻辑问题，若无问题请说明原因："""


class LogicAgent(BaseAgent):
    role_name = "Logic Agent"
    system_prompt = LOGIC_SYSTEM_PROMPT

    def build_check_prompt(
        self,
        chapter_content: str,
        world_setting: str,
        characters_info: str,
        previous_events: str,
    ) -> str:
        prompt = self.system_prompt
        prompt = prompt.replace("{chapter_content}", chapter_content)
        prompt = prompt.replace("{world_setting}", world_setting)
        prompt = prompt.replace("{characters_info}", characters_info)
        prompt = prompt.replace("{previous_events}", previous_events)
        return prompt
