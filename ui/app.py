import json
import logging
import os
import re
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from dotenv import load_dotenv

from core.base import Message
from core.coordinator import Coordinator
from core.date_parser import normalize_user_date_to_iso
from core.provider_factory import build_primary_provider
from core.agent_builder import build_agents
from core.intent_router import match_travel_intent
from core.location_resolver import LocationResolver
from core.travel_flow import (
    build_structured_fallback_response,
    generate_travel_response_with_tools,
    resolve_location_for_travel,
    run_travel_pipeline,
)
from core.validation import validate_user_input


def create_app():
    logging.basicConfig(
        filename="travel_agent.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("travel_agent")

    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))

    def initialize_agents() -> Coordinator:
        load_dotenv()

        huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        logger.info("Ollama endpoint: %s", ollama_base_url)
        logger.info("Hugging Face API: %s", "✓ (API key provided)" if huggingface_key else "✓ (free tier)")

        primary_provider_name, primary_provider = build_primary_provider(logger.warning)
        logger.info("Using %s as primary provider", primary_provider_name)

        coordinator = Coordinator()
        build_agents(coordinator, primary_provider)
        return coordinator

    coordinator = initialize_agents()
    location_resolver = LocationResolver()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ask", methods=["POST"])
    def ask():
        raw_input = request.form.get("user_input", "")
        try:
            user_input = validate_user_input(raw_input)
        except ValueError as exc:
            return jsonify({"response": str(exc)})

        logger.info("User Query: %s", user_input)
        user_message = Message(content=user_input, sender="User")
        travel = match_travel_intent(user_input)

        try:
            if travel:
                location, raw_date_str = travel
                try:
                    date_str = normalize_user_date_to_iso(raw_date_str)
                except ValueError as exc:
                    return jsonify({"response": str(exc)})
                logger.info("Detected travel intent for %s on %s", location, date_str)
                resolution = resolve_location_for_travel(location, location_resolver)
                if resolution.clarification_message:
                    return jsonify({"response": resolution.clarification_message})
                resolved_location = resolution.resolved_location
                if not resolved_location:
                    return jsonify({"response": "I could not resolve the destination. Please try again with more details."})

                canonical_location = resolved_location.canonical_name
                sections = run_travel_pipeline(resolved_location, date_str)
                if sections.weather or sections.hotels or sections.restaurants or sections.attractions:
                    final_response = generate_travel_response_with_tools(
                        coordinator, canonical_location, date_str, sections
                    )
                    cleaned = _clean_response(final_response.content)
                else:
                    cleaned = build_structured_fallback_response(canonical_location, date_str, sections)
                logger.info("Final Response: %s", cleaned)

                os.makedirs("history", exist_ok=True)
                filename = f"history/travel_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, "w") as f:
                    json.dump(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "user_query": user_input,
                            "location": location,
                            "resolved_location": resolved_location.to_dict(),
                            "date": date_str,
                            # Legacy specialized outputs (disabled in one-call mode):
                            # "weather_response": weather_response.content,
                            # "hotel_response": hotel_response.content,
                            # "restaurant_response": restaurant_response.content,
                            # "attraction_response": attraction_response.content,
                            "final_response": cleaned,
                        },
                        f,
                        indent=2,
                    )

                return jsonify({"response": cleaned})

            response = coordinator.process_message(user_message, "Assistant")
            logger.info("Assistant Response: %s", response.content)
            return jsonify({"response": _clean_response(response.content)})

        except Exception as exc:
            import traceback
            logger.error("Error: %s\n%s", exc, traceback.format_exc())
            return jsonify({"response": "I'm sorry, but I encountered an error processing your request. Please try again."})

    @app.route("/ask/stream", methods=["POST"])
    def ask_stream():
        raw_input = request.form.get("user_input", "")
        try:
            user_input = validate_user_input(raw_input)
        except ValueError as exc:
            return jsonify({"response": str(exc)}), 400

        travel = match_travel_intent(user_input)
        if not travel:
            return jsonify({"response": "Streaming is available for travel guide requests only."}), 400

        location, raw_date_str = travel
        try:
            date_str = normalize_user_date_to_iso(raw_date_str)
        except ValueError as exc:
            return jsonify({"response": str(exc)}), 400
        resolution = resolve_location_for_travel(location, location_resolver)
        if resolution.clarification_message:
            return jsonify({"response": resolution.clarification_message}), 400
        resolved_location = resolution.resolved_location
        if not resolved_location:
            return jsonify({"response": "I could not resolve the destination. Please try again with more details."}), 400

        canonical_location = resolved_location.canonical_name

        @stream_with_context
        def event_stream():
            emitted = []

            def event_callback(event_name, payload):
                emitted.append((event_name, payload))

            sections = run_travel_pipeline(resolved_location, date_str, event_callback=event_callback)
            for event_name, payload in emitted:
                yield _sse_event(event_name, payload)

            if sections.weather or sections.hotels or sections.restaurants or sections.attractions:
                final_response = generate_travel_response_with_tools(
                    coordinator, canonical_location, date_str, sections
                )
                cleaned = _clean_response(final_response.content)
            else:
                cleaned = build_structured_fallback_response(canonical_location, date_str, sections)
            yield _sse_event("final_message", {"response": cleaned})
            yield _sse_event("done", {"ok": True})

        return Response(event_stream(), mimetype="text/event-stream")

    return app


def _clean_response(response_text: str) -> str:
    """Strip any residual prompt leakage from model response."""
    for marker in ("System:", "User:", "Assistant:"):
        if response_text.startswith(marker):
            parts = response_text.split("Assistant:", 1)
            if len(parts) > 1:
                return parts[-1].strip()
    return response_text.strip()


def _sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"
