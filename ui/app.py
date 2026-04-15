import json
import logging
import os
import re
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from core.base import Message
from core.coordinator import Coordinator
from core.provider_factory import build_primary_provider
from core.agent_builder import build_agents
from core.intent_router import match_travel_intent
from core.location_resolver import LocationResolver
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
                location, date_str = travel
                logger.info("Detected travel intent for %s on %s", location, date_str)
                resolved_location = location_resolver.resolve(location)
                if not location_resolver.is_confident(resolved_location):
                    return jsonify(
                        {
                            "response": (
                                f"I found multiple possible matches for '{location}'. "
                                "Please include country or county to continue."
                            )
                        }
                    )

                canonical_location = resolved_location.canonical_name

                weather_response = coordinator.process_message(
                    Message(content=f"What will the weather be like in {canonical_location} on {date_str}?", sender="User"),
                    "WeatherExpert",
                )
                hotel_response = coordinator.process_message(
                    Message(content=f"What are the 5 best hotels in {canonical_location}?", sender="User"),
                    "HotelExpert",
                )
                restaurant_response = coordinator.process_message(
                    Message(content=f"What are the 5 best restaurants in {canonical_location}?", sender="User"),
                    "RestaurantExpert",
                )
                attraction_response = coordinator.process_message(
                    Message(content=f"What are the 5 best attractions in {canonical_location}?", sender="User"),
                    "AttractionExpert",
                )

                guide_prompt = (
                    f"Create a comprehensive travel guide for {canonical_location} on {date_str} using the following information:\n\n"
                    f"WEATHER:\n{weather_response.content}\n\n"
                    f"HOTELS:\n{hotel_response.content}\n\n"
                    f"RESTAURANTS:\n{restaurant_response.content}\n\n"
                    f"ATTRACTIONS:\n{attraction_response.content}\n\n"
                    "Format the guide in a clear, organized way with sections for weather, accommodation, dining, and sightseeing. "
                    "Add a brief introduction and conclusion."
                )
                final_response = coordinator.process_message(
                    Message(content=guide_prompt, sender="User"), "Assistant"
                )
                logger.info("Final Response: %s", final_response.content)
                cleaned = _clean_response(final_response.content)

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
                            "weather_response": weather_response.content,
                            "hotel_response": hotel_response.content,
                            "restaurant_response": restaurant_response.content,
                            "attraction_response": attraction_response.content,
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

    return app


def _clean_response(response_text: str) -> str:
    """Strip any residual prompt leakage from model response."""
    for marker in ("System:", "User:", "Assistant:"):
        if response_text.startswith(marker):
            parts = response_text.split("Assistant:", 1)
            if len(parts) > 1:
                return parts[-1].strip()
    return response_text.strip()
