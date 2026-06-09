from __future__ import annotations

import traceback
from typing import Any, Dict, Tuple, Union

from flask import Response, jsonify

from core.agent_platform import Message
from core.intent import match_travel_intent
from core.support import clean_llm_response
from core.validation import validate_user_input
from ui.context import AppContext
from ui.history import persist_travel_guide
from ui.sse import travel_sse_response

FlaskReturn = Union[Response, Tuple[Response, int], Tuple[Any, int]]


def parse_user_input(
    raw_input: str,
    *,
    as_bad_request: bool = False,
) -> Tuple[str, FlaskReturn | None]:
    try:
        return validate_user_input(raw_input), None
    except ValueError as exc:
        response = jsonify({"response": str(exc)})
        if as_bad_request:
            return "", (response, 400)
        return "", response


def handle_ask(ctx: AppContext, raw_input: str) -> FlaskReturn:
    user_input, error_response = parse_user_input(raw_input)
    if error_response is not None:
        return error_response

    ctx.logger.info("User Query: %s", user_input)
    user_message = Message(content=user_input, sender="User")
    travel = match_travel_intent(user_input)

    try:
        if travel:
            return _handle_travel_guide(ctx, user_input, travel)

        response = ctx.coordinator.process_message(user_message, "Assistant")
        ctx.logger.info("Assistant Response: %s", response.content)
        return jsonify({"response": clean_llm_response(response.content)})

    except TimeoutError as exc:
        return _timeout_response(ctx, exc)

    except Exception as exc:
        ctx.logger.error("Error: %s\n%s", exc, traceback.format_exc())
        return jsonify(
            {
                "response": (
                    "I'm sorry, but I encountered an error processing your request. "
                    "Please try again."
                )
            }
        )


def handle_ask_stream(ctx: AppContext, raw_input: str) -> FlaskReturn:
    user_input, error_response = parse_user_input(raw_input, as_bad_request=True)
    if error_response is not None:
        return error_response

    travel = match_travel_intent(user_input)
    if not travel:
        return (
            jsonify({"response": "Streaming is available for travel guide requests only."}),
            400,
        )

    location, raw_date_str = travel
    return travel_sse_response(
        ctx.runner,
        user_input=user_input,
        raw_location=location,
        raw_date=raw_date_str,
    )


def _handle_travel_guide(
    ctx: AppContext,
    user_input: str,
    travel: Tuple[str, str],
) -> FlaskReturn:
    location, raw_date_str = travel
    ctx.logger.info("Detected travel intent for %s on %s", location, raw_date_str)

    final_state = ctx.runner.invoke(
        user_input=user_input,
        raw_location=location,
        raw_date=raw_date_str,
    )
    cleaned = final_state.get("final_response") or ""
    ctx.logger.info(
        "Final Response (run_id=%s thread_id=%s status=%s): %s",
        final_state.get("run_id"),
        final_state.get("thread_id"),
        final_state.get("status"),
        cleaned,
    )

    persist_travel_guide(
        user_query=user_input,
        location=location,
        raw_date=raw_date_str,
        final_state=final_state,
        final_response=cleaned,
    )
    return jsonify({"response": cleaned})


def _timeout_response(ctx: AppContext, exc: TimeoutError) -> FlaskReturn:
    limit = getattr(ctx.runner, "config", None)
    secs = getattr(limit, "global_timeout_seconds", None) if limit else None
    ctx.logger.error(
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
