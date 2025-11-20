from flask import current_app
import json, os


def template_route(file_name=None):
    """Returns path to templates folder for the current style, or file path for given 'file_name' in templates folder"""
    site_config = json.loads(current_app.redis.get("site_config"))
    style_config = json.loads(current_app.redis.get(f"{site_config['style']}_style"))
    path = os.path.join(
        site_config["style"],
        style_config["template_path"],
        file_name if file_name else "",
    )
    return path


def static_route(file_name=None):
    """Returns path to static folder for the current theme, or file path for given 'file_name' in static folder"""
    site_config = json.loads(current_app.redis.get("site_config"))
    style_config = json.loads(current_app.redis.get("style_config"))
    path = os.path.join(
        "addons",
        "style",
        site_config["style"],
        style_config["static_path"],
        file_name if file_name else "",
    )
    return path

