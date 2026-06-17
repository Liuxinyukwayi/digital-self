from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.llm import get_available_providers
from app.services.llm.llm_client import _is_real_key, _get_provider_config, FAKE_KEYS

router = APIRouter()

ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"


class SettingsUpdate(BaseModel):
    active_provider: Optional[str] = None
    mimo_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_api_base: Optional[str] = None
    custom_model: Optional[str] = None
    embedding_mode: Optional[str] = None
    short_term_memory_limit: Optional[int] = None
    memory_importance_threshold: Optional[int] = None
    distill_schedule: Optional[str] = None


def update_env_file(updates: Dict[str, str]) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()

    content = ENV_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    result_lines = []
    handled_keys = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            result_lines.append(line)
            continue
        match = re.match(r"^([A-Z_]+)\s*=", stripped)
        if match:
            key = match.group(1)
            if key in updates:
                result_lines.append(f"{key}={updates[key]}")
                handled_keys.add(key)
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    for key, value in updates.items():
        if key not in handled_keys:
            result_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(result_lines) + "\n", encoding="utf-8")


def apply_settings(updates: Dict[str, Any]) -> None:
    if "ACTIVE_PROVIDER" in updates:
        settings.ACTIVE_PROVIDER = updates["ACTIVE_PROVIDER"]
    if "MIMO_API_KEY" in updates:
        settings.MIMO_API_KEY = updates["MIMO_API_KEY"]
    if "DEEPSEEK_API_KEY" in updates:
        settings.DEEPSEEK_API_KEY = updates["DEEPSEEK_API_KEY"]
    if "OPENAI_API_KEY" in updates:
        settings.OPENAI_API_KEY = updates["OPENAI_API_KEY"]
    if "CUSTOM_API_KEY" in updates:
        settings.CUSTOM_API_KEY = updates["CUSTOM_API_KEY"]
    if "CUSTOM_API_BASE" in updates:
        settings.CUSTOM_API_BASE = updates["CUSTOM_API_BASE"]
    if "CUSTOM_MODEL" in updates:
        settings.CUSTOM_MODEL = updates["CUSTOM_MODEL"]
    if "EMBEDDING_MODE" in updates:
        settings.EMBEDDING_MODE = updates["EMBEDDING_MODE"]
    if "SHORT_TERM_MEMORY_LIMIT" in updates:
        settings.SHORT_TERM_MEMORY_LIMIT = updates["SHORT_TERM_MEMORY_LIMIT"]
    if "MEMORY_IMPORTANCE_THRESHOLD" in updates:
        settings.MEMORY_IMPORTANCE_THRESHOLD = updates["MEMORY_IMPORTANCE_THRESHOLD"]
    if "DISTILL_SCHEDULE" in updates:
        settings.DISTILL_SCHEDULE = updates["DISTILL_SCHEDULE"]


def mask_key(key: Optional[str]) -> str:
    if not _is_real_key(key):
        return ""
    if len(key) <= 8:
        return key[:2] + "****" + key[-2:]
    return key[:4] + "****" + key[-4:]


@router.get("/")
async def get_settings() -> Dict[str, Any]:
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "active_provider": settings.ACTIVE_PROVIDER,
        "mimo_model": settings.MIMO_MODEL,
        "mimo_configured": _is_real_key(settings.MIMO_API_KEY),
        "mimo_key_masked": mask_key(settings.MIMO_API_KEY),
        "deepseek_model": settings.DEEPSEEK_MODEL,
        "deepseek_configured": _is_real_key(settings.DEEPSEEK_API_KEY),
        "deepseek_key_masked": mask_key(settings.DEEPSEEK_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "openai_configured": _is_real_key(settings.OPENAI_API_KEY),
        "openai_key_masked": mask_key(settings.OPENAI_API_KEY),
        "custom_model": settings.CUSTOM_MODEL,
        "custom_api_base": settings.CUSTOM_API_BASE,
        "custom_configured": _is_real_key(settings.CUSTOM_API_KEY),
        "custom_key_masked": mask_key(settings.CUSTOM_API_KEY),
        "qdrant_enabled": settings.QDRANT_ENABLED,
        "lightrag_enabled": settings.LIGHTRAG_ENABLED,
        "embedding_mode": settings.EMBEDDING_MODE,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "short_term_memory_limit": settings.SHORT_TERM_MEMORY_LIMIT,
        "memory_importance_threshold": settings.MEMORY_IMPORTANCE_THRESHOLD,
        "distill_schedule": settings.DISTILL_SCHEDULE,
    }


