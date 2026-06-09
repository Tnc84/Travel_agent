from __future__ import annotations

from flask import Flask, render_template, request

from ui.context import AppContext
from ui.handlers import handle_ask, handle_ask_stream


def register_routes(app: Flask, ctx: AppContext) -> None:
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ask", methods=["POST"])
    def ask():
        return handle_ask(ctx, request.form.get("user_input", ""))

    @app.route("/ask/stream", methods=["POST"])
    def ask_stream():
        return handle_ask_stream(ctx, request.form.get("user_input", ""))
