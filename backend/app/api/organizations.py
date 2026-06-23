"""Organization API routes — CRUD + members + AI generation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.relationship import Organization, OrganizationMember
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger
import json

router = APIRouter(prefix="/organizations", tags=["organizations"])
logger = get_logger(__name__)


@router.get("/project/{project_id}")
async def list_organizations(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.project_id == project_id))
    orgs = result.scalars().all()
    return {
        "items": [{
            "id": o.id, "name": o.name, "org_type": o.org_type,
            "leader_id": o.leader_id, "goal": o.goal, "description": o.description,
            "hierarchy": json.loads(o.hierarchy) if o.hierarchy else None,
        } for o in orgs],
        "total": len(orgs),
    }


@router.get("/{org_id}")
async def get_organization(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    members_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
    members = members_result.scalars().all()

    return {
        "id": org.id, "project_id": org.project_id, "name": org.name,
        "org_type": org.org_type, "leader_id": org.leader_id,
        "goal": org.goal, "description": org.description,
        "hierarchy": json.loads(org.hierarchy) if org.hierarchy else None,
        "members": [{"id": m.id, "character_id": m.character_id, "role": m.role} for m in members],
    }


@router.post("")
async def create_organization(data: dict, db: AsyncSession = Depends(get_db)):
    org = Organization(
        project_id=data.get("project_id", ""),
        name=data.get("name", "新组织"),
        org_type=data.get("org_type", "门派"),
        leader_id=data.get("leader_id"),
        goal=data.get("goal", ""),
        description=data.get("description", ""),
        hierarchy=json.dumps(data.get("hierarchy"), ensure_ascii=False) if data.get("hierarchy") else None,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return {"id": org.id}


@router.put("/{org_id}")
async def update_organization(org_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    for key in ("name", "org_type", "leader_id", "goal", "description"):
        if key in data:
            setattr(org, key, data[key])
    if "hierarchy" in data and isinstance(data["hierarchy"], (list, dict)):
        org.hierarchy = json.dumps(data["hierarchy"], ensure_ascii=False)
    await db.commit()
    return {"id": org_id, "updated": True}


@router.delete("/{org_id}")
async def delete_organization(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    # Delete members first
    members_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
    for m in members_result.scalars().all():
        await db.delete(m)
    await db.delete(org)
    await db.commit()
    return {"deleted": True}


@router.post("/{org_id}/members")
async def add_member(org_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organization not found")
    member = OrganizationMember(
        organization_id=org_id,
        character_id=data.get("character_id", ""),
        role=data.get("role", ""),
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return {"id": member.id, "added": True}


@router.delete("/{org_id}/members/{character_id}")
async def remove_member(org_id: str, character_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.character_id == character_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()
    return {"removed": True}


@router.post("/generate")
async def generate_organization(data: dict):
    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.7, max_tokens=8000,
    )
    prompt = f"""小说类型：{data.get('genre', '玄幻')}
世界观：{data.get('world_context', '未设定')}

请设计一个组织/势力。以JSON格式输出：
{{"name": "组织名", "org_type": "门派/势力/组织/家族", "goal": "目标(30-80字)", "description": "描述(50-150字)", "hierarchy": ["层级1", "层级2"], "alignment": "正义/中立/邪恶"}}
只输出JSON。"""
    try:
        result = await ai.generate_json("你是一位世界观设计师。只输出JSON。", prompt)
        return {"status": "completed", "organization": result}
    except Exception as e:
        logger.error("Organization generation failed: %s", e)
        return {"status": "failed", "error": str(e)}
