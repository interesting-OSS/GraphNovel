"""Skills Management API — skill list, load, and AI chat with skill context."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.sse_response import SSEResponse
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger
from app.skills.loader import SkillLoader, get_skill_loader
from pathlib import Path
import asyncio

router = APIRouter(prefix="/skills", tags=["skills"])
logger = get_logger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def _get_loader() -> SkillLoader:
    return get_skill_loader()


def _load_skill_content(skill_name: str) -> str:
    """Load skill prompt content via SkillLoader."""
    loader = _get_loader()
    skill = loader.load(skill_name)
    return skill.content if skill else ""


@router.get("/list")
async def list_skills():
    """List all available skills from the skill loader."""
    loader = _get_loader()
    return {"items": loader.list_skills()}


@router.post("/match")
async def match_skill(data: dict):
    """Match user input to the most relevant skill via SkillLoader."""
    query = data.get("query", "")
    if not query:
        return {"matched": None}
    loader = _get_loader()
    matched = loader.match(query)
    return {"matched": matched.name if matched else None, "skill": matched.to_dict() if matched else None}


@router.post("/chat")
async def skill_chat_stream(data: dict):
    """AI chat with skill context via SSE streaming."""
    async def event_generator():
        try:
            ai = create_ai_service(
                provider=data.get("provider", "openai"),
                api_key=data.get("api_key"),
                model=data.get("model", settings.default_ai_model),
                temperature=0.7, max_tokens=8000,
            )
            skill_name = data.get("skill_name", "")
            user_message = data.get("message", "")

            # Load skill context
            skill_content = _load_skill_content(skill_name) if skill_name else ""
            system_prompt = skill_content if skill_content else "你是一位小说创作助手。"

            yield SSEResponse.progress("技能对话中...", 30.0, "chatting")

            full_response = ""
            async for chunk in ai.generate_stream(system_prompt, user_message):
                full_response += chunk
                yield SSEResponse.chunk(chunk)

            yield SSEResponse.result({"response": full_response})
            yield SSEResponse.done("对话完成")
        except Exception as e:
            logger.error("Skill chat failed: %s", e)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{skill_name}")
async def get_skill(skill_name: str):
    """Get a skill's content and metadata from the loader."""
    loader = _get_loader()
    skill = loader.load(skill_name)
    if not skill:
        return {"name": skill_name, "content": "", "loaded": False,
                "display_name": skill_name, "category": "unknown"}

    return {
        "name": skill.name,
        "display_name": skill.display_name,
        "category": skill.category,
        "description": skill.description,
        "triggers": skill.triggers,
        "content": skill.content,
        "loaded": True,
    }


@router.post("")
async def create_skill(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a custom skill (stored as file)."""
    name = data.get("name", "custom-skill")
    content = data.get("content", "")
    if not content:
        return {"id": "", "error": "No content provided"}

    skill_path = SKILLS_DIR / name
    skill_path.mkdir(parents=True, exist_ok=True)
    (skill_path / "SKILL.md").write_text(content, encoding="utf-8")

    loader = _get_loader()
    loader.clear_cache()
    return {"name": name, "message": "Skill created"}


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str, db: AsyncSession = Depends(get_db)):
    """Delete a custom skill (builtins are protected)."""
    loader = _get_loader()
    skill = loader.load(skill_name)
    if skill and any(skill.name in ["story-long-write", "story-short-write",
                                     "story-long-analyze", "story-short-analyze",
                                     "story-long-scan", "story-deslop"]):
        return {"deleted": False, "error": "Cannot delete builtin skill"}

    skill_path = SKILLS_DIR / skill_name
    if skill_path.exists():
        import shutil
        shutil.rmtree(skill_path)
        loader.clear_cache()
    return {"deleted": True}


@router.post("/refresh-cache")
async def refresh_skills_cache():
    """Clear and refresh the skill content cache."""
    loader = _get_loader()
    loader.clear_cache()
    loader.load_all()  # Pre-load all skills
    skills = loader.list_skills()
    return {"status": "refreshed", "cached": len(skills)}
