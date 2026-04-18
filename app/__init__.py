"""Flask application factory for the HL7 Integration Engine."""

import logging
from flask import Flask

from app.core.storage import init_db


def create_app():
    app = Flask(__name__)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    init_db()

    from app.routes import bp
    app.register_blueprint(bp)

    return app