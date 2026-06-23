"""Character Relationship API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.relationship import CharacterRelationship, Organization, OrganizationMember
from app.logger import get_logger

router = APIRouter(prefix="/relationships", tags=["relationships"])
logger = get_logger(__name__)


@router.get("/project/{project_id}")
async def list_relationships(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all character relationships for a project."""
    result = await db.execute(
        select(CharacterRelationship).where(CharacterRelationship.project_id == project_id)
    )
    rels = result.scalars().all()
    return {
        "items": [{
            "id": r.id, "char_a_id": r.char_a_id, "char_b_id": r.char_b_id,
            "relation_type": r.relation_type, "description": r.description,
            "intimacy": r.intimacy, "status": r.status, "source": r.source,
        } for r in rels],
        "total": len(rels),
    }


@router.post("")
async def create_relationship(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new character relationship."""
    rel = CharacterRelationship(
        project_id=data.get("project_id", ""),
        char_a_id=data.get("char_a_id", ""),
        char_b_id=data.get("char_b_id", ""),
        relation_type=data.get("relation_type", "其他"),
        description=data.get("description", ""),
        intimacy=data.get("intimacy", 50),
        status=data.get("status", "正常"),
        source=data.get("source", "手动创建"),
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return {"id": rel.id}


@router.put("/{rel_id}")
async def update_relationship(rel_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a relationship."""
    result = await db.execute(select(CharacterRelationship).where(CharacterRelationship.id == rel_id))
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    for key in ("char_a_id", "char_b_id", "relation_type", "description", "intimacy", "status"):
        if key in data:
            setattr(rel, key, data[key])
    await db.commit()
    return {"id": rel_id, "updated": True}


@router.delete("/{rel_id}")
async def delete_relationship(rel_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a relationship."""
    result = await db.execute(select(CharacterRelationship).where(CharacterRelationship.id == rel_id))
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    await db.delete(rel)
    await db.commit()
    return {"deleted": True}
