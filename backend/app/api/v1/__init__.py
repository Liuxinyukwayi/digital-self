from fastapi import APIRouter
from app.api.v1.endpoints import chat, knowledge, memory, persona, settings, sync, timeline

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(persona.router, prefix="/persona", tags=["persona"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
