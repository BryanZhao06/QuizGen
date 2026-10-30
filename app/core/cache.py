import hashlib
import json
import redis
from app.core.config import settings

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_cache_key(context: str, num_questions: int, topic: str) -> str:
    normalized = f"{topic}:{num_questions}:{context.strip().lower()}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"quiz_cache:{digest}"

def fetch_cached_quiz(context: str, num_questions: int, topic: str):
    try:
        key = get_cache_key(context, num_questions, topic)
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None

def set_cached_quiz(context: str, num_questions: int, topic: str, quiz_data: dict, ttl_seconds: int = 86400):
    try:
        key = get_cache_key(context, num_questions, topic)
        r.setex(key, ttl_seconds, json.dumps(quiz_data))
    except Exception:
        pass
