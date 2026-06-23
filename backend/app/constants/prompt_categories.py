"""Prompt template categories and popular genre tags."""

PROMPT_CATEGORIES = {
    "通用": {
        "description": "适用于所有类型的通用提示词模板",
        "templates": ["项目创建", "世界观初始化", "大纲生成"],
    },
    "玄幻/仙侠": {
        "description": "玄幻、仙侠类小说的专用模板",
        "templates": ["修炼体系", "宗门设定", "秘境生成"],
    },
    "武侠": {
        "description": "武侠类小说的专用模板",
        "templates": ["武功体系", "门派设定", "江湖势力"],
    },
    "言情": {
        "description": "言情类小说的专用模板",
        "templates": ["感情线设计", "人物关系", "感情冲突"],
    },
    "科幻": {
        "description": "科幻类小说的专用模板",
        "templates": ["科技树设计", "未来世界", "外星文明"],
    },
    "悬疑/惊悚": {
        "description": "悬疑、惊悚类小说的专用模板",
        "templates": ["案件设计", "线索铺设", "反转设计"],
    },
    "历史": {
        "description": "历史类小说的专用模板",
        "templates": ["时代背景", "历史事件改编", "朝堂势力"],
    },
    "都市": {
        "description": "都市类小说的专用模板",
        "templates": ["现代职业体系", "都市势力", "商战设计"],
    },
    "游戏/电竞": {
        "description": "游戏、电竞类小说的专用模板",
        "templates": ["游戏系统设计", "竞技体系", "公会设定"],
    },
    "其他": {
        "description": "其他类型的提示词模板",
        "templates": [],
    },
}

CATEGORY_LIST = list(PROMPT_CATEGORIES.keys())

POPULAR_TAGS = [
    "玄幻", "仙侠", "升级流", "系统流", "穿越",
    "重生", "言情", "甜宠", "虐恋", "宫斗",
    "武侠", "修真", "科幻", "末世", "游戏",
    "电竞", "悬疑", "推理", "惊悚", "灵异",
    "历史", "架空", "都市", "商战", "种田",
    "基建", "无限流", "综漫",
]
