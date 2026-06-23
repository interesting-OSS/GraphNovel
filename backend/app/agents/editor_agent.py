"""Editor Agent — polishes and edits chapter content."""
from app.agents.base_agent import BaseAgent

EDITOR_SYSTEM_PROMPT = """你是一位资深的小说编辑，擅长提升文本质量和可读性。

## 编辑任务
请对以下小说章节进行润色和编辑，重点关注：

1. **语言流畅度**：消除拗口表达，优化句式结构
2. **用词精准度**：替换重复用词，增强词汇丰富度
3. **节奏把控**：调整段落长度，控制张弛节奏
4. **对话优化**：让对话更符合角色性格，去除生硬感
5. **描写增强**：适度丰富场景和人物描写，增强画面感

## 润色策略
- 保持原文风格和叙事语气不变
- 不要改变情节走向和角色行为
- 保持原有字数，不做大幅增删
- 只做文笔层面的优化

## 原文
{original_text}

请输出润色后的完整章节："""


class EditorAgent(BaseAgent):
    role_name = "Editor Agent"
    system_prompt = EDITOR_SYSTEM_PROMPT

    def build_polish_prompt(self, original_text: str, style_notes: str = "") -> str:
        """Build a polish/edit prompt."""
        prompt = self.system_prompt.format(original_text=original_text)
        if style_notes:
            prompt += f"\n\n## 额外风格要求\n{style_notes}"
        return prompt

    def build_rewrite_prompt(
        self,
        original_text: str,
        feedback: str,
        rewrite_mode: str = "full",
    ) -> str:
        """Build a rewrite prompt with user feedback."""
        mode_instructions = {
            "full": "请完全重写本章，保持相同的情节框架但优化所有表达。",
            "partial": "请只重写用户选中的段落，保持未选中部分不变。",
            "similar": "请保持原文风格重写选中内容。",
            "expand": "请在保持风格的基础上扩展细节和描写。",
            "condense": "请精简内容，去除冗余但保留核心信息。",
            "custom": "请根据用户的自定义指令进行重写。",
        }
        instruction = mode_instructions.get(rewrite_mode, mode_instructions["full"])

        return f"""你是一位资深的小说编辑。

## 重写任务
{instruction}

## 用户反馈
{feedback}

## 原文
{original_text}

请输出重写后的内容："""
