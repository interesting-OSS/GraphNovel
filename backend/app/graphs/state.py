"""NovelState — the complete state schema for the novel creation graph.

NovelState 是 LangGraph 全局状态，贯穿整个小说创作流水线。
所有节点通过读写这个 state 来传递数据和控制流程。
"""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from app.config import settings


class NovelState(TypedDict, total=False):
    # =========================================================================
    # === 项目元数据 ===
    # =========================================================================
    project_id: str
    """项目唯一标识（UUID），用于数据库关联、日志追踪、指标记录"""
    title: str
    """小说标题"""
    description: Optional[str]
    """小说简介/梗概，AI 生成各个维度时会以此为出发点"""
    genre: str
    """小说类型，默认 "玄幻"。影响世界观风格、力量体系、文化设定等"""
    target_words: int
    """目标总字数，大纲规划时用来估算章节数"""
    narrative_perspective: str
    """叙事视角，如 "第三人称" / "第一人称"，影响章节写作的语气和风格"""
    project_status: str
    """项目状态：planning（规划中）/ writing（写作中）/ revising（修订中）/ completed（已完成）"""
    total_word_count: int
    """已写总字数，写作过程中累加"""
    outline_mode: str
    """大纲模式：one-to-one（一个大纲节点=一章）/ one-to-many（一个大纲节点=多章）"""
    cover_prompt: Optional[str]
    """封面生成提示词，用户在 UI 中自定义封面风格时填入"""
    cover_url: Optional[str]
    """生成后的封面图片 URL"""

    # =========================================================================
    # === 世界观设定 ===
    # =========================================================================
    world_setting: dict
    """
    世界观数据字典，由 WorldBuild 子图生成：
    {
        "time_period": "时代背景（300-500字）",
        "geography":   "地理版图（300-500字）",
        "power_system":"力量体系（300-500字）",
        "factions":    "势力格局（300-500字）",
        "culture":     "文化风俗（300-500字）",
        "consistency_check": {
            "has_conflicts": bool,      # 是否有内部矛盾
            "conflicts": [str],         # 矛盾描述列表
            "suggestions": [str]        # 改进建议列表
        },
        "_fix_attempts": int,           # 内部字段：自动修复轮次
        "_fix_history": [...]           # 内部字段：修复记录
    }
    """

    # =========================================================================
    # === 大纲 ===
    # =========================================================================
    outlines: List[dict]
    """
    大纲列表，由 outline_plan_node 生成。每个元素：
    {
        "volume": int,              # 卷号
        "chapter_index": int,       # 章节序号
        "title": str,               # 章节标题
        "summary": str,             # 内容摘要（50-150字）
        "key_points": str,          # 关键情节要点
        "target_words": int,        # 本章目标字数
        "mode": str,                # "one-to-one" / "one-to-many"
        "expansion_strategy": str   # 展开策略：balanced / detailed / concise
    }
    """

    # =========================================================================
    # === 角色 & 组织 ===
    # =========================================================================
    characters: List[dict]
    """
    角色列表，由 char_create 子图生成。每个元素：
    {
        "name": str,                # 角色名
        "role_type": str,           # 角色类型：主角/反派/配角/路人
        "goals": str,               # 角色目标
        "personality": str,         # 性格描述
        "background": str,          # 背景故事
        "appearance": str,          # 外貌描述
        "abilities": str,           # 能力/技能
        "relationships": [...]      # 与其他角色的关系
    }
    """
    relationships: List[dict]
    """角色关系列表，描述角色之间的互动关系（师徒/敌对/盟友/恋人等）"""
    organizations: List[dict]
    """组织/势力列表，如宗门、帮派、国家等"""
    careers: List[dict]
    """角色职业/修炼等级方案，由 career_manage_node 生成"""

    # =========================================================================
    # === 章节 ===
    # =========================================================================
    current_chapter_index: int
    """当前正在处理的章节序号，写作过程中递增"""
    chapters: List[dict]
    """
    已生成的章节列表。每个元素：
    {
        "chapter_index": int,       # 章节序号
        "title": str,               # 章节标题
        "content": str,             # 章节正文
        "word_count": int,          # 字数
        "status": str,              # draft / reviewed / polished / published
        "draft": str,               # 初稿
        "feedback": str,            # 用户反馈
        "revision_history": [...]   # 修订历史
    }
    """

    # =========================================================================
    # === 记忆 & 上下文 ===
    # =========================================================================
    plot_memory: List[dict]
    """
    情节记忆库（向量存储），用于跨章节连贯性。
    记录已发生的关键事件、时间线、因果链，防止前后矛盾。
    """
    chapter_analyses: List[dict]
    """
    章节分析记录，chapter_analyze 子图产出。
    每写完一章后自动分析：情节进展、角色弧光、伏笔状态等。
    """
    foreshadows: List[dict]
    """
    伏笔列表。追踪所有已埋下和已回收的伏笔：
    {
        "id": str,                  # 伏笔唯一ID
        "description": str,         # 伏笔描述
        "planted_in": int,          # 埋伏笔的章节号
        "resolved_in": int|None,    # 回收伏笔的章节号（None=未回收）
        "status": str               # pending / resolved / abandoned
    }
    """

    # =========================================================================
    # === 生成记录 ===
    # =========================================================================
    generation_history: List[dict]
    """
    AI 生成操作的审计日志。每条记录：
    {
        "phase": str,               # 哪个阶段（如 world_build / chapter_write）
        "timestamp": float,         # 时间戳
        "prompt_snapshot": str,     # 输入提示词截断
        "result_snapshot": str,     # 输出结果截断
        "success": bool             # 是否成功
    }
    """

    # =========================================================================
    # === 后台任务 ===
    # =========================================================================
    background_tasks: List[dict]
    """
    后台异步任务列表（Celery task ID 及状态），如批量生成、导出等长耗时操作
    """

    # =========================================================================
    # === 消息（LangChain 对话） ===
    # =========================================================================
    messages: Annotated[List[BaseMessage], add_messages]
    """
    LangChain 消息历史。Annotated[List, add_messages] 是 LangGraph 的约定写法，
    表示新消息会 append 而不是覆盖。用于支持对话式交互和多轮生成。
    """

    # =========================================================================
    # === 控制流 ===
    # =========================================================================
    current_phase: str
    """
    当前阶段标识，相当于状态机的心跳信号。
    每个节点执行完都会写入自己的 phase，如：
      "time_period_generated" → "geography_generated" → ... → "consistency_checked"
    前端通过轮询/SSE 读取此字段来展示进度条和当前步骤名称。
    """
    human_feedback: Optional[str]
    """
    用户反馈文本。在 human_review 中断节点中，用户通过 UI 提交反馈后写入此字段，
    下游节点根据反馈内容决定是修改、重写还是继续。
    """
    generation_config: dict
    """
    生成配置，指定使用哪个 AI 服务：
    {
        "provider": str,         # "openai" / "anthropic" / "deepseek" 等
        "model": str,            # 模型名，如 "gpt-4o" / "claude-sonnet-4-6"
        "api_key": str,          # API 密钥
        "base_url": str,         # 自定义 API 地址
        "temperature": float,    # 温度（0-2），控制随机性
        "max_tokens": int,       # 最大输出 token 数
        "stream": bool           # 是否流式输出
    }
    """
    error: Optional[str]
    """
    错误信息。任何节点发生异常时写入，前端可读取此字段展示错误提示。
    正常情况下为 None。
    """
    _fix_attempts: int
    """
    内部字段：当前子图自动修复的轮次计数。
    world_build / char_create 的一致性检查→修复循环中使用，单次最多 3 轮。
    """
    _fix_history: List[dict]
    """
    内部字段：自动修复的历史记录。
    [{"attempt": 1, "issues": [...], "fixed_characters": ["张三"]}, ...]
    """
    _ooc_check: dict
    """
    内部字段：角色OOC（Out-of-Character）一致性检查结果，由 char_create 子图的
    check_ooc 节点产出。格式同 consistency_check：
    {"has_issues": bool, "issues": [str], "suggestions": [str]}
    """

    # =========================================================================
    # === 灵感/创意 ===
    # =========================================================================
    inspirations: List[dict]
    """
    灵感/创意片段列表，用户或 AI 记录的零散想法，可在创作时参考。
    """

    # =========================================================================
    # === 写作风格 / 技能 ===
    # =========================================================================
    active_skill: Optional[str]
    """当前激活的写作技能/插件名称（如 "幽默改写"、"战斗场景增强"）"""
    writing_style_id: Optional[str]
    """写作风格模板 ID，引用预设的风格配置"""
    prompt_template_id: Optional[str]
    """提示词模板 ID，引用预设的提示词模板"""


