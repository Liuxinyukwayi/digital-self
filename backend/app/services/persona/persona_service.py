from typing import Dict, List, Any, Optional
import json
import re
from collections import Counter
from app.services.llm.llm_client import get_llm_client
from app.services.rag.text_index import tokenize


class PersonaService:
    async def generate_persona_from_chat(self, chat_records: List[Dict]) -> Dict[str, Any]:
        system_prompt = """你是一个人格分析专家。基于提供的聊天记录，分析并生成该用户的人格特征。

请返回JSON格式：
{
    "name": "用户名称",
    "traits": ["特征1", "特征2", ...],
    "speaking_style": ["说话风格1", "说话风格2", ...],
    "interests": ["兴趣1", "兴趣2", ...],
    "values": ["价值观1", "价值观2", ...],
    "summary": "简短的人格总结"
}"""

        chat_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_records[:100]])
        user_prompt = f"请分析以下聊天记录并生成人格特征：\n\n{chat_text}"

        try:
            llm = get_llm_client()
            response = await llm.simple_chat(user_prompt, system_prompt)
            return self._loads_json(response)
        except Exception as e:
            return self._fallback_persona(chat_records, str(e))

    async def analyze_personality(self, texts: List[str]) -> Dict[str, Any]:
        system_prompt = """分析以下文本中的人格特征，返回JSON格式：
{
    "traits": ["特征1", "特征2"],
    "communication_style": "沟通风格描述",
    "emotional_patterns": ["情绪模式1", "情绪模式2"]
}"""

        combined_text = "\n".join(texts[:50])
        user_prompt = f"请分析以下文本的人格特征：\n\n{combined_text}"

        try:
            llm = get_llm_client()
            response = await llm.simple_chat(user_prompt, system_prompt)
            return self._loads_json(response)
        except Exception:
            common = self._common_terms(texts)
            return {
                "traits": ["信息密度较高" if common else "待补充"],
                "communication_style": "基于本地文本粗略分析，偏直接表达。",
                "emotional_patterns": [],
                "keywords": common,
            }

    async def extract_values(self, texts: List[str]) -> List[str]:
        system_prompt = "从文本中提取用户的核心价值观，返回JSON数组格式。"

        combined_text = "\n".join(texts[:50])
        user_prompt = f"请提取以下文本中的价值观：\n\n{combined_text}"

        try:
            llm = get_llm_client()
            response = await llm.simple_chat(user_prompt, system_prompt)
            return self._loads_json(response)
        except Exception:
            return self._common_terms(texts, 6)

    async def extract_interests(self, texts: List[str]) -> List[str]:
        system_prompt = "从文本中提取用户的兴趣爱好，返回JSON数组格式。"

        combined_text = "\n".join(texts[:50])
        user_prompt = f"请提取以下文本中的兴趣爱好：\n\n{combined_text}"

        try:
            llm = get_llm_client()
            response = await llm.simple_chat(user_prompt, system_prompt)
            return self._loads_json(response)
        except Exception:
            return self._common_terms(texts, 8)

    async def update_persona(self, persona_id: int, new_data: Dict) -> Dict:
        # TODO: 更新Persona
        return new_data

    def _loads_json(self, text: str) -> Any:
        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
        if fenced:
            cleaned = fenced.group(1).strip()
        return json.loads(cleaned)

    def _common_terms(self, texts: List[str], limit: int = 10) -> List[str]:
        counter = Counter()
        for text in texts:
            counter.update(tokenize(text))
        return [term for term, _ in counter.most_common(limit)]

    def _fallback_persona(self, chat_records: List[Dict], reason: str) -> Dict[str, Any]:
        texts = [record.get("content", "") for record in chat_records]
        keywords = self._common_terms(texts, 12)
        return {
            "name": "用户",
            "traits": ["重视经验积累", "关注细节", "愿意持续迭代"] if keywords else ["待补充"],
            "speaking_style": ["直接", "上下文驱动", "偏任务导向"],
            "interests": keywords[:6],
            "values": keywords[6:10],
            "summary": f"已根据本地记录生成基础 Persona。AI 精细分析暂不可用：{reason}",
            "metadata": {"mode": "local_fallback", "keywords": keywords},
        }
