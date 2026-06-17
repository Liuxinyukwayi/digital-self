from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

import jieba


STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它",
    "我们", "你们", "他们", "一个", "这个", "那个", "以及", "或者",
    "但是", "然后", "因为", "所以", "the", "and", "or", "to", "of", "in", "a",
}


def normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def tokenize(text: str | None) -> List[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    words = []
    for token in jieba.lcut(normalized):
        token = token.strip()
        if len(token) < 2 or token in STOPWORDS:
            continue
        words.append(token)

    ascii_terms = re.findall(r"[a-z0-9_\-]{2,}", normalized)
    chinese_bigrams = re.findall(r"[\u4e00-\u9fff]{2}", normalized)
    return words + ascii_terms + chinese_bigrams


def chunk_text(text: str | None, chunk_size: int = 900, overlap: int = 140) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs or [text]:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, chunk_size - overlap)
            for start in range(0, len(paragraph), step):
                part = paragraph[start : start + chunk_size].strip()
                if part:
                    chunks.append(part)
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)
    return chunks


def _tfidf_vector(tokens: Iterable[str], idf: Dict[str, float]) -> Dict[str, float]:
    counts = Counter(tokens)
    if not counts:
        return {}
    total = sum(counts.values())
    return {term: (count / total) * idf.get(term, 1.0) for term, count in counts.items()}


def _cosine(left: Dict[str, float], right: Dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(term, 0.0) for term, weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def rank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    *,
    text_key: str = "content",
    title_key: str | None = "title",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    query_tokens = tokenize(query)
    if not query_tokens or not documents:
        return []

    prepared = []
    doc_frequency: Counter[str] = Counter()
    for document in documents:
        title = str(document.get(title_key, "")) if title_key else ""
        text = str(document.get(text_key, ""))
        tokens = tokenize(f"{title} {title} {text}")
        token_set = set(tokens)
        doc_frequency.update(token_set)
        prepared.append((document, tokens, token_set, normalize_text(f"{title} {text}")))

    total_docs = len(prepared)
    idf = {
        term: math.log((1 + total_docs) / (1 + frequency)) + 1
        for term, frequency in doc_frequency.items()
    }

    query_vector = _tfidf_vector(query_tokens, idf)
    query_set = set(query_tokens)
    normalized_query = normalize_text(query)

    ranked = []
    for document, tokens, token_set, normalized_text in prepared:
        doc_vector = _tfidf_vector(tokens, idf)
        cosine = _cosine(query_vector, doc_vector)
        overlap = len(query_set & token_set) / max(1, len(query_set))
        phrase_boost = 0.15 if normalized_query and normalized_query in normalized_text else 0.0
        importance = float(document.get("importance", 5) or 5) / 10.0
        score = (0.68 * cosine) + (0.22 * overlap) + phrase_boost + (0.04 * importance)

        if score > 0:
            item = dict(document)
            item["score"] = round(min(score, 1.0), 4)
            item["matched_terms"] = sorted(query_set & token_set)[:12]
            ranked.append(item)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


async def get_embedding(text: str) -> Optional[List[float]]:
    from app.services.embedding.embedding_service import get_embedding_service
    svc = get_embedding_service()
    return await svc.embed(text)


async def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    from app.services.embedding.embedding_service import get_embedding_service
    svc = get_embedding_service()
    return await svc.embed_batch(texts)
