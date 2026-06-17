from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.embedding.embedding_service import get_embedding_service, hashed_embedding
from app.services.llm.llm_client import get_llm_client


class LightRAGService:
    def __init__(self):
        self._rag = None
        self._initialized = False
        self._error: Optional[str] = None

        if not settings.LIGHTRAG_ENABLED:
            self._error = "LightRAG disabled in config"
            return

        try:
            from lightrag import LightRAG
            from lightrag.base import EmbeddingFunc
        except ImportError:
            self._error = "lightrag-hku not installed"
            print(f"LightRAG disabled: {self._error}")
            return

        working_dir = settings.LIGHTRAG_WORKING_DIR
        os.makedirs(working_dir, exist_ok=True)

        try:
            embedding_func = EmbeddingFunc(
                embedding_dim=settings.EMBEDDING_DIMENSION,
                func=self._embedding_adapter,
                max_token_size=8000,
            )
            self._rag = LightRAG(
                working_dir=working_dir,
                llm_model_func=self._llm_adapter,
                embedding_func=embedding_func,
            )
            self._initialized = True
        except Exception as exc:
            self._error = str(exc)
            print(f"LightRAG init failed: {exc}")

    @property
    def enabled(self) -> bool:
        return self._initialized and self._rag is not None

    @property
    def error(self) -> Optional[str]:
        return self._error

    async def insert_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "skipped", "reason": self._error}

        try:
            await self._rag.ainsert(content)
            return {"status": "success", "content_length": len(content)}
        except Exception as exc:
            print(f"LightRAG insert failed: {exc}")
            return {"status": "error", "reason": str(exc)}

    async def query(self, question: str, mode: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None

        query_mode = mode or settings.LIGHTRAG_QUERY_MODE
        try:
            from lightrag import QueryParam
            result = await self._rag.aquery(question, QueryParam(mode=query_mode))
            return result
        except Exception as exc:
            print(f"LightRAG query failed: {exc}")
            return None

    async def _llm_adapter(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List] = None,
        **kwargs,
    ) -> str:
        llm = get_llm_client()
        effective_system = system_prompt or "你是一个知识检索助手，用中文回答。"
        return await llm.simple_chat(prompt, effective_system)

    async def _embedding_adapter(self, texts: List[str]) -> List[List[float]]:
        svc = get_embedding_service()
        results = await svc.embed_batch(texts)
        final = []
        for text, vec in zip(texts, results):
            if vec:
                final.append(vec)
            else:
                final.append(hashed_embedding(text, settings.EMBEDDING_DIMENSION))
        return final


_lightrag_service: Optional[LightRAGService] = None


def get_lightrag_service() -> LightRAGService:
    global _lightrag_service
    if _lightrag_service is None:
        _lightrag_service = LightRAGService()
    return _lightrag_service


lightrag_service = None


def __getattr__(name: str):
    if name == "lightrag_service":
        return get_lightrag_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
