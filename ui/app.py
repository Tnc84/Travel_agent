import os

from flask import Flask

from ui.bootstrap import build_app_context
from ui.routes import register_routes


def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
    ctx = build_app_context()
    register_routes(app, ctx)
    return app
