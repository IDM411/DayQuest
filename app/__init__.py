from flask import Flask
from flask_migrate import Migrate

from .models import db

migrate = Migrate()


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    from .routes import bp as api_bp

    app.register_blueprint(api_bp)

    return app
