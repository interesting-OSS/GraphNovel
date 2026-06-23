"""Background Tasks API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(project_id: str = ""):
    tasks = await task_service.list(project_id if project_id else None)
    return {"items": tasks, "total": len(tasks)}


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await task_service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    success = await task_service.pause(task_id)
    return {"paused": success}


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    success = await task_service.resume(task_id)
    return {"resumed": success}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    success = await task_service.cancel(task_id)
    return {"cancelled": success}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    success = await task_service.delete(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete task in current status")
    return {"deleted": success}
