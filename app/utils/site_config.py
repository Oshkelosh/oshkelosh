"""
Fast, non-DB site configuration cache.
Used heavily on every request (theme, store name, tax rates, feature flags, etc.).
"""
import json
from typing import Any, Dict

from flask import current_app
from .extensions import redis_client
from .logging import get_logger

log = get_logger(__name__)

CONFIG_PREFIX = "oshkelosh:config:"

def cache_config() -> None:
    """
    One-time (per startup or admin change) push of all site config to Redis.
    Safe to call multiple times — overwrites existing keys.
    """
    from app.models import models  # late import — avoids circular dependency

    configs = models.set_configs()  # ← you already have something like this
    if not configs:
        log.warning("No site configs found in DB — Redis cache will be empty")
        return

    pipe = redis_client.client.pipeline()
    for key, config in configs:
        key = f"{CONFIG_PREFIX}{key}"
        value = json.dumps(config.data())  
        pipe.set(key, value)
    pipe.execute()
    log.info("Site config cached to Redis (%d keys)", len(configs))


def get_config(key: str, default: Any = None) -> Any:
    """
    Fast read path — used in templates, helpers, middleware, etc.
    Falls back to DB only on Redis miss (very rare after startup).
    """
    redis_key = f"{CONFIG_PREFIX}{key}"
    raw = redis_client.client.get(redis_key)

    if raw is not None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Corrupted Redis config key %s — falling back to DB", key)

    from app.models import models
    configs = models.set_configs()
    config = configs[key]
    if config is not None:
        data = config.data()
        redis_client.client.set(redis_key, json.dumps(data))
        return data

    return default


def invalidate_config_cache(key: str | None = None) -> None:
    """
    Call from admin routes after config changes.
    """
    if key:
        redis_client.client.delete(f"{CONFIG_PREFIX}{key}")
        log.info("Invalidated Redis config key: %s", key)
        return
    
        # Delete all — cheap pattern match
    keys = redis_client.client.keys(f"{CONFIG_PREFIX}*")
    if keys:
        str_keys = [k.decode() if isinstance(k, bytes) else k for k in keys]
        count = redis_client.client.delete(*str_keys)
        log.info("Invalidated all site config cache (%d keys)", count)
