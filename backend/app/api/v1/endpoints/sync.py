from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.models.models import DataSource
from app.services.sync.sync_service import SyncService
from app.services.queue.task_queue import get_task_queue

router = APIRouter()


class SyncSource(BaseModel):
    name: str
    type: str
    enabled: bool = True
    config: Dict[str, Any] = {}


class SyncStatus(BaseModel):
    source: str
    status: str
    last_sync: Optional[str] = None
    items_synced: int = 0


def get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    return SyncService(db)


@router.get("/sources")
async def get_sync_sources() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "sources": [
            {"name": "微信聊天记录", "type": "wechat", "enabled": True, "mode": "file_import"},
            {"name": "QQ聊天记录", "type": "qq", "enabled": True, "mode": "file_import"},
            {"name": "飞书文档", "type": "feishu", "enabled": True, "mode": "file_import"},
            {"name": "GitHub活动", "type": "github", "enabled": True, "mode": "file_or_webhook"},
            {"name": "邮件", "type": "email", "enabled": True, "mode": "file_or_imap_adapter"},
        ]
    }


@router.post("/sources")
async def add_sync_source(source: SyncSource) -> Dict[str, Any]:
    return {"status": "ready", "source": source.model_dump(), "message": "同步源接口已预留，可接入 OAuth/Webhook/IMAP 配置。"}


@router.delete("/sources/{source_name}")
async def delete_sync_source(source_name: str) -> Dict[str, str]:
    return {"status": "deleted", "source": source_name}


@router.post("/sync/{source_name}")
async def trigger_sync(source_name: str) -> Dict[str, str]:
    return {"status": "queued", "source": source_name, "message": "在线同步适配器接口已预留。"}


@router.get("/status")
async def get_sync_status(sync_service: SyncService = Depends(get_sync_service)) -> Dict[str, Any]:
    return {"statuses": await sync_service.get_sync_status()}


@router.post("/import/{source_name}")
async def import_source(
    source_name: str,
    file: UploadFile = File(...),
    sync_service: SyncService = Depends(get_sync_service),
) -> Dict[str, Any]:
    try:
        source = DataSource(source_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_name}") from exc

    content = await file.read()
    if source in (DataSource.WECHAT, DataSource.QQ):
        result = await sync_service.import_messages(content, user_id=1, source=source)
    else:
        result = await sync_service.import_text_document(content, user_id=1, source=source)
    return {"status": "success", "filename": file.filename, **result}


async def _async_import_worker(content: bytes, source_name: str, filename: str) -> Dict[str, Any]:
    source = DataSource(source_name)
    db = SessionLocal()
    try:
        sync_service = SyncService(db)
        if source in (DataSource.WECHAT, DataSource.QQ):
            result = await sync_service.import_messages(content, user_id=1, source=source)
        else:
            result = await sync_service.import_text_document(content, user_id=1, source=source)
        return result
    finally:
        db.close()


@router.post("/import/{source_name}/async")
async def import_source_async(
    source_name: str,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    try:
        source = DataSource(source_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_name}") from exc

    content = await file.read()
    tq = get_task_queue()
    task_id = await tq.enqueue(_async_import_worker, content, source_name, file.filename or "unknown")
    return {
        "status": "queued",
        "task_id": task_id,
        "filename": file.filename,
        "source": source_name,
        "message": "导入任务已提交，请通过 task_id 查询进度",
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    tq = get_task_queue()
    task = tq.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@router.get("/tasks")
async def list_tasks() -> Dict[str, Any]:
    tq = get_task_queue()
    return {
        "tasks": tq.get_all_tasks(),
        "pending": tq.pending_count,
    }
