from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.lightrag.lightrag_service import get_lightrag_service
from app.models.models import Knowledge

router = APIRouter()


class KnowledgeCreate(BaseModel):
    title: str
    content: Optional[str] = None
    content_type: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    content: Optional[str]
    content_type: Optional[str]
    category: Optional[str]
    tags: List[str]

    class Config:
        from_attributes = True


def get_knowledge_service(db: Session = Depends(get_db)):
    return KnowledgeService(db)


@router.post("/", response_model=KnowledgeResponse)
async def create_knowledge(
    knowledge: KnowledgeCreate,
    db: Session = Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    result = await knowledge_service.create_knowledge(
        title=knowledge.title,
        user_id=1,
        content=knowledge.content,
        content_type=knowledge.content_type,
        category=knowledge.category,
        tags=knowledge.tags,
    )
    return KnowledgeResponse(
        id=result.id,
        title=result.title,
        content=result.content,
        content_type=result.content_type,
        category=result.category,
        tags=result.tags or [],
    )


@router.get("/")
async def get_knowledge_list(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Knowledge).filter(Knowledge.user_id == 1)
    if category:
        query = query.filter(Knowledge.category == category)
    total = query.count()
    items = query.order_by(Knowledge.created_at.desc()).offset(skip).limit(limit).all()
    result = [
        KnowledgeResponse(
            id=k.id,
            title=k.title,
            content=k.content,
            content_type=k.content_type,
            category=k.category,
            tags=k.tags or [],
        )
        for k in items
    ]
    return {"items": result, "total": total, "skip": skip, "limit": limit}


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return KnowledgeResponse(
        id=knowledge.id,
        title=knowledge.title,
        content=knowledge.content,
        content_type=knowledge.content_type,
        category=knowledge.category,
        tags=knowledge.tags or [],
    )


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    db.delete(knowledge)
    db.commit()
    return {"status": "deleted"}


@router.post("/upload")
async def upload_knowledge(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    text_content = content.decode("utf-8", errors="ignore")

    lightrag = get_lightrag_service()
    if lightrag.enabled:
        result = await lightrag.insert_document(text_content, {"title": file.filename})
        knowledge_service = KnowledgeService(db)
        db_record = await knowledge_service.create_knowledge(
            title=file.filename,
            user_id=1,
            content=text_content[:2000],
            content_type=file.content_type,
            tags=["lightrag"],
        )
        return {
            "filename": file.filename,
            "status": "uploaded",
            "id": db_record.id,
            "storage": "lightrag+db",
            "lightrag_status": result.get("status"),
        }

    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.create_knowledge(
        title=file.filename,
        user_id=1,
        content=text_content,
        content_type=file.content_type,
    )
    return {"filename": file.filename, "status": "uploaded", "id": result.id, "storage": "db"}


@router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    db: Session = Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    results = await knowledge_service.search_knowledge(request.query, user_id=1, limit=request.limit)
    return {"results": results}
