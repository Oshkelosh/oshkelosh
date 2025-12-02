"""
Modular theme system.
- Templates: theme → app fallback
- Static: served from /static-<theme_name>/
- Theme selected via config → Redis → DB → "default"
Zero Flask hacks, fully typed, works in tests.
"""
import os
from typing import Tuple

import jinja2
from flask import current_app
from app.utils.site_config import get_config
from app.utils.logging import get_logger

log = get_logger(__name__)

def get_theme_loader() -> jinja2.ChoiceLoader:
    """
    ChoiceLoader chain:
    - Active theme templates
    - App's own templates/ (for shared admin/error pages)
    """
    theme = get_config("style_config")
    theme_path = os.path.join(current_app.root_path, "themes", theme["template_path"])

    loaders = [
        jinja2.FileSystemLoader(theme_path),
        current_app.create_jinja_loader(),  # fallback to app/templates/
    ]

    if not os.path.exists(theme_path):
        log.warning("Theme '%s' templates missing — falling back only", theme)

    return jinja2.ChoiceLoader(loaders)


def get_theme_static() -> Tuple[str, str]:
    """
    Returns (static_folder_path, url_path)
    e.g. ("/app/themes/dark/static", "/static-dark")
    """
    theme = get_config("style_config")
    folder = os.path.join(current_app.root_path, "themes", theme["static_path"])
    url_path = f"/static-{theme["style_name"]}-{theme["theme_name"]}"

    if not os.path.exists(folder):
        log.warning("Theme '%s' static folder missing — serving empty", theme)
        # Return empty dir fallback to avoid Flask errors
        empty = os.path.join(current_app.instance_path, "empty_static")
        os.makedirs(empty, exist_ok=True)
        return empty, url_path

    return folder, url_path
