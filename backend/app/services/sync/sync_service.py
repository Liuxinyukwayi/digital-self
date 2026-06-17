from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import DataSource, MemoryType
from app.services.llm.llm_client import get_llm_client
from app.services.lightrag.lightrag_service import get_lightrag_service
from app.services.memory.memory_service import MemoryService


CLASSIFY_PROMPT = """分析以下聊天内容，判断其类型，只返回类型名称（不要返回其他内容）：

fact - 客观事实陈述（工作、地点、时间等）
preference - 个人偏好（喜欢、讨厌、偏好）
opinion - 观点看法（认为、觉得、判断）
goal - 目标计划（想要、计划、目标）
relationship - 人物关系（提到某人及其关系）
episodic - 一般经历/日常对话

内容：
{content}

类型："""


SCORE_PROMPT = """评估以下内容的重要性（1-10分），只返回数字：
1-2 = 闲聊/表情
3-4 = 日常对话
5-6 = 有价值信息
7-8 = 重要事实/决策
9-10 = 人生转折点

内容：
{content}

分数："""


BATCH_CLASSIFY_PROMPT = """分析以下多段内容，为每段判断类型。返回JSON数组，每个元素是一个类型字符串。
可选类型：fact, preference, opinion, goal, relationship, episodic

内容列表：
{content_list}

返回JSON数组（只返回数组，不要其他内容）："""


BATCH_SCORE_PROMPT = """评估以下多段内容的重要性（每段1-10分）。返回JSON数组，每个元素是一个数字。
1-2=闲聊/表情 3-4=日常对话 5-6=有价值信息 7-8=重要事实/决策 9-10=人生转折点

内容列表：
{content_list}

返回JSON数组（只返回数组，不要其他内容）："""


