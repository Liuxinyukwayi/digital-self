from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.models import User
from app.services.memory.memory_service import MemoryService
from app.services.llm.llm_client import get_llm_client
from app.services.rag.rag_service import RAGService


class AgentService:
    def __init__(self, rag_service: RAGService, memory_service: MemoryService, db: Session | None = None):
        self.rag_service = rag_service
        self.memory_service = memory_service
        self.db = db

    async def process_message(self, message: str, user_id: int, conversation_history: List[Dict] | None = None) -> Dict[str, Any]:
        context = await self.rag_service.retrieve_context(message, user_id)
        persona = self._load_persona(user_id)
        system_prompt = self._build_system_prompt(context, persona)

        history = (conversation_history or [])[-12:]
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]

        try:
            llm = get_llm_client()
            result = await llm.chat_completion(messages)
            reply = result["choices"][0]["message"]["content"]
        except Exception as exc:
            reply = self._local_rag_reply(message, context, exc)

        await self._create_memory_from_interaction(message, reply, user_id)

        return {
            "reply": reply,
            "memories_used": [str(memory.get("id")) for memory in context.get("memories", [])],
            "knowledge_used": [str(item.get("knowledge_id") or item.get("id")) for item in context.get("knowledge", [])],
            "context": context,
        }

    def _load_persona(self, user_id: int) -> Dict[str, Any]:
        if not self.db:
            return {}
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.persona_data if user and user.persona_data else {}

    def _build_system_prompt(self, context: Dict[str, Any], persona: Dict[str, Any]) -> str:
        prompt = """你是用户的数字分身，代表用户进行回答和对话。
要求：
1. 优先使用检索到的记忆、经历、知识库片段。
2. 尽量保持用户的说话风格、兴趣和价值观。
3. 不知道就说明不知道，不要编造来源。
4. 回答要自然、有帮助，默认使用中文。
"""
        if persona:
            prompt += f"\nPersona：{persona}\n"
        if context.get("context_text"):
            prompt += f"\n可用上下文：\n{context['context_text']}\n"
        return prompt

    def _local_rag_reply(self, message: str, context: Dict[str, Any], error: Exception) -> str:
        memory_lines = []
        for memory in context.get("memories", [])[:3]:
            memory_lines.append(f"- {memory.get('summary') or memory.get('content', '')[:180]}")

        knowledge_lines = []
        for item in context.get("knowledge", [])[:4]:
            knowledge_lines.append(f"- 《{item.get('title', '知识条目')}》：{item.get('content', '')[:220]}")

        if not memory_lines and not knowledge_lines:
            return (
                "我现在没有检索到足够相关的记忆或知识库内容。"
                "可以先导入聊天记录、文章或项目文档，再问我更具体的问题。"
            )

        sections = ["我先基于已检索到的资料回答："]
        if memory_lines:
            sections.append("\n相关记忆：\n" + "\n".join(memory_lines))
        if knowledge_lines:
            sections.append("\n相关知识：\n" + "\n".join(knowledge_lines))
        sections.append("\nMIMO API 暂时不可用，因此这是本地 RAG 摘要回答。")
        return "\n".join(sections)

    async def _create_memory_from_interaction(self, user_message: str, agent_reply: str, user_id: int) -> None:
        content = f"用户问：{user_message}\n数字分身回答：{agent_reply}"
        await self.memory_service.create_memory(
            content=content,
            user_id=user_id,
            summary=f"对话：{user_message[:60]}",
            importance=3,
            tags=["conversation", "short-term"],
        )
