from flask import Flask, jsonify

from .config import Config
from .db import init_db
from .errors import register_error_handlers
from .routes.events import events_bp


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    app.url_map.strict_slashes = False

    init_db(app)
    register_error_handlers(app)
    app.register_blueprint(events_bp, url_prefix="/api/events")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
