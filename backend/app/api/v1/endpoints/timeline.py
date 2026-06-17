from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Event, Memory

router = APIRouter()


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    event_type: str = "manual"
    importance: int = 5
    tags: List[str] = []


@router.get("/")
async def get_timeline(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    events = (
        db.query(Event)
        .filter(Event.user_id == 1)
        .all()
    )
    memories = (
        db.query(Memory)
        .filter(Memory.user_id == 1)
        .all()
    )

    timeline = []
    for event in events:
        timeline.append({
            "id": str(event.id),
            "source_type": "event",
            "title": event.title,
            "description": event.description,
            "date": (event.event_date or event.created_at).isoformat() if (event.event_date or event.created_at) else None,
            "sort_key": event.event_date or event.created_at,
            "type": event.event_type,
            "importance": event.importance,
            "tags": event.tags or [],
        })
    for memory in memories:
        timeline.append({
            "id": f"memory-{memory.id}",
            "source_type": "memory",
            "title": memory.summary or memory.content[:40],
            "description": memory.content[:260],
            "date": memory.created_at.isoformat() if memory.created_at else None,
            "sort_key": memory.created_at,
            "type": memory.source.value if memory.source else memory.memory_type.value,
            "importance": memory.importance,
            "tags": memory.tags or [],
        })

    timeline.sort(key=lambda x: x["sort_key"] or datetime.min, reverse=True)
    total = len(timeline)

    for item in timeline:
        del item["sort_key"]

    page = timeline[skip: skip + limit]

    return {"items": page, "total": total, "skip": skip, "limit": limit}


@router.post("/")
async def create_event(event: EventCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    created = Event(
        user_id=1,
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        event_type=event.event_type,
        importance=event.importance,
        tags=event.tags,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "id": created.id}


@router.delete("/{event_id}")
async def delete_event(event_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if event_id.startswith("memory-"):
        memory_id = int(event_id.replace("memory-", ""))
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        db.delete(memory)
        db.commit()
        return {"status": "deleted", "type": "memory", "id": memory_id}
    else:
        try:
            eid = int(event_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event id")
        event = db.query(Event).filter(Event.id == eid).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        db.delete(event)
        db.commit()
        return {"status": "deleted", "type": "event", "id": eid}
