from app.utils.logging import get_logger

from flask import Flask
from flask_login import LoginManager
import redis
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis import Redis

logger = get_logger(__name__)

login_manager = LoginManager()

class RedisClient:
    def __init__(self) -> None:
        self._client: "Redis[str] | None" = None

    def init_app(self, app: Flask) -> None:
        url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self._client = redis.from_url(url)
        app.extensions['redis'] = self

    @property
    def client(self) -> "Redis[str]":
        if self._client is None:
            raise RuntimeError("Redis not initialized")
        return self._client

redis_client = RedisClient()




