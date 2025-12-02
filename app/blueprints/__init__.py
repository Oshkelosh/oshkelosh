"""
Central registry for all blueprints.
Import this from app/__init__.py → one function call registers everything.
"""
from flask import Flask
from app.utils.logging import get_logger

log = get_logger(__name__)

BLUEPRINTS = []

def register_blueprint(bp, *, url_prefix=None):
    """Helper used inside each blueprint's __init__.py"""
    BLUEPRINTS.append((bp, url_prefix))

def init_blueprints(app: Flask) -> None:
    """Call this once from the app factory"""
    for bp, prefix in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix=prefix)
        log.info("Blueprint registered: %s → %s", bp.name, prefix or "/")
    log.info("All %d blueprints registered", len(BLUEPRINTS))
