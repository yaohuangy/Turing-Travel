"""RAG retriever: query rewrite, vector search, rerank, and caching."""
import hashlib
import logging

import dashscope
from dashscope import Generation, TextReRank

from app.config import settings
from app.services import cache_service
from rag import vector_db

logger = logging.getLogger(__name__)

RERANK_MODEL = "qwen3-rerank"
RERANK_TOP_N = 3
RAG_CACHE_TTL = 3600  # 1 hour

REWRITE_SYSTEM_PROMPT = """你是一个搜索查询改写专家。将用户的旅行需求改写为适合向量检索的简短查询。

规则：
1. 查询应包含目的地和关键偏好词汇
2. 长度控制在20字以内
3. 只输出改写后的查询，不要任何解释

示例：
用户：我想去杭州玩，喜欢自然风光和美食
输出：杭州 自然风光 美食攻略

用户：成都亲子游，带孩子看熊猫
输出：成都 亲子 大熊猫 景点"""


def _llm_rewrite(user_query: str, city: str) -> str:
    """Use LLM few-shot to rewrite query."""
    try:
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        resp = Generation.call(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            result_format="message",
            max_tokens=50,
        )
        if resp.status_code == 200:
            rewritten = resp.output.choices[0].message.content.strip()
            logger.info("LLM rewrite: '%s' -> '%s'", user_query[:60], rewritten)
            return rewritten
        else:
            raise RuntimeError(f"Rewrite API error: {resp.status_code}")
    except Exception as e:
        logger.warning("LLM rewrite failed: %s, using rule-based fallback", e)
        return _rule_rewrite(user_query, city)


def _rule_rewrite(user_query: str, city: str) -> str:
    """Rule-based query rewrite as fallback."""
    prefs = ["美食", "自然", "历史", "文化", "亲子", "休闲", "户外"]
    keywords = [city]
    for p in prefs:
        if p in user_query:
            keywords.append(p)
    keywords.append("攻略")
    result = " ".join(keywords)
    logger.info("Rule rewrite: '%s' -> '%s'", user_query[:60], result)
    return result


def rewrite_query(user_query: str, city: str) -> str:
    """Rewrite user query for better retrieval. Primary: LLM, fallback: rule."""
    try:
        return _llm_rewrite(user_query, city)
    except Exception as e:
        logger.error("Query rewrite failed: %s", e)
        return _rule_rewrite(user_query, city)


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Rerank candidate chunks using qwen3-rerank cross-encoder."""
    if not candidates:
        return []
    try:
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        documents = [c["content"] for c in candidates]
        resp = TextReRank.call(
            model=RERANK_MODEL,
            query=query,
            documents=documents,
            top_n=min(RERANK_TOP_N, len(documents)),
            return_documents=False,
        )
        if resp.status_code != 200:
            logger.warning("Rerank API error: %s, returning original order", resp.message)
            return candidates[:RERANK_TOP_N]

        reranked = []
        for item in resp.output.results:
            idx = item["index"]
            if isinstance(idx, int) and idx < len(candidates):
                c = candidates[idx].copy()
                c["score"] = round(item["relevance_score"], 4)
                reranked.append(c)
        logger.info("Rerank: %d -> %d candidates", len(candidates), len(reranked))
        return reranked
    except Exception as e:
        logger.warning("Rerank failed: %s, returning top %d from vector search", e, min(RERANK_TOP_N, len(candidates)))
        return candidates[:RERANK_TOP_N]


def retrieve(query: str, city: str, top_k: int = 5, use_rerank: bool = True) -> list[dict]:
    """Retrieve relevant travel guide chunks.

    1. Rewrite query
    2. Check Redis cache
    3. Vector search with city filter
    4. Cross-encoder rerank (optional)
    5. Cache results
    """
    rewritten = rewrite_query(query, city)
    cache_key = f"rag:{hashlib.md5(rewritten.encode()).hexdigest()}:{city}"

    # Check cache
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("RAG cache HIT for query='%s', city='%s'", rewritten[:50], city)
        return cached

    # Vector search
    candidates = vector_db.search(rewritten, city, top_k=max(top_k, 10))
    if not candidates:
        return []

    # Rerank
    if use_rerank and len(candidates) > 1:
        results = _rerank(rewritten, candidates)
    else:
        results = candidates[:top_k]

    # Cache results
    cache_service.set(cache_key, results, ttl=RAG_CACHE_TTL)
    return results
