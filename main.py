from agents import (
    GeneralAgent, WeatherAgent, HotelAgent, RestaurantAgent, AttractionAgent
)
from core.base import Message
from core.coordinator import Coordinator
from core.provider_factory import build_primary_provider
import os
import re
from datetime import datetime
from dotenv import load_dotenv


def main():
    load_dotenv()
    
    # Create coordinator
    coordinator = Coordinator()
    
    # Check available API key
    huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Print available API
    print("Available APIs:")
    print(f"- Ollama: local server at {ollama_base_url}")
    print(f"- Hugging Face: {'✓ (API key provided)' if huggingface_key else '✓ (free tier)'}")
    
    # Create LLM provider with fallback
    primary_provider_name, primary_provider = build_primary_provider()
    print(f"Using {primary_provider_name} as primary provider")
    
    # Create specialized agents using the primary provider
    general_assistant = GeneralAgent("Assistant", primary_provider)
    weather_assistant = WeatherAgent("WeatherExpert", primary_provider)
    hotel_assistant = HotelAgent("HotelExpert", primary_provider)
    restaurant_assistant = RestaurantAgent("RestaurantExpert", primary_provider)
    attraction_assistant = AttractionAgent("AttractionExpert", primary_provider)
    
    # Initialize agents
    general_assistant.initialize()
    weather_assistant.initialize()
    hotel_assistant.initialize()
    restaurant_assistant.initialize()
    attraction_assistant.initialize()
    
    # Add agents to coordinator
    coordinator.add_agent(general_assistant)
    coordinator.add_agent(weather_assistant)
    coordinator.add_agent(hotel_assistant)
    coordinator.add_agent(restaurant_assistant)
    coordinator.add_agent(attraction_assistant)
    
    print("\nMulti-Agent Travel Assistant System (Type 'exit' to quit)")
    print("Available agents: Assistant, WeatherExpert, HotelExpert, RestaurantExpert, AttractionExpert")
    print("You can switch agents by typing '@AgentName your message'")
    print("For a comprehensive travel guide, simply say: 'I want to go to [location] on [date]'")
    print("-" * 50)
    
    current_agent = "Assistant"  # Default agent
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'exit':
            break
        
        # Check for agent switching command
        if user_input.lower().startswith("@"):
            parts = user_input.split(" ", 1)
            agent_name = parts[0][1:]  # Remove @ symbol
            
            if agent_name in coordinator.agents:
                current_agent = agent_name
                print(f"Switched to {current_agent}")
                
                # If there's a message after the agent name, process it
                if len(parts) > 1:
                    user_input = parts[1]
                else:
                    continue
            else:
                print(f"Agent '{agent_name}' not found. Available agents: {', '.join(coordinator.agents.keys())}")
                continue
        
        # Create user message
        user_message = Message(
            content=user_input,
            sender="User"
        )
        
        # Check for travel intent pattern: "I want to go to/in [location] on [date]"
        travel_pattern = re.compile(r"(?:i want to|planning to|going to|travel to|visit) (?:go to|go in|visit) ([a-zA-Z\s]+) (?:on|at|in) ([a-zA-Z0-9\s,]+)", re.IGNORECASE)
        match = travel_pattern.search(user_input)
        
        if match:
            # Extract location and date
            location = match.group(1).strip()
            date_str = match.group(2).strip()
            
            print(f"Detected travel intent for {location} on {date_str}")
            print("Building comprehensive travel guide...")
            
            # Collect information from all specialized agents
            try:
                # 1. Get weather information
                weather_query = f"What will the weather be like in {location} on {date_str}?"
                weather_message = Message(content=weather_query, sender="User")
                weather_response = coordinator.process_message(weather_message, "WeatherExpert")
                
                # 2. Get hotel information
                hotel_query = f"What are the 5 best hotels in {location}?"
                hotel_message = Message(content=hotel_query, sender="User")
                hotel_response = coordinator.process_message(hotel_message, "HotelExpert")
                
                # 3. Get restaurant information
                restaurant_query = f"What are the 5 best restaurants in {location}?"
                restaurant_message = Message(content=restaurant_query, sender="User")
                restaurant_response = coordinator.process_message(restaurant_message, "RestaurantExpert")
                
                # 4. Get attraction information
                attraction_query = f"What are the 5 best attractions in {location}?"
                attraction_message = Message(content=attraction_query, sender="User")
                attraction_response = coordinator.process_message(attraction_message, "AttractionExpert")
                
                # 5. Compile comprehensive guide
                guide_prompt = f"""Create a comprehensive travel guide for {location} on {date_str} using the following information:
                
                WEATHER:
                {weather_response.content}
                
                HOTELS:
                {hotel_response.content}
                
                RESTAURANTS:
                {restaurant_response.content}
                
                ATTRACTIONS:
                {attraction_response.content}
                
                Format the guide in a clear, organized way with sections for weather, accommodation, dining, and sightseeing.
                Add a brief introduction and conclusion.
                """
                
                guide_message = Message(content=guide_prompt, sender="User")
                final_response = coordinator.process_message(guide_message, "Assistant")
                
                print(f"{final_response.sender}: {final_response.content}")
            
            except Exception as e:
                import traceback
                print(f"Error building travel guide: {str(e)}")
                print(traceback.format_exc())
                
                # Fall back to general assistant
                try:
                    print(f"Processing message with {current_agent} instead...")
                    response = coordinator.process_message(user_message, current_agent)
                    print(f"{response.sender}: {response.content}")
                except Exception as e:
                    print(f"Error: {str(e)}")
        else:
            # Determine which agent to use based on content
            target_agent = current_agent
            weather_keywords = ["weather", "temperature", "forecast", "rain", "sunny", "climate", "humid", "cold", "hot"]
            hotel_keywords = ["hotel", "motel", "accommodation", "stay", "room", "suite", "lodge", "resort"]
            restaurant_keywords = ["restaurant", "food", "eat", "dining", "cuisine", "meal", "breakfast", "lunch", "dinner"]
            attraction_keywords = ["attraction", "visit", "sightseeing", "tour", "museum", "landmark", "monument", "park", "gallery"]
            
            if current_agent == "Assistant":
                if any(keyword in user_input.lower() for keyword in weather_keywords):
                    target_agent = "WeatherExpert"
                elif any(keyword in user_input.lower() for keyword in hotel_keywords):
                    target_agent = "HotelExpert"
                elif any(keyword in user_input.lower() for keyword in restaurant_keywords):
                    target_agent = "RestaurantExpert"
                elif any(keyword in user_input.lower() for keyword in attraction_keywords):
                    target_agent = "AttractionExpert"
                
                if target_agent != "Assistant":
                    print(f"Routing to {target_agent} based on query content...")
            
            # Process message with appropriate agent
            try:
                print(f"Processing message with {target_agent}...")
                response = coordinator.process_message(user_message, target_agent)
                print(f"{response.sender}: {response.content}")
            except Exception as e:
                import traceback
                print(f"Error: {str(e)}")
                print(traceback.format_exc())
        
        print("-" * 50)

if __name__ == "__main__":
    main() 