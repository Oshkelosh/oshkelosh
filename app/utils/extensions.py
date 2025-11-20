from app.logging import get_logger

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

from app.database import setupDB
from app.database import schema

from app.models import models

class DBClient:
    def init_app(self, app):
        logger.info("Setting up sql database . . .")
        setupDB(schema = schema.schema, db_path=app.DATABASE_URI)
    
    def set_defaults(self, default_list):
        logger.info("Setting Default to database . . ")
        success = models.set_defaults(default_list=default_list)
        if not success:
            logger.error("Failed to load defaults")
            raise ValueError("Failed to load defaults to database!")


db = DBClient()
