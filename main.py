import logging
import os
import traceback

from dotenv import load_dotenv

from core.agent_platform import Coordinator, Message
from core.agent_platform.builder import build_agents
from core.graph.runner import open_runner
from core.intent import match_travel_intent, route_by_keywords
from core.location import LocationResolver
from core.llm import build_primary_provider
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
    hf_status = "✓ (API key provided)" if huggingface_key else "✓ (free tier)"
    print(f"- Hugging Face: {hf_status}")

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

    with open_runner(coordinator, location_resolver) as runner:
        while True:
            raw_input_text = input("You: ")

            if raw_input_text.strip().lower() == "exit":
                break

            try:
                user_input = validate_user_input(raw_input_text)
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
                    print(
                        f"Agent '{agent_name}' not found. "
                        f"Available: {', '.join(coordinator.agents.keys())}"
                    )
                    continue

            user_message = Message(content=user_input, sender="User")
            travel = match_travel_intent(user_input)

            if travel:
                location, raw_date_str = travel
                print(f"Detected travel intent for {location} on {raw_date_str}")
                print("Building comprehensive travel guide...")
                try:
                    for event_name, payload in runner.stream_events(
                        user_input=user_input,
                        raw_location=location,
                        raw_date=raw_date_str,
                    ):
                        if event_name == "location_resolved":
                            print("Location resolved.")
                        elif event_name.endswith("_ready"):
                            section = event_name.replace("_ready", "").capitalize()
                            print(f"{section} ready.")
                        elif event_name == "final_message":
                            print(f"Assistant: {payload.get('response', '')}")
                        elif event_name == "done":
                            print("All sections completed.")
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
