import os
from dotenv import load_dotenv
from pathlib import Path

from datetime import timedelta
from typing import Type

from flask import Flask

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
DEFAULT_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FILE = None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=f"{BASE_DIR}.env")


class Config:
    """Base configuration – never use directly."""
    SECRET_KEY: str | None = os.getenv("APP_SECRET", "")

    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False   # overridden in prod
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    LOG_FORMAT = os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT)
    LOG_DATEFMT = os.getenv("LOG_DATEFMT", DEFAULT_LOG_DATEFMT)
    LOG_FILE = os.getenv("LOG_FILE", DEFAULT_LOG_FILE)

    ACTIVE_THEME = os.getenv("ACTIVE_THEME", "default")

    DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'database.db')}"
    )

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @staticmethod
    def init_app(app: Flask) -> None:
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 5000

    @staticmethod
    def init_app(app: Flask) -> None:
        print("→ Development mode active")
        # Helpful warning only in dev
        if len(app.secret_key or "") < 32:  # type: ignore
            print(
                "\033[93mWARNING: SECRET_KEY is weak or missing. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'\033[0m"
            )


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", 5000))

    @staticmethod
    def init_app(app: Flask) -> None:
        # Fail fast if secret is garbage – no silent insecurity in prod
        if not app.secret_key or len(app.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be a strong 32+ byte value in production. "
                "Set it in .env or environment variables."
            )


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    DATABASE_URI = "sqlite:///:memory:"  # in-memory for speed
    SERVER_NAME = "localhost.localdomain"  # allows url_for in tests


config_by_name: dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