def create_initial_state(
    project_id: str = "",
    title: str = "",
    genre: str = "玄幻",
    target_words: int = 100000,
    narrative_perspective: str = "第三人称",
    generation_config: Optional[dict] = None,
) -> NovelState:
    """创建小说创作会话的初始状态。

    Args:
        project_id: 项目唯一标识
        title: 小说标题
        genre: 小说类型
        target_words: 目标总字数
        narrative_perspective: 叙事视角
        generation_config: AI 生成配置（provider/model/temperature等）

    Returns:
        初始化完毕的 NovelState，所有列表字段为空，状态为 "planning"
    """
    return NovelState(
        project_id=project_id,
        title=title,
        description=None,
        genre=genre,
        target_words=target_words,
        narrative_perspective=narrative_perspective,
        project_status="planning",
        total_word_count=0,
        outline_mode="one-to-one",
        cover_prompt=None,
        cover_url=None,
        world_setting={},
        outlines=[],
        characters=[],
        relationships=[],
        organizations=[],
        careers=[],
        current_chapter_index=0,
        chapters=[],
        plot_memory=[],
        chapter_analyses=[],
        foreshadows=[],
        generation_history=[],
        background_tasks=[],
        messages=[],
        current_phase="init",
        human_feedback=None,
        generation_config=generation_config or {
            "provider": settings.default_llm_provider,
            "model": settings.default_llm_model,
            "temperature": 0.7,
            "max_tokens": 32000,
            "stream": True,
        },
        error=None,
        _fix_attempts=0,
        _fix_history=[],
        _ooc_check={},
        inspirations=[],
        active_skill=None,
        writing_style_id=None,
        prompt_template_id=None,
    )
