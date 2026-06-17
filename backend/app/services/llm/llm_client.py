import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

FAKE_KEYS = {
    "sk-abcdef1234567890xyz",
    "sk-1234567890abcdef",
    "your-api-key",
    "your-openai-api-key",
    "your-mimo-api-key",
    "your-deepseek-api-key",
}


def _is_real_key(key: Optional[str]) -> bool:
    if not key:
        return False
    if key in FAKE_KEYS:
        return False
    if key.startswith("your-"):
        return False
    return True


def _get_provider_config(provider: str) -> Dict[str, Any]:
    if provider == "mimo":
        return {
            "name": "MiMo",
            "api_base": settings.MIMO_API_BASE,
            "api_key": settings.MIMO_API_KEY,
            "model": settings.MIMO_MODEL,
            "header_key": "api-key",
        }
    elif provider == "deepseek":
        return {
            "name": "DeepSeek",
            "api_base": settings.DEEPSEEK_API_BASE,
            "api_key": settings.DEEPSEEK_API_KEY,
            "model": settings.DEEPSEEK_MODEL,
            "header_key": "Authorization",
        }
    elif provider == "openai":
        return {
            "name": "ChatGPT",
            "api_base": settings.OPENAI_API_BASE,
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL,
            "header_key": "Authorization",
        }
    elif provider == "custom":
        return {
            "name": "自定义",
            "api_base": settings.CUSTOM_API_BASE,
            "api_key": settings.CUSTOM_API_KEY,
            "model": settings.CUSTOM_MODEL,
            "header_key": "Authorization",
        }
    return {
        "name": provider,
        "api_base": settings.MIMO_API_BASE,
        "api_key": settings.MIMO_API_KEY,
        "model": settings.MIMO_MODEL,
        "header_key": "api-key",
    }


class LLMClient:
    def __init__(self, provider: str = None):
        self.provider = provider or settings.ACTIVE_PROVIDER
        self.config = _get_provider_config(self.provider)

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self.config["api_key"]
        if self.config["header_key"] == "api-key":
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: int = 1024,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        payload = {
            "messages": messages,
            "model": self.config["model"],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config['api_base']}/chat/completions",
                headers=self.get_headers(),
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


def get_llm_client(provider: str = None) -> LLMClient:
    return LLMClient(provider)


def get_available_providers() -> List[Dict[str, Any]]:
    providers = ["mimo", "deepseek", "openai", "custom"]
    result = []
    for key in providers:
        config = _get_provider_config(key)
        result.append({
            "id": key,
            "name": config["name"],
            "model": config["model"],
            "configured": _is_real_key(config["api_key"]),
            "active": key == settings.ACTIVE_PROVIDER,
        })
    return result
