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
from flask import current_app, Blueprint, send_from_directory, render_template_string, abort

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
    theme_path = os.path.join(current_app.root_path, "styles", theme["template_path"])
    default_path = os.path.join(current_app.root_path, "templates")

    loaders = [
        jinja2.FileSystemLoader(theme_path),
        jinja2.FileSystemLoader(default_path),
        #current_app.jinja_loader,  # fallback to app/templates/
        ]

    if not os.path.exists(theme_path):
        log.warning("Theme '%s' templates missing — falling back only", theme)

    return jinja2.ChoiceLoader(loaders)


theme_static_bp = Blueprint(
    "theme_static",
    __name__,
    url_prefix="/theme_static"
)

@theme_static_bp.route("/<path:filename>")
def serve_static(filename):
    style_config = get_config('style_config')
    folder = os.path.join(current_app.root_path, "styles", style_config["static_path"])

    if not os.path.exists(folder):
        log.warning("Theme '%s' static folder missing — serving empty", style_config["static_path"])
        # Return empty dir fallback to avoid Flask errors
        folder = os.path.join(current_app.instance_path, "empty_static")
        os.makedirs(folder, exist_ok=True)

    if filename.lower().endswith('.css'):
        file_path = os.path.abspath(os.path.join(folder,filename))
        if not file_path.startswith(os.path.abspath(folder)):
            abort(404)
        if not os.path.isfile(file_path):
            abort(404)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            rendered_template = render_template_string(
                template_content,
                style = style_config
            )
            response = current_app.response_class(
                rendered_template,
                mimetype="text/css"
            )
            # Optional: aggressive caching since content is deterministic per theme
            response.headers["Cache-Control"] = "public, max-age=3600"
            return response
        except Exception as e:
            log.error(f"Failed rendering dynamic css: {e}")
            abort(500)

    return send_from_directory(folder, filename)
