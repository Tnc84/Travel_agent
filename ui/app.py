import atexit
import json
import logging
import os
import traceback
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from core.agent_platform import Coordinator, Message
from core.agent_platform.builder import build_agents
from core.graph.runner import TravelGraphRunner
from core.intent import match_travel_intent
from core.location import LocationResolver
from core.llm import build_primary_provider
from core.support import clean_llm_response
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
        logger.info(
            "Hugging Face API: %s",
            "✓ (API key provided)" if huggingface_key else "✓ (free tier)",
        )

        primary_provider_name, primary_provider = build_primary_provider(logger.warning)
        logger.info("Using %s as primary provider", primary_provider_name)

        coordinator_local = Coordinator()
        build_agents(coordinator_local, primary_provider)
        return coordinator_local

    coordinator = initialize_agents()
    location_resolver = LocationResolver()

    runner = TravelGraphRunner(coordinator, location_resolver)
    runner.__enter__()
    logger.info("LangGraph travel runtime started (checkpoint=%s)", bool(runner.config.checkpoint_dsn))
    atexit.register(lambda: runner.__exit__(None, None, None))

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
                logger.info("Detected travel intent for %s on %s", location, raw_date_str)

                final_state = runner.invoke(
                    user_input=user_input,
                    raw_location=location,
                    raw_date=raw_date_str,
                )
                cleaned = final_state.get("final_response") or ""
                logger.info(
                    "Final Response (run_id=%s thread_id=%s status=%s): %s",
                    final_state.get("run_id"),
                    final_state.get("thread_id"),
                    final_state.get("status"),
                    cleaned,
                )

                os.makedirs("history", exist_ok=True)
                filename = f"history/travel_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, "w") as f:
                    json.dump(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "user_query": user_input,
                            "location": location,
                            "resolved_location": final_state.get("resolved_location"),
                            "date": final_state.get("date_str") or raw_date_str,
                            "status": final_state.get("status"),
                            "run_id": final_state.get("run_id"),
                            "thread_id": final_state.get("thread_id"),
                            "final_response": cleaned,
                        },
                        f,
                        indent=2,
                    )

                return jsonify({"response": cleaned})

            response = coordinator.process_message(user_message, "Assistant")
            logger.info("Assistant Response: %s", response.content)
            return jsonify({"response": clean_llm_response(response.content)})

        except TimeoutError as exc:
            limit = getattr(runner, "config", None)
            secs = getattr(limit, "global_timeout_seconds", None) if limit else None
            logger.error(
                "Graph timed out (%s); TRAVEL_GLOBAL_TIMEOUT_SECONDS=%s",
                exc,
                secs,
                exc_info=True,
            )
            return jsonify(
                {
                    "response": (
                        "The travel guide took too long to finish. Try again, or increase "
                        "TRAVEL_GLOBAL_TIMEOUT_SECONDS if you use a slow local LLM."
                    )
                }
            )

        except Exception as exc:
            logger.error("Error: %s\n%s", exc, traceback.format_exc())
            return jsonify(
                {"response": "I'm sorry, but I encountered an error processing your request. Please try again."}
            )

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

        @stream_with_context
        def event_stream():
            for event_name, payload in runner.stream_events(
                user_input=user_input,
                raw_location=location,
                raw_date=raw_date_str,
            ):
                yield _sse_event(event_name, payload)

        return Response(event_stream(), mimetype="text/event-stream")

    return app


def _sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"
