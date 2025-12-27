"""
Central registry for all blueprints.
Import this from app/__init__.py → one function call registers everything.
"""
from flask import Flask, Blueprint
from app.utils.logging import get_logger
from typing import List, Tuple, Optional

log = get_logger(__name__)

BLUEPRINTS: List[Tuple[Blueprint, Optional[str]]] = []


def register_blueprint(bp: Blueprint, *, url_prefix: Optional[str] = None) -> None:
    """Helper used inside each blueprint's __init__.py"""
    BLUEPRINTS.append((bp, url_prefix))

def init_blueprints(app: Flask) -> None:
    """Call this once from the app factory"""
    for bp, prefix in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix=prefix)
        log.info("Blueprint registered: %s → %s", bp.name, prefix or "/")
    log.info("All %d blueprints registered", len(BLUEPRINTS))

from .admin import *
from .main import *
from .user import *