MEMORY_TYPE_MAP = {
    "fact": MemoryType.FACT,
    "preference": MemoryType.PREFERENCE,
    "opinion": MemoryType.OPINION,
    "goal": MemoryType.GOAL,
    "relationship": MemoryType.RELATIONSHIP,
    "episodic": MemoryType.EPISODIC,
}


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.memory_service = MemoryService(db)

    async def import_messages(
        self,
        payload: bytes | str,
        user_id: int,
        source: DataSource,
        skip_classification: bool = False,
    ) -> Dict[str, Any]:
        text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else payload
        messages = self._parse_messages(text)
        chunks = self._group_into_chunks(messages)

        chunk_contents = []
        for chunk in chunks:
            combined_content = "\n".join(chunk["lines"])
            chunk_contents.append(combined_content)

        if skip_classification or not chunk_contents:
            types = [MemoryType.EPISODIC] * len(chunk_contents)
            scores = [4] * len(chunk_contents)
        else:
            types = await self._batch_classify(chunk_contents)
            scores = await self._batch_score(chunk_contents)

        imported = 0
        for i, chunk in enumerate(chunks):
            combined_content = chunk_contents[i]
            summary_lines = [line for line in chunk["lines"] if line.strip()][:3]
            summary = " | ".join(summary_lines)[:140]

            memory_type = types[i] if i < len(types) else MemoryType.EPISODIC
            importance = scores[i] if i < len(scores) else 4

            await self.memory_service.create_memory(
                content=combined_content,
                user_id=user_id,
                summary=summary,
                memory_type=memory_type,
                source=source,
                importance=importance,
                tags=[source.value, "chat-import", memory_type.value],
            )
            imported += 1

        return {"imported": imported, "source": source.value, "chunks": len(chunks)}

    async def _batch_classify(self, contents: List[str]) -> List[MemoryType]:
        if not contents:
            return []

        llm = get_llm_client()
        content_list = "\n---\n".join(f"[{i+1}] {c[:300]}" for i, c in enumerate(contents))

        try:
            response = await llm.simple_chat(
                BATCH_CLASSIFY_PROMPT.format(content_list=content_list),
                "你是一个内容分类助手，只返回JSON数组。",
            )
            parsed = self._parse_json_array(response)
            results = []
            for item in parsed:
                item_str = str(item).strip().lower()
                results.append(MEMORY_TYPE_MAP.get(item_str, MemoryType.EPISODIC))
            while len(results) < len(contents):
                results.append(MemoryType.EPISODIC)
            return results[:len(contents)]
        except Exception as exc:
            print(f"Batch classify failed, using episodic: {exc}")
            return [MemoryType.EPISODIC] * len(contents)

    async def _batch_score(self, contents: List[str]) -> List[int]:
        if not contents:
            return []

        llm = get_llm_client()
        content_list = "\n---\n".join(f"[{i+1}] {c[:300]}" for i, c in enumerate(contents))

        try:
            response = await llm.simple_chat(
                BATCH_SCORE_PROMPT.format(content_list=content_list),
                "你是一个内容评分助手，只返回JSON数组。",
            )
            parsed = self._parse_json_array(response)
            results = []
            for item in parsed:
                try:
                    score = max(1, min(10, int(float(str(item)))))
                except (ValueError, TypeError):
                    score = 4
                results.append(score)
            while len(results) < len(contents):
                results.append(4)
            return results[:len(contents)]
        except Exception as exc:
            print(f"Batch score failed, using default: {exc}")
            return [4] * len(contents)

    def _parse_json_array(self, text: str) -> list:
        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        match = re.search(r"\[.*?\]", cleaned, re.S)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []

    def _group_into_chunks(self, messages: List[Dict[str, Any]], gap_minutes: int = 3) -> List[Dict[str, Any]]:
        if not messages:
            return []

        chunks: List[Dict[str, Any]] = []
        current_chunk: Dict[str, Any] = {"lines": [], "first_time": None, "last_time": None}

        for message in messages:
            content = message.get("content", "").strip()
            if not content:
                continue

            ts = self._parse_timestamp(message.get("time") or message.get("timestamp"))
            sender = message.get("sender") or message.get("from") or message.get("role")
            line = f"{sender}: {content}" if sender else content
            if ts:
                line = f"[{ts.strftime('%m-%d %H:%M')}] {line}"

            if current_chunk["last_time"] and ts:
                gap = ts - current_chunk["last_time"]
                if gap > timedelta(minutes=gap_minutes):
                    chunks.append(current_chunk)
                    current_chunk = {"lines": [], "first_time": None, "last_time": None}

            if not current_chunk["first_time"]:
                current_chunk["first_time"] = ts
            current_chunk["last_time"] = ts or current_chunk["last_time"]
            current_chunk["lines"].append(line)

        if current_chunk["lines"]:
            chunks.append(current_chunk)

        return chunks

    def _parse_timestamp(self, value: Any) -> Any:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S", "%m-%d %H:%M"):
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        return None

    async def import_text_document(self, payload: bytes | str, user_id: int, source: DataSource) -> Dict[str, Any]:
        text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else payload
        if not text.strip():
            return {"imported": 0, "source": source.value}

        lightrag = get_lightrag_service()
        if lightrag.enabled and source not in (DataSource.WECHAT, DataSource.QQ):
            result = await lightrag.insert_document(text.strip(), {"source": source.value})
            if result.get("status") == "success":
                return {"imported": 1, "source": source.value, "storage": "lightrag"}
            return {"imported": 0, "source": source.value, "error": result.get("reason", "LightRAG insert failed")}

        llm = get_llm_client()
        try:
            response = await llm.simple_chat(
                CLASSIFY_PROMPT.format(content=text[:500]),
                "你是一个内容分类助手，只返回类型名称。",
            )
            type_str = response.strip().lower()
            memory_type = MEMORY_TYPE_MAP.get(type_str, MemoryType.KNOWLEDGE)
        except Exception:
            memory_type = MemoryType.KNOWLEDGE

        try:
            response = await llm.simple_chat(
                SCORE_PROMPT.format(content=text[:500]),
                "你是一个内容评分助手，只返回数字。",
            )
            importance = max(1, min(10, int(float(response.strip()))))
        except Exception:
            importance = 5

        await self.memory_service.create_memory(
            content=text.strip(),
            user_id=user_id,
            summary=text.strip()[:140],
            memory_type=memory_type,
            source=source,
            importance=importance,
            tags=[source.value, "sync-import", memory_type.value],
        )
        return {"imported": 1, "source": source.value, "storage": "memory"}

    async def import_wechat(self, file_path: str, user_id: int) -> Dict[str, Any]:
        return await self._import_chat_file(file_path, user_id, DataSource.WECHAT)

    async def import_qq(self, file_path: str, user_id: int) -> Dict[str, Any]:
        return await self._import_chat_file(file_path, user_id, DataSource.QQ)

    async def import_feishu(self, file_path: str, user_id: int) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        return await self.import_text_document(path.read_text(encoding="utf-8"), user_id, DataSource.FEISHU)

    async def import_github(self, file_path: str, user_id: int) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        return await self.import_text_document(path.read_text(encoding="utf-8"), user_id, DataSource.GITHUB)

    async def get_sync_status(self) -> List[Dict[str, Any]]:
        return [
            {"source": source.value, "status": "ready", "last_sync": None, "items_synced": 0}
            for source in DataSource
            if source is not DataSource.MANUAL
        ]

    async def _import_chat_file(self, file_path: str, user_id: int, source: DataSource) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        return await self.import_messages(path.read_bytes(), user_id, source)

    def _parse_messages(self, text: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                for key in ("messages", "records", "data", "items"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return [item for item in value if isinstance(item, dict)]
                if "content" in data:
                    return [data]
        except json.JSONDecodeError:
            pass

        messages = []
        jsonl_count = 0
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "content" in obj:
                    content = obj.get("content", "").strip()
                    if not content or content.startswith("[图片:") or content.startswith("[视频:") or content.startswith("[音频:"):
                        continue
                    message: Dict[str, Any] = {"content": content}
                    if obj.get("time"):
                        message["time"] = obj["time"]
                    elif obj.get("timestamp"):
                        message["timestamp"] = obj["timestamp"]
                    if obj.get("sender") or obj.get("from") or obj.get("nickname"):
                        message["sender"] = obj.get("sender") or obj.get("from") or obj.get("nickname")
                    messages.append(message)
                    jsonl_count += 1
                    continue
            except json.JSONDecodeError:
                pass
            messages.append({"content": line})

        if jsonl_count > 0:
            return messages

        return messages if messages else []
