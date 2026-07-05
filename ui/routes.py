from __future__ import annotations

from typing import Any, Tuple, Union

from flask import Response, jsonify, request

from core.persistence.config import load_persistence_config
from core.persistence.repositories.trips import TripRepository
from ui.context import AppContext
from ui.handlers import handle_ask, handle_ask_stream
from flask import render_template

FlaskReturn = Union[Response, Tuple[Response, int], Tuple[Any, int]]


def _user_id_from_request() -> str:
    return request.headers.get("X-User-Id") or request.args.get("user_id") or "anonymous"


def register_routes(app, ctx: AppContext) -> None:
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ask", methods=["POST"])
    def ask():
        return handle_ask(ctx, request.form.get("user_input", ""))

    @app.route("/ask/stream", methods=["POST"])
    def ask_stream():
        return handle_ask_stream(ctx, request.form.get("user_input", ""))

    @app.route("/trips", methods=["GET"])
    def list_trips():
        if not load_persistence_config().enabled:
            return jsonify({"error": "APP_DATABASE_DSN not configured"}), 503
        user_id = _user_id_from_request()
        limit = min(int(request.args.get("limit", 20)), 100)
        trips = TripRepository().list_by_user(user_id, limit=limit)
        return jsonify({"trips": [t.model_dump() for t in trips]})

    @app.route("/trips/<trip_id>", methods=["GET"])
    def get_trip(trip_id: str):
        if not load_persistence_config().enabled:
            return jsonify({"error": "APP_DATABASE_DSN not configured"}), 503
        trip = TripRepository().get_by_id(trip_id)
        if trip is None:
            return jsonify({"error": "trip not found"}), 404
        return jsonify({"trip": trip})

    @app.route("/trips", methods=["POST"])
    def create_trip():
        if not load_persistence_config().enabled:
            return jsonify({"error": "APP_DATABASE_DSN not configured"}), 503
        payload = request.get_json(silent=True) or {}
        required = ("query", "location", "date_str", "response")
        missing = [field for field in required if not payload.get(field)]
        if missing:
            return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
        user_id = payload.get("user_id") or _user_id_from_request()
        trip_id = TripRepository().save_trip(
            user_id=user_id,
            query=payload["query"],
            location=payload["location"],
            date_str=payload["date_str"],
            response=payload["response"],
            resolved_location=payload.get("resolved_location"),
            graph_run_id=payload.get("graph_run_id"),
            thread_id=payload.get("thread_id"),
        )
        return jsonify({"trip_id": trip_id}), 201

    @app.route("/trips/<trip_id>/favorite", methods=["POST"])
    def add_favorite(trip_id: str):
        if not load_persistence_config().enabled:
            return jsonify({"error": "APP_DATABASE_DSN not configured"}), 503
        TripRepository().add_favorite(_user_id_from_request(), trip_id)
        return jsonify({"ok": True})

    @app.route("/trips/<trip_id>/favorite", methods=["DELETE"])
    def remove_favorite(trip_id: str):
        if not load_persistence_config().enabled:
            return jsonify({"error": "APP_DATABASE_DSN not configured"}), 503
        TripRepository().remove_favorite(_user_id_from_request(), trip_id)
        return jsonify({"ok": True})
