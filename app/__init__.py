import os
from typing import Optional

from flask import Flask, Blueprint,  send_from_directory

from dotenv import load_dotenv

from .config import config_by_name
from .utils.logging import setup_logging
from .utils.extensions import login_manager, redis_client
from .database import db
from .styles import get_theme_loader
from pathlib import Path

load_dotenv()

def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory.
    Keeps startup side-effects isolated and testable.
    """
    config_name = config_name or os.getenv("FLASK_ENV", "default")
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="static",
        template_folder="templates",
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
    
    # ------------------------------------------------------------------
    # SQLAlchemy Database
    # ------------------------------------------------------------------
    db.init_app(app)
    
    with app.app_context():
        # ------------------------------------------------------------------
        # Database & defaults
        # ------------------------------------------------------------------
        # Create SQLAlchemy tables from models
        db.create_all()
        
        from app.models import models
        from app.database import default_list
        models.set_defaults(default_list = default_list)

        # ------------------------------------------------------------------
        # Cache site config in Redis
        # ------------------------------------------------------------------
        from app.utils.site_config import cache_config
        cache_config()

        # ------------------------------------------------------------------
        # Theme / Template / Static resolution
        # ------------------------------------------------------------------
        @app.before_request
        def dynamic_style() -> None:
            app.jinja_loader = get_theme_loader()
        
        from .styles import theme_static_bp

        app.register_blueprint(theme_static_bp)

        from .blueprints import init_blueprints
        init_blueprints(app)
        from .utils.error_handlers import register_error_handlers
        register_error_handlers(app)

        @login_manager.user_loader
        def load_user(user_id: int) -> models.User | None:
            return models.User.query.get(int(user_id))
    
        app.logger.info("Oshkelosh %s server ready (theme: %s)", config_name, app.config.get("ACTIVE_THEME", 'basic'))

    return app


