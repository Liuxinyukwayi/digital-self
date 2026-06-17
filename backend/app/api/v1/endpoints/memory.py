from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.services.memory.memory_service import MemoryService
from app.services.memory.memory_dedup import MemoryDedupService
from app.services.distill.distill_service import DistillService
from app.models.models import Memory, MemoryType

router = APIRouter()


class MemoryCreate(BaseModel):
    content: str
    summary: Optional[str] = None
    memory_type: str = "long_term"
    source: Optional[str] = None
    importance: int = 5
    tags: List[str] = []


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class MemoryResponse(BaseModel):
    id: int
    content: str
    summary: Optional[str]
    memory_type: str
    importance: int
    tags: List[str]
    evidence_count: Optional[int] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


def get_memory_service(db: Session = Depends(get_db)):
    return MemoryService(db)


def get_dedup_service(db: Session = Depends(get_db)):
    return MemoryDedupService(db)


def get_distill_service(db: Session = Depends(get_db)):
    return DistillService(db)


@router.post("/", response_model=MemoryResponse)
async def create_memory(
    memory: MemoryCreate,
    db: Session = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
):
    memory_type = MemoryType(memory.memory_type) if memory.memory_type else MemoryType.LONG_TERM
    result = await memory_service.create_memory(
        content=memory.content,
        user_id=1,
        summary=memory.summary,
        memory_type=memory_type,
        source=memory.source,
        importance=memory.importance,
        tags=memory.tags,
    )
    return MemoryResponse(
        id=result.id,
        content=result.content,
        summary=result.summary,
        memory_type=result.memory_type.value,
        importance=result.importance,
        tags=result.tags or [],
        evidence_count=result.evidence_count,
        confidence=result.confidence,
    )


@router.get("/")
async def get_memories(
    skip: int = 0,
    limit: int = 50,
    memory_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Memory).filter(Memory.user_id == 1)
    if memory_type:
        query = query.filter(Memory.memory_type == memory_type)
    total = query.count()
    memories = query.order_by(Memory.created_at.desc()).offset(skip).limit(limit).all()
    items = [
        MemoryResponse(
            id=m.id,
            content=m.content,
            summary=m.summary,
            memory_type=m.memory_type.value,
            importance=m.importance,
            tags=m.tags or [],
            evidence_count=m.evidence_count,
            confidence=m.confidence,
        )
        for m in memories
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: int, db: Session = Depends(get_db)):
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        summary=memory.summary,
        memory_type=memory.memory_type.value,
        importance=memory.importance,
        tags=memory.tags or [],
        evidence_count=memory.evidence_count,
        confidence=memory.confidence,
    )


@router.delete("/{memory_id}")
async def delete_memory(memory_id: int, db: Session = Depends(get_db)):
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(memory)
    db.commit()
    return {"status": "deleted"}


@router.post("/search")
async def search_memories(
    request: SearchRequest,
    db: Session = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
):
    results = await memory_service.search_memories(request.query, user_id=1, limit=request.limit)
    return {"results": results}


@router.post("/distill")
async def distill_memories(
    db: Session = Depends(get_db),
    distill_service: DistillService = Depends(get_distill_service),
):
    result = await distill_service.distill_layer2(user_id=1)
    return {"status": "distilled", **result}


@router.post("/dedup")
async def dedup_memories(
    db: Session = Depends(get_db),
    dedup_service: MemoryDedupService = Depends(get_dedup_service),
):
    result = await dedup_service.bulk_dedup(user_id=1)
    return {"status": "deduped", **result}


@router.post("/distill/persona")
async def build_persona(
    db: Session = Depends(get_db),
    distill_service: DistillService = Depends(get_distill_service),
):
    result = await distill_service.build_persona(user_id=1)
    return result


@router.get("/distill/persona")
async def get_persona(
    db: Session = Depends(get_db),
    distill_service: DistillService = Depends(get_distill_service),
):
    result = await distill_service.get_persona(user_id=1)
    if not result:
        return {"status": "empty", "persona": None}
    return {"status": "ok", "persona": result}
