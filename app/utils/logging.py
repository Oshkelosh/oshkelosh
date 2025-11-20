"""
Centralized, idempotent logging configuration.
Import anywhere — configures only once.
"""
import logging
import logging.handlers
import os
from typing import Optional

from flask import current_app, has_app_context
from .config import DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATEFMT


_configured = False


def setup_logging(app=None) -> None:
    """
    Configure root + Flask app logger.
    Safe to call multiple times (e.g. in tests).
    """
    global _configured
    if _configured:
        return

    if app is None:
        app = current_app  

    if app is None:
        logging.basicConfig(level=logging.INFO, format=DEFAULT_LOG_FORMAT)
        _configured = True
        return

    if app.debug:
        level = logging.DEBUG
    else:
        level_name = app.config.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
        level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        app.config.get("LOG_FORMAT", DEFAULT_LOG_FORMAT),
        datefmt=app.config.get("LOG_DATEFMT", DEFAULT_LOG_DATEFMT),
    )

    root = logging.getLogger()
    root.handlers.clear()     
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    console.addFilter(UTF8Filter())
    root.addHandler(console)

    log_file = app.config.get("LOG_FILE")
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,   # 10 MB
                backupCount=7,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
            app.logger.info(f"File logging → {log_file}")
        except Exception as exc:  # Never crash on logging failure
            app.logger.warning(f"Failed to initialize file logging ({log_file}): {exc}")

    app.logger.propagate = False
    app.logger.handlers = root.handlers[:]
    app.logger.setLevel(level)

    app.logger.info(f"Logging initialized — level={logging.getLevelName(level)}")
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Preferred way: logger = get_logger(__name__)
    Hierarchically named, automatically uses app.logger as parent when available.
    """
    if has_app_context() and current_app:
        base = current_app.logger
    else:
        base = logging.getLogger()

    if not name or name == "__main__":
        return base

    return base.getChild(name.split(".")[-1] if "." in name else name)


class UTF8Filter(logging.Filter):
    """Prevent console crashes on broken Unicode (rare but happens with POD webhooks)."""
    def filter(self, record):
        if isinstance(record.msg, bytes):
            record.msg = record.msg.decode("utf-8", errors="replace")
        return True
