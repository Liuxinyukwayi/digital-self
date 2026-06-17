from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import DataSource, Memory, MemoryType
from app.services.llm.llm_client import get_llm_client
from app.services.rag.text_index import get_embedding, get_embeddings_batch, rank_documents


class MemoryService:
    def __init__(self, db: Session):
        self.db = db
        self.vector_size = settings.EMBEDDING_DIMENSION
        self.qdrant: QdrantClient | None = None
        if settings.QDRANT_ENABLED and settings.EMBEDDING_MODE == "full":
            try:
                self.qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2)
                self._ensure_collection()
            except Exception as exc:
                self.qdrant = None
                print(f"Qdrant memory disabled, using TF-IDF retrieval: {exc}")

    def _ensure_collection(self) -> None:
        if not self.qdrant:
            return
        try:
            collections = self.qdrant.get_collections().collections
            collection_names = [collection.name for collection in collections]
            if settings.QDRANT_COLLECTION in collection_names:
                info = self.qdrant.get_collection(settings.QDRANT_COLLECTION)
                current_size = info.config.params.vectors.size
                if current_size != self.vector_size:
                    self.qdrant.delete_collection(settings.QDRANT_COLLECTION)
                    collection_names.remove(settings.QDRANT_COLLECTION)
            if settings.QDRANT_COLLECTION not in collection_names:
                self.qdrant.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
        except Exception as exc:
            print(f"Qdrant collection setup failed: {exc}")

    async def create_memory(
        self,
        content: str,
        user_id: int,
        summary: Optional[str] = None,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        source: Optional[str | DataSource] = None,
        importance: int = 5,
        tags: Optional[List[str]] = None,
        skip_dedup: bool = False,
    ) -> Memory:
        source_value = self._parse_source(source)
        embedding_id = f"memory_{user_id}_{hashlib.sha1(content.encode('utf-8')).hexdigest()[:16]}"

        if not skip_dedup:
            existing = await self._find_similar_memory(content, user_id)
            if existing:
                existing.evidence_count = (existing.evidence_count or 1) + 1
                existing.confidence = min(1.0, (existing.evidence_count or 1) * 0.1)
                existing.last_evidence_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(existing)
                return existing

        memory = Memory(
            user_id=user_id,
            content=content,
            summary=summary,
            memory_type=memory_type,
            source=source_value,
            importance=max(1, min(10, importance)),
            tags=tags or [],
            embedding_id=embedding_id,
            evidence_count=1,
            confidence=0.5,
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        await self._upsert_memory_vector(memory, user_id)
        return memory

    async def search_memories(self, query: str, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        qdrant_results = await self._search_qdrant(query, user_id, limit)
        if qdrant_results:
            for result in qdrant_results:
                memory = self.db.query(Memory).filter(Memory.id == result["id"]).first()
                if memory:
                    result["score"] = self.calculate_memory_score(memory, result.get("score", 0.5))
            qdrant_results.sort(key=lambda r: r["score"], reverse=True)
            return qdrant_results[:limit]

        memories = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(500)
            .all()
        )
        documents = [
            {
                "id": memory.id,
                "content": memory.content,
                "summary": memory.summary,
                "importance": memory.importance,
                "memory_type": memory.memory_type.value if memory.memory_type else None,
                "source": memory.source.value if memory.source else None,
                "tags": memory.tags or [],
            }
            for memory in memories
        ]
        results = rank_documents(query, documents, title_key=None, limit=limit)
        for result in results:
            memory = self.db.query(Memory).filter(Memory.id == result["id"]).first()
            if memory:
                result["score"] = self.calculate_memory_score(memory, result.get("score", 0.5))
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def calculate_memory_score(self, memory: Memory, relevance_score: float = 0.5) -> float:
        importance = (memory.importance or 5) / 10.0
        confidence = memory.confidence or 0.5
        days_old = (datetime.utcnow() - (memory.created_at or datetime.utcnow())).days
        freshness = math.exp(-days_old / 365)
        return round(importance * confidence * freshness * 0.6 + relevance_score * 0.4, 4)

    async def distill_memories(self, user_id: int) -> Dict[str, Any]:
        week_ago = datetime.utcnow() - timedelta(days=7)
        memories = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.created_at >= week_ago)
            .filter(Memory.memory_type != MemoryType.SEMANTIC)
            .order_by(Memory.importance.desc())
            .limit(200)
            .all()
        )

        if not memories:
            return {"distilled": 0, "summaries": [], "categories": {}}

        grouped: Dict[str, List[Memory]] = {}
        for memory in memories:
            type_key = memory.memory_type.value if memory.memory_type else "episodic"
            grouped.setdefault(type_key, []).append(memory)

        distill_prompts = {
            "episodic": "将以下零散经历提炼为关键事件摘要，每条用一句话概括，保持简洁：",
            "fact": "从以下内容提取关键事实，形成简洁的事实清单：",
            "preference": "从以下内容总结用户的偏好和喜好，形成偏好列表：",
            "opinion": "从以下内容提炼用户的核心观点和看法：",
            "goal": "从以下内容整理用户的目标和计划：",
            "relationship": "从以下内容提取人物关系信息：",
            "short_term": "将以下短期记忆中有价值的内容提炼为长期记忆：",
            "long_term": "将以下长期记忆精炼压缩：",
        }

        llm = get_llm_client()
        summaries = []
        categories = {}

        for type_key, type_memories in grouped.items():
            if not type_memories:
                continue
            combined = "\n".join([f"- {m.content}" for m in type_memories[:30]])
            prompt = distill_prompts.get(type_key, distill_prompts["episodic"])
            try:
                summary = await llm.simple_chat(combined, prompt)
            except Exception:
                summary = "；".join(m.summary or m.content[:60] for m in type_memories[:5])

            distilled = await self.create_memory(
                content=summary,
                user_id=user_id,
                summary=f"[{type_key}] 蒸馏记忆 ({len(type_memories)}条)",
                memory_type=MemoryType.SEMANTIC,
                source=DataSource.MANUAL,
                importance=8,
                tags=["distilled", "layer2", type_key],
                skip_dedup=True,
            )
            summaries.append({"type": type_key, "summary": summary, "id": distilled.id})
            categories[type_key] = len(type_memories)

        return {
            "distilled": len(memories),
            "summaries": summaries,
            "categories": categories,
            "layers": "layer2",
        }

    async def _upsert_memory_vector(self, memory: Memory, user_id: int) -> None:
        if not self.qdrant or not memory.embedding_id:
            return
        try:
            text = f"{memory.summary or ''}\n{memory.content}"
            vector = await get_embedding(text)
            if not vector:
                return
            point_id = int(hashlib.sha1(memory.embedding_id.encode("utf-8")).hexdigest()[:16], 16)
            self.qdrant.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "kind": "memory",
                            "memory_id": memory.id,
                            "user_id": user_id,
                            "importance": memory.importance,
                        },
                    )
                ],
            )
        except Exception as exc:
            print(f"Qdrant memory upsert skipped: {exc}")

    async def _search_qdrant(self, query: str, user_id: int, limit: int) -> List[Dict[str, Any]]:
        if not self.qdrant:
            return []
        try:
            query_vector = await get_embedding(query)
            if not query_vector:
                return []
            results = self.qdrant.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                query_filter=None,
                limit=limit * 2,
            )
        except Exception as exc:
            print(f"Qdrant memory search skipped: {exc}")
            return []

        memories = []
        for result in results:
            payload = result.payload or {}
            if payload.get("user_id") != user_id:
                continue
            memory = self.db.query(Memory).filter(Memory.id == payload.get("memory_id")).first()
            if not memory:
                continue
            memories.append(
                {
                    "id": memory.id,
                    "content": memory.content,
                    "summary": memory.summary,
                    "importance": memory.importance,
                    "memory_type": memory.memory_type.value if memory.memory_type else None,
                    "source": memory.source.value if memory.source else None,
                    "tags": memory.tags or [],
                    "score": round(float(result.score), 4),
                    "evidence_count": memory.evidence_count,
                    "confidence": memory.confidence,
                }
            )
            if len(memories) >= limit:
                break
        return memories

    async def _find_similar_memory(self, content: str, user_id: int, threshold: float = 0.92) -> Optional[Memory]:
        if self.qdrant:
            try:
                vector = await get_embedding(content)
                if vector:
                    results = self.qdrant.search(
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

        recent = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(200)
            .all()
        )
        for memory in recent:
            if self._text_similarity(content, memory.content) >= threshold:
                return memory
        return None

    def _text_similarity(self, text1: str, text2: str) -> float:
        from app.services.rag.text_index import tokenize, _tfidf_vector, _cosine
        tokens1 = tokenize(text1)
        tokens2 = tokenize(text2)
        if not tokens1 or not tokens2:
            return 0.0
        from collections import Counter
        all_tokens = set(tokens1) | set(tokens2)
        idf = {token: 1.0 for token in all_tokens}
        vec1 = _tfidf_vector(tokens1, idf)
        vec2 = _tfidf_vector(tokens2, idf)
        return _cosine(vec1, vec2)

    def _parse_source(self, source: Optional[str | DataSource]) -> Optional[DataSource]:
        if not source:
            return None
        if isinstance(source, DataSource):
            return source
        try:
            return DataSource(source)
        except ValueError:
            return DataSource.MANUAL
