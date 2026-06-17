from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Knowledge
from app.services.rag.text_index import chunk_text, get_embedding, get_embeddings_batch, rank_documents


class KnowledgeService:
    collection_name = "digital_self_knowledge"

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
                print(f"Qdrant knowledge disabled, using TF-IDF retrieval: {exc}")

    def _ensure_collection(self) -> None:
        if not self.qdrant:
            return
        try:
            collections = self.qdrant.get_collections().collections
            collection_names = [collection.name for collection in collections]
            if self.collection_name in collection_names:
                info = self.qdrant.get_collection(self.collection_name)
                current_size = info.config.params.vectors.size
                if current_size != self.vector_size:
                    self.qdrant.delete_collection(self.collection_name)
                    collection_names.remove(self.collection_name)
            if self.collection_name not in collection_names:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
        except Exception as exc:
            print(f"Qdrant knowledge collection setup failed: {exc}")

    async def create_knowledge(
        self,
        title: str,
        user_id: int,
        content: Optional[str] = None,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Knowledge:
        chunks = chunk_text(content)
        embedding_id = f"knowledge_{user_id}_{hashlib.sha1((title + (content or '')).encode('utf-8')).hexdigest()[:16]}"

        knowledge = Knowledge(
            user_id=user_id,
            title=title,
            content=content or "",
            content_type=content_type or "text/plain",
            category=category or "未分类",
            tags=tags or [],
            metadata_={"chunk_count": max(1, len(chunks)), "retrieval": "semantic-qdrant"},
            embedding_id=embedding_id,
        )
        self.db.add(knowledge)
        self.db.commit()
        self.db.refresh(knowledge)

        await self._upsert_knowledge_vectors(knowledge, user_id, chunks or [content or title])
        return knowledge

    async def search_knowledge(self, query: str, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        qdrant_results = await self._search_qdrant(query, user_id, limit)
        if qdrant_results:
            return qdrant_results

        items = (
            self.db.query(Knowledge)
            .filter(Knowledge.user_id == user_id)
            .order_by(Knowledge.created_at.desc())
            .limit(250)
            .all()
        )

        documents = []
        for item in items:
            chunks = chunk_text(item.content) or [item.content or item.title]
            for index, chunk in enumerate(chunks):
                documents.append(
                    {
                        "id": item.id,
                        "knowledge_id": item.id,
                        "title": item.title,
                        "content": chunk,
                        "full_content": item.content,
                        "category": item.category,
                        "tags": item.tags or [],
                        "chunk_index": index,
                    }
                )

        return rank_documents(query, documents, limit=limit)

    async def _upsert_knowledge_vectors(self, knowledge: Knowledge, user_id: int, chunks: List[str]) -> None:
        if not self.qdrant or not knowledge.embedding_id:
            return

        truncated_chunks = [f"{knowledge.title}\n{chunk}" for chunk in chunks[:200]]
        try:
            vectors = await get_embeddings_batch(truncated_chunks)
        except Exception as exc:
            print(f"Knowledge embedding failed: {exc}")
            return

        points = []
        for index, (chunk, vector) in enumerate(zip(chunks[:200], vectors)):
            if not vector:
                continue
            point_key = f"{knowledge.embedding_id}_{index}"
            point_id = int(hashlib.sha1(point_key.encode("utf-8")).hexdigest()[:16], 16)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "kind": "knowledge",
                        "knowledge_id": knowledge.id,
                        "user_id": user_id,
                        "title": knowledge.title,
                        "category": knowledge.category,
                        "chunk_index": index,
                        "chunk": chunk[:1600],
                    },
                )
            )

        if not points:
            return
        try:
            self.qdrant.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            print(f"Qdrant knowledge upsert skipped: {exc}")

    async def _search_qdrant(self, query: str, user_id: int, limit: int) -> List[Dict[str, Any]]:
        if not self.qdrant:
            return []
        try:
            query_vector = await get_embedding(query)
            if not query_vector:
                return []
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit * 3,
            )
        except Exception as exc:
            print(f"Qdrant knowledge search skipped: {exc}")
            return []

        knowledge_items = []
        for result in results:
            payload = result.payload or {}
            if payload.get("user_id") != user_id:
                continue
            knowledge = self.db.query(Knowledge).filter(Knowledge.id == payload.get("knowledge_id")).first()
            if not knowledge:
                continue
            knowledge_items.append(
                {
                    "id": knowledge.id,
                    "knowledge_id": knowledge.id,
                    "title": knowledge.title,
                    "content": payload.get("chunk") or knowledge.content,
                    "full_content": knowledge.content,
                    "category": knowledge.category,
                    "tags": knowledge.tags or [],
                    "chunk_index": payload.get("chunk_index", 0),
                    "score": round(float(result.score), 4),
                }
            )
            if len(knowledge_items) >= limit:
                break
        return knowledge_items
