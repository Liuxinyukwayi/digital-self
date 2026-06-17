import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings


class MIMOClient:
    def __init__(self):
        self.api_base = settings.MIMO_API_BASE
        self.api_key = settings.MIMO_API_KEY
        self.model = settings.MIMO_MODEL

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: int = 1024,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "messages": messages,
            "model": self.model,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    async def simple_chat(self, user_message: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        result = await self.chat_completion(messages)
        return result["choices"][0]["message"]["content"]

    async def chat_with_history(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        system_prompt: str = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        result = await self.chat_completion(messages)
        return result["choices"][0]["message"]["content"]


mimo_client = MIMOClient()