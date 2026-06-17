from __future__ import annotations

import math
import re
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings


class EmbeddingService(ABC):
    @abstractmethod
    async def embed(self, text: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def mode_name(self) -> str:
        pass

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


class LiteEmbeddingService(EmbeddingService):
    def is_available(self) -> bool:
        return True

    def mode_name(self) -> str:
        return "lite"

    async def embed(self, text: str) -> None:
        return None

    async def embed_batch(self, texts: List[str]) -> List[None]:
        return [None] * len(texts)


class OllamaEmbeddingService(EmbeddingService):
    def __init__(self):
        self._base_url = settings.OLLAMA_BASE_URL
        self._model = "bge-m3"
        self._available = False
        self._checked = False

    def mode_name(self) -> str:
        return "full"

    def is_available(self) -> bool:
        return self._available

    async def check_and_init(self) -> Dict[str, Any]:
        result = {"ollama_found": False, "model_found": False, "model_pulled": False, "error": None}

        try:
            proc = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode != 0:
                result["error"] = "Ollama not found"
                self._checked = True
                return result
            result["ollama_found"] = True
        except FileNotFoundError:
            result["error"] = (
                "Ollama not found.\n"
                "Please install Ollama first: https://ollama.com"
            )
            self._checked = True
            return result
        except Exception as exc:
            result["error"] = f"Ollama check failed: {exc}"
            self._checked = True
            return result

        try:
            proc = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10,
            )
            if self._model in proc.stdout:
                result["model_found"] = True
            else:
                print(f"First startup: Downloading embedding model {self._model}...")
                pull_proc = subprocess.run(
                    ["ollama", "pull", self._model],
                    capture_output=True, text=True, timeout=600,
                )
                if pull_proc.returncode == 0:
                    result["model_found"] = True
                    result["model_pulled"] = True
                    print(f"Download complete.")
                else:
                    result["error"] = f"Failed to pull {self._model}: {pull_proc.stderr}"
                    self._checked = True
                    return result
        except Exception as exc:
            result["error"] = f"Model check failed: {exc}"
            self._checked = True
            return result

        try:
            test = await self.embed("test")
            if test and len(test) > 0:
                self._available = True
            else:
                result["error"] = "Embedding test returned empty"
        except Exception as exc:
            result["error"] = f"Embedding test failed: {exc}"

        self._checked = True
        return result

    async def embed(self, text: str) -> Optional[List[float]]:
        if not self._available:
            return None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text[:8000]},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")
        except Exception as exc:
            print(f"Ollama embed failed: {exc}")
            return None

    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        results = []
        for text in texts:
            result = await self.embed(text)
            results.append(result)
        return results


def hashed_embedding(text: str, dimensions: int = 1024) -> List[float]:
    import jieba
    stopwords = {
        "的", "了", "和", "是", "在", "我", "你", "他", "她", "它",
        "我们", "你们", "他们", "一个", "这个", "那个", "以及", "或者",
        "但是", "然后", "因为", "所以", "the", "and", "or", "to", "of", "in", "a",
    }
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    tokens = []
    for token in jieba.lcut(normalized):
        token = token.strip()
        if len(token) >= 2 and token not in stopwords:
            tokens.append(token)
    vector = [0.0] * dimensions
    for token in tokens:
        index = hash(token) % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        if settings.EMBEDDING_MODE == "full":
            _embedding_service = OllamaEmbeddingService()
        else:
            _embedding_service = LiteEmbeddingService()
    return _embedding_service


async def check_and_init_embedding() -> Dict[str, Any]:
    svc = get_embedding_service()
    if isinstance(svc, OllamaEmbeddingService):
        result = await svc.check_and_init()
        if not svc.is_available():
            print(f"Full mode unavailable ({result.get('error')}). Falling back to Lite mode.")
            global _embedding_service
            _embedding_service = LiteEmbeddingService()
            result["fallback"] = True
        else:
            print("Embedding runtime ready (Full mode: Ollama + bge-m3)")
            result["fallback"] = False
        return result
    else:
        print("Embedding runtime ready (Lite mode: TF-IDF)")
        return {"mode": "lite", "available": True}
