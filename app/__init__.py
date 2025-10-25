from flask import Flask

# from flask_login import LoginManager
import jinja2
import redis

import os
from flask_config import flask_configs
from dotenv import dotenv_values
import json

from .database import migrations, schema, models

# login = LoginManager()


def create_app():
    env_config = dotenv_values(".env")
    if "FLASK_ENV" not in env_config:
        print(
            "Please set FLASK_ENV in the .env file. Possible environments: 'development', 'production', 'testing', 'default'"
        )
        return False

    app = Flask(__name__, static_folder=None, static_url_path=None)
    app.config.from_object(flask_configs[env_config["FLASK_ENV"]])
    flask_configs[env_config["FLASK_ENV"]].init_app(env_config["APP_SECRET"])

    print("Setting up Redis")
    app.redis = redis.Redis(host="localhost", port=6379, db=0)

    print("Setting up DB")
    migrations.setupDB(schema=schema.schema, db_path=schema.db_path)
    from .admin import default

    print("Setting Defaults")
    success = models.set_defaults(default_list=default.default_list)
    if not success:
        return False

    print("Setting up Oshkelosh Configs")
    oshkelosh = models.set_configs()
    for key, config in oshkelosh.items():
        app.redis.set(key, json.dumps(config.data()))

    print("Loading Jinja2 ChoiseLoader")
    path = os.path.join(app.root_path, "addons", "style")
    oshkelosh_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader(path)])
    app.jinja_loader = oshkelosh_loader

    # login.init_app(app)

    print("Loading Blueprints")
    from app.main import bp as main_bp

    app.register_blueprint(main_bp, url_prefix="")

    from app.admin import bp as admin_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.user import bp as user_bp

    app.register_blueprint(user_bp, url_prefix="/user")

    print(f"Strating Oshkelosh Flask {env_config['FLASK_ENV']} server for {__name__}\n")

    return app
