from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.services.memory.memory_service import MemoryService
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.rag.rag_service import RAGService
from app.services.agent.agent_service import AgentService
from app.models.models import Conversation, Message

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    memories_used: List[str] = []
    knowledge_used: List[str] = []


def get_agent_service(db: Session = Depends(get_db)):
    memory_service = MemoryService(db)
    knowledge_service = KnowledgeService(db)
    rag_service = RAGService(memory_service, knowledge_service)
    return AgentService(rag_service, memory_service, db)


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    user_id = 1
    from app.models.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="default_user", display_name="用户", persona_data={})
        db.add(user)
        db.commit()

    conversation = None
    if request.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()

    if not conversation:
        conversation = Conversation(user_id=user_id, title=request.message[:50])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    result = await agent_service.process_message(request.message, user_id, history)

    user_msg = Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_msg)

    agent_msg = Message(conversation_id=conversation.id, role="assistant", content=result["reply"])
    db.add(agent_msg)
    db.commit()

    return ChatResponse(
        reply=result["reply"],
        conversation_id=conversation.id,
        memories_used=result.get("memories_used", []),
        knowledge_used=result.get("knowledge_used", []),
    )


@router.post("/rag/search")
async def rag_search(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    context = await agent_service.rag_service.retrieve_context(request.message, user_id=1, limit=8)
    return context


@router.get("/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    conversations = db.query(Conversation).all()
    return {
        "conversations": [
            {"id": c.id, "title": c.title, "created_at": str(c.created_at)}
            for c in conversations
        ]
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )

    return {
        "conversation_id": conversation.id,
        "title": conversation.title,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()

    return {"status": "deleted", "conversation_id": conversation_id}
