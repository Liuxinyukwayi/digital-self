from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.models import Memory, MemoryType, DataSource, PersonaProfile
from app.services.llm.llm_client import get_llm_client


PERSONA_PROMPT = """基于以下长期记忆，构建用户人格画像。
输出 JSON 格式（不要输出其他内容）：
{
  "interests": ["兴趣1", "兴趣2"],
  "values": ["价值观1", "价值观2"],
  "goals": ["目标1", "目标2"],
  "speech_style": ["口头禅1", "口头禅2"],
  "thinking_style": "思维风格描述"
}

长期记忆：
{semantic_memories}

人格画像："""


class DistillService:
    def __init__(self, db: Session):
        self.db = db

    async def distill_layer2(self, user_id: int) -> Dict[str, Any]:
        from app.services.memory.memory_service import MemoryService
        memory_service = MemoryService(self.db)
        return await memory_service.distill_memories(user_id)

    async def build_persona(self, user_id: int) -> Dict[str, Any]:
        semantic_memories = (
            self.db.query(Memory)
            .filter(
                Memory.user_id == user_id,
                Memory.memory_type == MemoryType.SEMANTIC,
            )
            .order_by(Memory.created_at.desc())
            .limit(50)
            .all()
        )

        if not semantic_memories:
            return {"status": "skipped", "reason": "no semantic memories"}

        combined = "\n".join([f"- {m.content}" for m in semantic_memories])

        llm = get_llm_client()
        try:
            response = await llm.simple_chat(
                PERSONA_PROMPT.format(semantic_memories=combined),
                "你是一个人格画像构建助手，只返回JSON。",
            )
            import json, re
            cleaned = response.strip()
            fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
            if fenced:
                cleaned = fenced.group(1).strip()
            persona_data = json.loads(cleaned)
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

        existing = (
            self.db.query(PersonaProfile)
            .filter(PersonaProfile.user_id == user_id)
            .order_by(PersonaProfile.version.desc())
            .first()
        )
        new_version = (existing.version or 0) + 1 if existing else 1

        profile = PersonaProfile(
            user_id=user_id,
            version=new_version,
            interests=persona_data.get("interests", []),
            values=persona_data.get("values", []),
            goals=persona_data.get("goals", []),
            speech_style=persona_data.get("speech_style", []),
            thinking_style=persona_data.get("thinking_style", ""),
            summary=f"基于 {len(semantic_memories)} 条长期记忆构建 (v{new_version})",
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return {
            "status": "success",
            "version": new_version,
            "profile_id": profile.id,
            "persona": persona_data,
        }

    async def get_persona(self, user_id: int) -> Optional[Dict[str, Any]]:
        profile = (
            self.db.query(PersonaProfile)
            .filter(PersonaProfile.user_id == user_id)
            .order_by(PersonaProfile.version.desc())
            .first()
        )
        if not profile:
            return None
        return {
            "id": profile.id,
            "version": profile.version,
            "interests": profile.interests or [],
            "values": profile.values or [],
            "goals": profile.goals or [],
            "speech_style": profile.speech_style or [],
            "thinking_style": profile.thinking_style,
            "summary": profile.summary,
            "created_at": str(profile.created_at),
        }

    async def analyze_values(self, user_id: int) -> List[str]:
        memories = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.importance.desc())
            .limit(50)
            .all()
        )
        if not memories:
            return []

        combined = "\n".join([m.content for m in memories])
        llm = get_llm_client()
        try:
            import json
            response = await llm.simple_chat(combined, "从以下内容中提取用户的核心价值观，返回JSON数组格式。")
            return json.loads(response)
        except Exception:
            return []

    async def analyze_decision_patterns(self, user_id: int) -> Dict[str, Any]:
        memories = (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(Memory.importance.desc())
            .limit(50)
            .all()
        )
        if not memories:
            return {}

        combined = "\n".join([m.content for m in memories])
        llm = get_llm_client()
        try:
            import json
            response = await llm.simple_chat(combined, "分析以下内容中的决策模式，返回JSON格式。")
            return json.loads(response)
        except Exception:
            return {}
