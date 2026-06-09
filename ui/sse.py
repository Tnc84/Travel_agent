from __future__ import annotations

import json
from typing import Iterator

from flask import Response, stream_with_context

from core.graph.runner import TravelGraphRunner


def format_sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


@stream_with_context
def travel_sse_events(
    runner: TravelGraphRunner,
    *,
    user_input: str,
    raw_location: str,
    raw_date: str,
) -> Iterator[str]:
    for event_name, payload in runner.stream_events(
        user_input=user_input,
        raw_location=raw_location,
        raw_date=raw_date,
    ):
        yield format_sse_event(event_name, payload)


def travel_sse_response(
    runner: TravelGraphRunner,
    *,
    user_input: str,
    raw_location: str,
    raw_date: str,
) -> Response:
    return Response(
        travel_sse_events(
            runner,
            user_input=user_input,
            raw_location=raw_location,
            raw_date=raw_date,
        ),
        mimetype="text/event-stream",
    )
