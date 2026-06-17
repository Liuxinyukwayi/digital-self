from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.lightrag.lightrag_service import get_lightrag_service
from app.services.memory.memory_service import MemoryService
from app.services.llm.llm_client import get_llm_client


class RAGService:
    def __init__(self, memory_service: MemoryService, knowledge_service: KnowledgeService):
        self.memory_service = memory_service
        self.knowledge_service = knowledge_service

    async def retrieve_context(self, query: str, user_id: int, limit: int = 6) -> Dict[str, Any]:
        lightrag = get_lightrag_service()

        tasks = {
            "memories": self.memory_service.search_memories(query, user_id, limit),
            "knowledge": self.knowledge_service.search_knowledge(query, user_id, limit),
        }

        if lightrag.enabled:
            tasks["lightrag"] = lightrag.query(query)

        results = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as exc:
                print(f"RAG retrieval {key} failed: {exc}")
                results[key] = None if key == "lightrag" else []

        memories = results.get("memories") or []
        knowledge = results.get("knowledge") or []
        lightrag_context = results.get("lightrag")

        context_parts: List[str] = []

        if memories:
            context_parts.append("【相关记忆】")
            for index, memory in enumerate(memories, 1):
                text = memory.get("summary") or memory.get("content", "")
                context_parts.append(
                    f"{index}. {text[:700]} (重要性: {memory.get('importance', '-')}, 相关度: {memory.get('score', '-')})"
                )

        if lightrag_context:
            context_parts.append("\n【知识图谱检索】")
            context_parts.append(lightrag_context[:1500])

        if knowledge:
            context_parts.append("\n【相关知识库片段】")
            for index, item in enumerate(knowledge, 1):
                title = item.get("title", "未命名")
                content = item.get("content", "")
                context_parts.append(
                    f"{index}. 《{title}》片段: {content[:900]} (相关度: {item.get('score', '-')})"
                )

        return {
            "memories": memories,
            "knowledge": knowledge,
            "lightrag_context": lightrag_context,
            "context_text": "\n".join(context_parts),
        }

    async def generate_response(self, query: str, user_id: int, persona: Optional[Dict] = None) -> str:
        context = await self.retrieve_context(query, user_id)

        system_prompt = (
            "你是一个数字分身，必须优先基于给定的长期记忆和知识库片段回答。"
            "如果资料不足，请明确说明缺少哪些信息。用中文，保持自然对话。"
        )
        if persona:
            system_prompt += f"\n\nPersona: {persona}"

        user_prompt = f"用户问题：{query}\n\n可用上下文：\n{context['context_text']}"
        llm = get_llm_client()
        return await llm.simple_chat(user_prompt, system_prompt)
