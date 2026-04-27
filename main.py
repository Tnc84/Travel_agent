import logging
import os
import traceback

from dotenv import load_dotenv

from core.base import Message
from core.coordinator import Coordinator
from core.provider_factory import build_primary_provider
from core.agent_builder import build_agents
from core.intent_router import match_travel_intent, route_by_keywords
from core.location_resolver import LocationResolver
from core.travel_flow import (
    build_structured_fallback_response,
    generate_travel_response_with_tools,
    resolve_location_for_travel,
    run_travel_pipeline,
)
from core.validation import validate_user_input

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    print("Available APIs:")
    print(f"- Ollama: local server at {ollama_base_url}")
    print(f"- Hugging Face: {'✓ (API key provided)' if huggingface_key else '✓ (free tier)'}")

    primary_provider_name, primary_provider = build_primary_provider()
    print(f"Using {primary_provider_name} as primary provider")

    coordinator = Coordinator()
    build_agents(coordinator, primary_provider)
    location_resolver = LocationResolver()

    print("\nMulti-Agent Travel Assistant System (Type 'exit' to quit)")
    print("Available agents:", ", ".join(coordinator.agents.keys()))
    print("Switch agents: '@AgentName your message'")
    print("Travel guide: 'I want to go to [location] on [date]'")
    print("-" * 50)

    current_agent = "Assistant"

    while True:
        raw_input = input("You: ")

        if raw_input.strip().lower() == "exit":
            break

        try:
            user_input = validate_user_input(raw_input)
        except ValueError as exc:
            print(f"Input error: {exc}")
            continue

        if user_input.startswith("@"):
            parts = user_input.split(" ", 1)
            agent_name = parts[0][1:]
            if agent_name in coordinator.agents:
                current_agent = agent_name
                print(f"Switched to {current_agent}")
                if len(parts) > 1:
                    user_input = parts[1]
                else:
                    continue
            else:
                print(f"Agent '{agent_name}' not found. Available: {', '.join(coordinator.agents.keys())}")
                continue

        user_message = Message(content=user_input, sender="User")
        travel = match_travel_intent(user_input)

        if travel:
            location, date_str = travel
            print(f"Detected travel intent for {location} on {date_str}")
            print("Building comprehensive travel guide...")
            try:
                resolution = resolve_location_for_travel(location, location_resolver)
                if resolution.clarification_message:
                    print(resolution.clarification_message.replace("to continue.", "and try again."))
                    print("-" * 50)
                    continue
                resolved_location = resolution.resolved_location
                if not resolved_location:
                    print("I could not resolve the destination. Please try again with more details.")
                    print("-" * 50)
                    continue

                canonical_location = resolved_location.canonical_name
                print("Collecting weather, hotels, restaurants, and attractions...")

                def _event_callback(event_name, payload):
                    if event_name == "location_resolved":
                        print("Location resolved.")
                    elif event_name.endswith("_ready"):
                        print(f"{event_name.replace('_ready', '').capitalize()} ready.")
                    elif event_name == "final_ready":
                        print("All sections completed.")

                sections = run_travel_pipeline(resolved_location, date_str, event_callback=_event_callback)
                if not (sections.weather or sections.hotels or sections.restaurants or sections.attractions):
                    print("Tool providers unavailable. Returning structured fallback.")
                    print(build_structured_fallback_response(canonical_location, date_str, sections))
                    print("-" * 50)
                    continue

                final_response = generate_travel_response_with_tools(
                    coordinator,
                    canonical_location,
                    date_str,
                    sections,
                )
                print(f"{final_response.sender}: {final_response.content}")
            except Exception as exc:
                logger.error("Error building travel guide: %s\n%s", exc, traceback.format_exc())
                try:
                    response = coordinator.process_message(user_message, current_agent)
                    print(f"{response.sender}: {response.content}")
                except Exception as fallback_exc:
                    print(f"Error: {fallback_exc}")
        else:
            target_agent = route_by_keywords(user_input, current_agent)
            if target_agent != current_agent:
                print(f"Routing to {target_agent} based on query content...")
            try:
                response = coordinator.process_message(user_message, target_agent)
                print(f"{response.sender}: {response.content}")
            except Exception as exc:
                logger.error("Error processing message: %s\n%s", exc, traceback.format_exc())

        print("-" * 50)


if __name__ == "__main__":
    main()
