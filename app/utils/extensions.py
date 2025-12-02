from app.utils.logging import get_logger

from flask_login import LoginManager
import redis

logger = get_logger(__name__)

login_manager = LoginManager()

class RedisClient:
    def __init__(self):
        self._client = None

    def init_app(self, app):
        url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self._client = redis.from_url(url)
        app.extensions['redis'] = self  # For easy access if needed

    @property
    def client(self):
        if self._client is None:
            raise RuntimeError("Redis not initialized")
        return self._client

redis_client = RedisClient()




