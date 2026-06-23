"""Cover generation service — AI cover image creation using multimodal models.

Uses Qwen (DashScope) for image generation when available.
Falls back to prompt-only mode for text-only providers.
"""
from typing import Optional
from app.services.ai_service import AIService, create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

COVER_PROMPT_TEMPLATE = """你是一位专业的小说封面设计师。请根据以下小说信息，生成一个高质量的封面设计提示词，用于AI图像生成模型。

## 小说信息
- 书名: {title}
- 类型: {genre}
- 简介: {description}
- 世界观: {world_setting}

## 输出要求
- 风格: {style}
- 生成中文图像提示词（100-200字），包含构图、色彩、主体、氛围
- 专注于视觉元素的精准描述
- 避免使用抽象概念，强调具象的视觉表达

请直接输出封面提示词（纯文本，不要JSON包裹）："""


class CoverService:
    """Service for generating novel cover images using AI (Qwen multimodal preferred)."""

    STYLES = {
        "anime":    "日系动漫风格，赛璐璐上色，柔和光线，角色居中构图",
        "realistic": "写实厚涂风格，电影级光影，细节丰富，史诗感构图",
        "chinese":  "中国风水墨画风格，留白构图，写意笔触，古典配色（墨色、朱砂红、藤黄）",
        "dark":     "暗黑奇幻风格，低饱和度，戏剧化侧光，压抑氛围，哥特元素",
        "light":    "明亮轻快风格，高饱和暖色调，柔光，治愈系氛围",
        "minimal":  "极简风格，大面积留白，几何构图，低饱和度配色，现代感",
    }

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service

    @classmethod
    def get_available_styles(cls) -> dict:
        return cls.STYLES.copy()

    async def generate_prompt(
        self,
        ai_service: AIService,
        title: str,
        description: str,
        genre: str,
        world_summary: str,
        style: str = "chinese",
    ) -> str:
        """Generate a cover image prompt from novel metadata via AI."""
        style_desc = self.STYLES.get(style, self.STYLES["chinese"])
        user_prompt = COVER_PROMPT_TEMPLATE.format(
            title=title,
            genre=genre,
            description=description or "暂无简介",
            world_setting=world_summary or "暂无世界观设定",
            style=style_desc,
        )
        system_prompt = "你是一位专业的AI图像提示词工程师，擅长为小说封面创作高质量的图像生成提示词。"
        prompt = await ai_service.generate(system_prompt, user_prompt)
        return prompt.strip()

    async def generate_image(
        self,
        prompt: str,
        provider: Optional[str] = None,
        size: str = "1024x1024",
    ) -> dict:
        """Generate a cover image using the multimodal provider.

        Uses Qwen (DashScope) for actual image generation.
        Returns dict with 'url' and 'revised_prompt'.
        """
        p = provider or settings.image_provider
        if p == "qwen":
            try:
                ai = create_ai_service(
                    provider="qwen",
                    api_key=settings.qwen_api_key,
                    base_url=settings.qwen_base_url,
                    model="qwen-vl-max",
                    temperature=0.7,
                    max_tokens=4000,
                )
                result = await ai.generate_image(prompt, size=size)
                logger.info("Cover image generated via Qwen: %s", result.get("url", "")[:80])
                return result
            except Exception as exc:
                logger.error("Qwen image generation failed, returning prompt only: %s", exc)
                return {"url": "", "revised_prompt": prompt, "error": str(exc)}

        # For non-multimodal providers: return prompt only
        logger.info("Image generation not available for provider '%s', returning prompt only", p)
        return {"url": "", "revised_prompt": prompt,
                "message": f"Provider '{p}' does not support image generation. Cover prompt is ready for external tools."}

    async def generate_cover(
        self,
        title: str,
        description: str,
        genre: str,
        world_summary: str,
        style: str = "chinese",
        provider: Optional[str] = None,
        size: str = "1024x1024",
    ) -> dict:
        """Full workflow: generate prompt → generate image (if multimodal).

        Returns dict with 'prompt', 'url', and 'provider_used'.
        """
        if not self.ai_service:
            self.ai_service = create_ai_service(
                provider="openai" if settings.openai_api_key else "qwen",
                temperature=0.7,
                max_tokens=4000,
            )

        # Step 1: Generate prompt
        prompt = await self.generate_prompt(
            self.ai_service, title, description, genre, world_summary, style,
        )

        # Step 2: Try image generation if multimodal provider available
        image_result = await self.generate_image(prompt, provider=provider, size=size)

        return {
            "prompt": prompt,
            "url": image_result.get("url", ""),
            "revised_prompt": image_result.get("revised_prompt", prompt),
            "provider_used": provider or settings.image_provider,
            "message": "Cover generated" if image_result.get("url")
                       else "Cover prompt ready (image generation unavailable or failed)",
            "error": image_result.get("error"),
        }
