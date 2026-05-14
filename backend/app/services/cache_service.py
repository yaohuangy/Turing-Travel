import json
import logging
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as e:
        logger.warning("Redis unavailable, caching disabled: %s", e)
        _redis_client = None
    return _redis_client


def get(key: str) -> Optional[dict]:
    r = _get_redis()
    if r is None:
        return None
    try:
        data = r.get(key)
        if data:
            logger.info("Cache HIT: %s", key)
            return json.loads(data)
        logger.info("Cache MISS: %s", key)
        return None
    except Exception as e:
        logger.warning("Redis get error for key=%s: %s", key, e)
        return None


def set(key: str, value: dict, ttl: int = 3600) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        logger.info("Cache SET: %s (TTL=%ds)", key, ttl)
    except Exception as e:
        logger.warning("Redis set error for key=%s: %s", key, e)
