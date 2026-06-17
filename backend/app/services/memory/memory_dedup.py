from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import Memory
from app.services.rag.text_index import get_embedding, tokenize, _tfidf_vector, _cosine


class MemoryDedupService:
    def __init__(self, db: Session):
        self.db = db

    async def check_and_merge(self, content: str, user_id: int, threshold: float = 0.92) -> Optional[Memory]:
        similar = await self._find_similar(content, user_id, threshold)
        if similar:
            similar.evidence_count = (similar.evidence_count or 1) + 1
            similar.confidence = min(1.0, (similar.evidence_count or 1) * 0.1)
            similar.last_evidence_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(similar)
            return similar
        return None

    async def _find_similar(self, content: str, user_id: int, threshold: float) -> Optional[Memory]:
        from app.core.config import settings
        from qdrant_client import QdrantClient

        qdrant = None
        if settings.QDRANT_ENABLED and settings.EMBEDDING_MODE == "full":
            try:
                qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2)
            except Exception:
                qdrant = None

        if qdrant:
            try:
                vector = await get_embedding(content)
                if vector:
                    results = qdrant.search(
                        collection_name=settings.QDRANT_COLLECTION,
                        query_vector=vector,
                        limit=1,
                        score_threshold=threshold,
                    )
                    if results:
                        payload = results[0].payload or {}
                        if payload.get("user_id") == user_id:
                            memory_id = payload.get("memory_id")
                            if memory_id:
                                return self.db.query(Memory).filter(Memory.id == memory_id).first()
            except Exception:
                pass

        return self._find_similar_tfidf(content, user_id, threshold)

    def _find_similar_tfidf(self, content: str, user_id: int, threshold: float) -> Optional[Memory]:
        recent = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(200)
            .all()
        )
        if not recent:
            return None

        tokens_new = tokenize(content)
        if not tokens_new:
            return None

        from collections import Counter
        all_tokens = set(tokens_new)
        for memory in recent:
            all_tokens.update(tokenize(memory.content))
        idf = {token: 1.0 for token in all_tokens}

        vec_new = _tfidf_vector(tokens_new, idf)

        for memory in recent:
            tokens_old = tokenize(memory.content)
            if not tokens_old:
                continue
            vec_old = _tfidf_vector(tokens_old, idf)
            similarity = _cosine(vec_new, vec_old)
            if similarity >= threshold:
                if memory.memory_type == memory.memory_type:
                    return memory
        return None

    async def bulk_dedup(self, user_id: int) -> Dict[str, Any]:
        memories = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.created_at)
            .all()
        )

        merged_count = 0
        seen_ids = set()

        for i, memory in enumerate(memories):
            if memory.id in seen_ids:
                continue
            for j in range(i + 1, len(memories)):
                other = memories[j]
                if other.id in seen_ids:
                    continue
                if memory.memory_type != other.memory_type:
                    continue
                similarity = self._compute_similarity(memory.content, other.content)
                if similarity >= 0.92:
                    memory.evidence_count = (memory.evidence_count or 1) + (other.evidence_count or 1)
                    memory.confidence = min(1.0, (memory.evidence_count or 1) * 0.1)
                    memory.last_evidence_at = datetime.utcnow()
                    seen_ids.add(other.id)
                    self.db.delete(other)
                    merged_count += 1

        self.db.commit()
        return {"merged": merged_count, "remaining": len(memories) - merged_count}

    def _compute_similarity(self, text1: str, text2: str) -> float:
        tokens1 = tokenize(text1)
        tokens2 = tokenize(text2)
        if not tokens1 or not tokens2:
            return 0.0
        all_tokens = set(tokens1) | set(tokens2)
        idf = {token: 1.0 for token in all_tokens}
        return _cosine(_tfidf_vector(tokens1, idf), _tfidf_vector(tokens2, idf))
