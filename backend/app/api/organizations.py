"""Organization API routes — CRUD + members + AI generation via graph."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.relationship import Organization, OrganizationMember
from app.graphs.state import NovelState
from app.config import settings
from app.graphs.utils import get_gen_config
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
            "alignment": o.alignment,
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
        "alignment": org.alignment,
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
        alignment=data.get("alignment", "中立"),
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
    for key in ("name", "org_type", "leader_id", "goal", "description", "alignment"):
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
    # Delete members in bulk (single query, no N+1)
    await db.execute(
        delete(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
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
    """Generate organizations via the graph's organization_node."""
    from app.graphs.main_graph import organization_node

    state = NovelState(
        project_id=data.get("project_id", ""),
        genre=data.get("genre", "玄幻"),
        world_setting=data.get("world_setting", {}),
        generation_config=get_gen_config(data, max_tokens=8000),
    )

    try:
        result = await organization_node(state)
        return {"status": "completed", "organizations": result.get("organizations", [])}
    except Exception as e:
        logger.error("Organization generation failed: %s", e)
        return {"status": "failed", "error": str(e)}
