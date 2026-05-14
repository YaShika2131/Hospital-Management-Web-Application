"""Redis caching utilities"""
import redis
from functools import wraps
import json
from flask import jsonify, has_request_context, request
from backend.config.config import Config

redis_client = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)


def _payload_to_cache(result):
    """Extract JSON-serializable data from a Flask view return value."""
    if isinstance(result, (dict, list)):
        return result
    if isinstance(result, tuple) and result:
        rv = result[0]
        if hasattr(rv, "get_json"):
            data = rv.get_json(silent=True)
            if isinstance(data, (dict, list)):
                return data
    return None


def cache_result(expiry=300):
    """
    Decorator to cache function results in Redis
    
    Args:
        expiry: Cache expiry time in seconds (default: 5 minutes)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            path_key = ""
            if has_request_context():
                path_key = request.full_path or request.path
            cache_key = f"{f.__name__}:{path_key}:{str(args)}:{str(kwargs)}"

            cached_value = redis_client.get(cache_key)
            if cached_value:
                try:
                    data = json.loads(cached_value)
                    return jsonify(data), 200
                except json.JSONDecodeError:
                    redis_client.delete(cache_key)

            result = f(*args, **kwargs)
            payload = _payload_to_cache(result)
            if payload is not None:
                try:
                    redis_client.setex(cache_key, expiry, json.dumps(payload))
                except (TypeError, ValueError):
                    pass

            return result
        return decorated_function
    return decorator

def invalidate_cache(pattern):
    """Invalidate cache entries matching pattern"""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)

def clear_cache():
    """Clear all cache"""
    redis_client.flushdb()

