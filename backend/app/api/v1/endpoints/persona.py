from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.services.persona.persona_service import PersonaService
from app.models.models import Memory

router = APIRouter()


class PersonaTrait(BaseModel):
    name: str
    description: str
    weight: float = 1.0


class PersonaStyle(BaseModel):
    speaking_style: List[str]
    interests: List[str]
    values: List[str]


class PersonaResponse(BaseModel):
    name: str
    traits: List[PersonaTrait]
    style: PersonaStyle
    summary: str
    metadata: Dict[str, Any] = {}


def get_persona_service():
    return PersonaService()


@router.get("/", response_model=PersonaResponse)
async def get_persona(db: Session = Depends(get_db)):
    from app.models.models import User

    user = db.query(User).filter(User.id == 1).first()
    if user and user.persona_data:
        data = user.persona_data
        return PersonaResponse(
            name=data.get("name", "用户"),
            traits=[PersonaTrait(name=t, description="", weight=1.0) for t in data.get("traits", [])],
            style=PersonaStyle(
                speaking_style=data.get("speaking_style", []),
                interests=data.get("interests", []),
                values=data.get("values", []),
            ),
            summary=data.get("summary", ""),
        )

    return PersonaResponse(
        name="用户",
        traits=[],
        style=PersonaStyle(speaking_style=[], interests=[], values=[]),
        summary="尚未生成Persona，请点击'生成Persona'按钮",
    )


@router.post("/generate")
async def generate_persona(
    db: Session = Depends(get_db),
    persona_service: PersonaService = Depends(get_persona_service),
):
    from app.models.models import User

    memories = db.query(Memory).filter(Memory.user_id == 1).order_by(Memory.created_at.desc()).limit(200).all()

    if not memories:
        return {"status": "no_data", "message": "没有足够的聊天记录来生成Persona"}

    chat_records = [{"role": "user", "content": m.content} for m in memories]
    persona_data = await persona_service.generate_persona_from_chat(chat_records)

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="default_user", display_name="用户", persona_data=persona_data)
        db.add(user)
    else:
        user.persona_data = persona_data

    db.commit()

    return {"status": "generated", "persona": persona_data}


@router.put("/", response_model=PersonaResponse)
async def update_persona(persona: PersonaResponse, db: Session = Depends(get_db)):
    from app.models.models import User

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="default_user", display_name="用户")
        db.add(user)

    persona_data = {
        "name": persona.name,
        "traits": [t.name for t in persona.traits],
        "speaking_style": persona.style.speaking_style,
        "interests": persona.style.interests,
        "values": persona.style.values,
        "summary": persona.summary,
    }
    user.persona_data = persona_data
    db.commit()

    return persona


@router.post("/analyze")
async def analyze_persona(
    db: Session = Depends(get_db),
    persona_service: PersonaService = Depends(get_persona_service),
):
    memories = db.query(Memory).filter(Memory.user_id == 1).limit(100).all()
    texts = [m.content for m in memories]
    analysis = await persona_service.analyze_personality(texts)
    return {"analysis": analysis}


@router.post("/values")
async def analyze_values(
    db: Session = Depends(get_db),
    persona_service: PersonaService = Depends(get_persona_service),
):
    memories = db.query(Memory).filter(Memory.user_id == 1).limit(100).all()
    texts = [m.content for m in memories]
    values = await persona_service.extract_values(texts)
    return {"values": values}


@router.post("/preferences")
async def analyze_preferences(db: Session = Depends(get_db)):
    from app.services.distill.distill_service import DistillService

    distill_service = DistillService(db)
    preferences = await distill_service.analyze_decision_patterns(user_id=1)
    return {"preferences": preferences}
