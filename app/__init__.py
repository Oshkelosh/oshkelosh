import os
from typing import Optional

from flask import Flask
from dotenv import load_dotenv

from .config import config_by_name
from .utils.logging import setup_logging
from .utils.extensions import login_manager, redis_client
from .database import DBClient
from .styles import get_theme_loader, get_theme_static
from .models import models  
from .blueprints import init_blueprints
from .utils.error_handlers import register_error_handlers

load_dotenv()  
db = DBClient()

def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory.
    Keeps startup side-effects isolated and testable.
    """
    config_name = config_name or os.getenv("FLASK_ENV", "default")
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=None,
        template_folder=None,
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config.from_object(config_by_name[config_name])
    config_by_name[config_name].init_app(app)
    app.config.from_envvar("OSHKELOSH_SETTINGS", silent=True)  
    
    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    setup_logging(app)

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    login_manager.init_app(app)
    login_manager.login_view = "user.login"
    login_manager.login_message_category = "warning"
    
    redis_client.init_app(app)
    
    with app.app_context():
        # ------------------------------------------------------------------
        # Database & defaults
        # ------------------------------------------------------------------
        from .database.schema import schema
        db.init_app(app, schema)
        from .database import default_list
        models.set_defaults(default_list = default_list)

        # Cache site config in Redis
        from .utils.site_config import cache_config
        cache_config()

        # ------------------------------------------------------------------
        # Blueprints & error handlers
        # ------------------------------------------------------------------
        init_blueprints(app)
        register_error_handlers(app)

        #-------------------------------------------------------------------
        # User Loader
        #-------------------------------------------------------------------
        @login_manager.user_loader
        def load_user(user_id: int):
            return models.User.get(id=user_id)
    
        # ------------------------------------------------------------------
        # Theme / Template / Static resolution
        # ------------------------------------------------------------------
        theme_loader = get_theme_loader()
        theme_static_folder, theme_static_url = get_theme_static()

        app.jinja_loader = theme_loader
        app.static_folder = theme_static_folder
        app.static_url_path = theme_static_url

        app.logger.info("Oshkelosh %s server ready (theme: %s)", config_name, app.config.get("ACTIVE_THEME", 'basic'))

    return app