@router.get("/providers")
async def get_providers() -> List[Dict[str, Any]]:
    return get_available_providers()


@router.post("/")
async def update_settings(update: SettingsUpdate) -> Dict[str, Any]:
    env_updates: Dict[str, str] = {}
    memory_updates: Dict[str, Any] = {}

    if update.active_provider:
        env_updates["ACTIVE_PROVIDER"] = update.active_provider
        memory_updates["ACTIVE_PROVIDER"] = update.active_provider

    if update.mimo_api_key:
        env_updates["MIMO_API_KEY"] = update.mimo_api_key
        memory_updates["MIMO_API_KEY"] = update.mimo_api_key

    if update.deepseek_api_key:
        env_updates["DEEPSEEK_API_KEY"] = update.deepseek_api_key
        memory_updates["DEEPSEEK_API_KEY"] = update.deepseek_api_key

    if update.openai_api_key:
        env_updates["OPENAI_API_KEY"] = update.openai_api_key
        memory_updates["OPENAI_API_KEY"] = update.openai_api_key

    if update.custom_api_key:
        env_updates["CUSTOM_API_KEY"] = update.custom_api_key
        memory_updates["CUSTOM_API_KEY"] = update.custom_api_key

    if update.custom_api_base:
        env_updates["CUSTOM_API_BASE"] = update.custom_api_base
        memory_updates["CUSTOM_API_BASE"] = update.custom_api_base

    if update.custom_model:
        env_updates["CUSTOM_MODEL"] = update.custom_model
        memory_updates["CUSTOM_MODEL"] = update.custom_model

    if update.embedding_mode:
        env_updates["EMBEDDING_MODE"] = update.embedding_mode
        memory_updates["EMBEDDING_MODE"] = update.embedding_mode

    if update.short_term_memory_limit is not None:
        env_updates["SHORT_TERM_MEMORY_LIMIT"] = str(update.short_term_memory_limit)
        memory_updates["SHORT_TERM_MEMORY_LIMIT"] = update.short_term_memory_limit

    if update.memory_importance_threshold is not None:
        env_updates["MEMORY_IMPORTANCE_THRESHOLD"] = str(update.memory_importance_threshold)
        memory_updates["MEMORY_IMPORTANCE_THRESHOLD"] = update.memory_importance_threshold

    if update.distill_schedule:
        env_updates["DISTILL_SCHEDULE"] = update.distill_schedule
        memory_updates["DISTILL_SCHEDULE"] = update.distill_schedule

    saved_keys = []
    if env_updates:
        update_env_file(env_updates)
        apply_settings(memory_updates)
        saved_keys = list(env_updates.keys())

    return {
        "status": "saved",
        "saved_keys": saved_keys,
        "active_provider": settings.ACTIVE_PROVIDER,
    }


@router.post("/check-ollama")
async def check_ollama() -> Dict[str, Any]:
    from app.services.embedding.embedding_service import OllamaEmbeddingService
    svc = OllamaEmbeddingService()
    result = await svc.check_and_init()
    if svc.is_available():
        import app.services.embedding.embedding_service as emb_mod
        emb_mod._embedding_service = svc
        result["status"] = "ready"
    else:
        result["status"] = "unavailable"
    return result
