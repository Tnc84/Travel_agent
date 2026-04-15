import logging
import os
import traceback

from dotenv import load_dotenv

from core.base import Message
from core.coordinator import Coordinator
from core.provider_factory import build_primary_provider
from core.agent_builder import build_agents
from core.intent_router import match_travel_intent, route_by_keywords
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
                weather_response = coordinator.process_message(
                    Message(content=f"What will the weather be like in {location} on {date_str}?", sender="User"),
                    "WeatherExpert",
                )
                hotel_response = coordinator.process_message(
                    Message(content=f"What are the 5 best hotels in {location}?", sender="User"),
                    "HotelExpert",
                )
                restaurant_response = coordinator.process_message(
                    Message(content=f"What are the 5 best restaurants in {location}?", sender="User"),
                    "RestaurantExpert",
                )
                attraction_response = coordinator.process_message(
                    Message(content=f"What are the 5 best attractions in {location}?", sender="User"),
                    "AttractionExpert",
                )

                guide_prompt = (
                    f"Create a comprehensive travel guide for {location} on {date_str} using the following information:\n\n"
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
