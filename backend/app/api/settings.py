"""Global Settings and API Preset Management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.settings_model import SettingsModel, APIPreset
from app.services.ai_service import AIService
from app.config import settings as app_settings
from app.logger import get_logger

router = APIRouter(prefix="/settings", tags=["settings"])
logger = get_logger(__name__)


async def _get_or_create_settings(db: AsyncSession) -> SettingsModel:
    result = await db.execute(select(SettingsModel).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SettingsModel()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get global settings."""
    settings = await _get_or_create_settings(db)
    return {
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "theme": settings.theme,
        "active_preset_id": settings.active_preset_id,
        "analysis_preset_id": settings.analysis_preset_id,
        "openai_api_key_set": bool(settings.ai_api_key),
        "anthropic_api_key_set": bool(app_settings.anthropic_api_key),
        "google_api_key_set": bool(app_settings.google_api_key),
    }


@router.put("")
async def save_settings(data: dict, db: AsyncSession = Depends(get_db)):
    """Update global settings."""
    settings = await _get_or_create_settings(db)
    updatable = ("ai_provider", "ai_model", "temperature", "max_tokens", "theme", "active_preset_id", "analysis_preset_id")
    for key in updatable:
        if key in data:
            setattr(settings, key, data[key])
    if "api_key" in data and data["api_key"]:
        settings.ai_api_key = data["api_key"]
    if "base_url" in data:
        settings.ai_base_url = data["base_url"]
    await db.commit()
    return {"saved": True}


@router.get("/available-models")
async def get_available_models(provider: str = "openai"):
    """Get available models for a provider."""
    from app.services.ai_service import PROVIDER_MODELS, get_available_providers
    models = PROVIDER_MODELS.get(provider, [])
    return {
        "models": models,
        "available_providers": get_available_providers(),
    }


@router.post("/test-connection")
async def test_api_connection(data: dict):
    """Test AI API connectivity with preview response."""
    try:
        service = AIService(
            provider=data.get("provider", "openai"),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            model=data.get("model", "gpt-4o"),
        )
        # Test basic connectivity
        response = await service.generate(
            "你是一个助手。用一句话介绍自己。",
            "请用一句话介绍你自己。",
        )
        # Test function calling support
        supports_fc = True
        try:
            await service.generate_json(
                "只输出JSON。", "返回 {\"test\": true}"
            )
        except Exception:
            supports_fc = False

        return {"success": True, "preview": response, "supports_function_calling": supports_fc}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── API Presets ──


@router.get("/presets")
async def list_presets(db: AsyncSession = Depends(get_db)):
    """List all API configuration presets."""
    settings = await _get_or_create_settings(db)
    result = await db.execute(select(APIPreset))
    presets = result.scalars().all()
    return {
        "items": [{
            "id": p.id, "name": p.name, "provider": p.provider, "model": p.model,
            "api_key_set": bool(p.api_key), "base_url": p.base_url,
            "temperature": p.temperature, "max_tokens": p.max_tokens,
            "is_active": p.id == settings.active_preset_id,
            "is_analysis": p.id == settings.analysis_preset_id,
        } for p in presets],
    }


@router.post("/presets")
async def create_preset(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new API configuration preset."""
    preset = APIPreset(
        name=data.get("name", "新预设"),
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o"),
        api_key=data.get("api_key"),
        base_url=data.get("base_url"),
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 32000),
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return {"id": preset.id, "message": "Preset created"}


@router.post("/presets/{preset_id}/activate")
async def activate_preset(preset_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Activate an API preset as the current default."""
    settings = await _get_or_create_settings(db)
    is_analysis = data.get("as_analysis", False)
    if is_analysis:
        settings.analysis_preset_id = preset_id
    else:
        settings.active_preset_id = preset_id

    # Copy preset config to settings
    result = await db.execute(select(APIPreset).where(APIPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if preset:
        settings.ai_provider = preset.provider
        settings.ai_model = preset.model
        settings.temperature = preset.temperature
        settings.max_tokens = preset.max_tokens
        if preset.api_key:
            settings.ai_api_key = preset.api_key
        if preset.base_url:
            settings.ai_base_url = preset.base_url

    await db.commit()
    return {"activated": preset_id}


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an API preset."""
    settings = await _get_or_create_settings(db)
    if settings.active_preset_id == preset_id:
        settings.active_preset_id = None
    if settings.analysis_preset_id == preset_id:
        settings.analysis_preset_id = None

    result = await db.execute(select(APIPreset).where(APIPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if preset:
        await db.delete(preset)
        await db.commit()
    return {"deleted": True}
