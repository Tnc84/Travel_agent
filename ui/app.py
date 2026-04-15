from flask import Flask, render_template, request, jsonify
import os
import re
import logging
from datetime import datetime
import json
from agents import (
    GeneralAgent, WeatherAgent, HotelAgent, RestaurantAgent, AttractionAgent
)
from core.base import Message
from core.coordinator import Coordinator
from core.provider_factory import build_primary_provider
from dotenv import load_dotenv


def create_app():
    """Create and configure the Flask application"""
    
    # Setup logging
    logging.basicConfig(
        filename='travel_agent.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('travel_agent')

    # Create Flask app
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

    # Initialize the travel agent system
    def initialize_agents():
        load_dotenv()
        
        # Create coordinator
        coordinator = Coordinator()
        
        # Check available API key
        huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Log API info
        logger.info(f"Ollama endpoint: {ollama_base_url}")
        logger.info(f"Hugging Face API: {'✓ (API key provided)' if huggingface_key else '✓ (free tier)'}")
        
        # Create LLM provider with fallback
        primary_provider_name, primary_provider = build_primary_provider(logger.warning)
        logger.info(f"Using {primary_provider_name} as primary provider")
        
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
        
        return coordinator

    # Initialize agents when the app starts
    coordinator = initialize_agents()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/ask', methods=['POST'])
    def ask():
        user_input = request.form.get('user_input', '').strip()
        
        if not user_input:
            return jsonify({'response': 'Please enter a query.'})
        
        # Log user query
        logger.info(f"User Query: {user_input}")
        
        # Create user message
        user_message = Message(
            content=user_input,
            sender="User"
        )
        
        # Check for travel intent pattern: "I want to go to/in [location] on [date]"
        travel_pattern = re.compile(r"(?:i want to|planning to|going to|travel to|visit) (?:go to|go in|visit) ([a-zA-Z\s]+) (?:on|at|in) ([a-zA-Z0-9\s,]+)", re.IGNORECASE)
        match = travel_pattern.search(user_input)
        
        try:
            if match:
                # Extract location and date
                location = match.group(1).strip()
                date_str = match.group(2).strip()
                
                logger.info(f"Detected travel intent for {location} on {date_str}")
                logger.info("Building comprehensive travel guide...")
                
                # Collect information from all specialized agents
                # 1. Get weather information
                weather_query = f"What will the weather be like in {location} on {date_str}?"
                weather_message = Message(content=weather_query, sender="User")
                weather_response = coordinator.process_message(weather_message, "WeatherExpert")
                logger.info(f"Weather Response: {weather_response.content}")
                
                # 2. Get hotel information
                hotel_query = f"What are the 5 best hotels in {location}?"
                hotel_message = Message(content=hotel_query, sender="User")
                hotel_response = coordinator.process_message(hotel_message, "HotelExpert")
                logger.info(f"Hotel Response: {hotel_response.content}")
                
                # 3. Get restaurant information
                restaurant_query = f"What are the 5 best restaurants in {location}?"
                restaurant_message = Message(content=restaurant_query, sender="User")
                restaurant_response = coordinator.process_message(restaurant_message, "RestaurantExpert")
                logger.info(f"Restaurant Response: {restaurant_response.content}")
                
                # 4. Get attraction information
                attraction_query = f"What are the 5 best attractions in {location}?"
                attraction_message = Message(content=attraction_query, sender="User")
                attraction_response = coordinator.process_message(attraction_message, "AttractionExpert")
                logger.info(f"Attraction Response: {attraction_response.content}")
                
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
                
                # Log the final response
                logger.info(f"Final Response: {final_response.content}")
                
                # Clean the response by removing system prompt text
                cleaned_response = clean_response(final_response.content)
                
                # Save the travel guide to a JSON file for history
                history_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "user_query": user_input,
                    "location": location,
                    "date": date_str,
                    "weather_response": weather_response.content,
                    "hotel_response": hotel_response.content,
                    "restaurant_response": restaurant_response.content,
                    "attraction_response": attraction_response.content,
                    "final_response": cleaned_response
                }
                
                # Create history directory if it doesn't exist
                os.makedirs('history', exist_ok=True)
                
                # Save to a JSON file with timestamp in the filename
                filename = f"history/travel_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(history_entry, f, indent=2)
                
                # Return only the final response to the UI
                return jsonify({'response': cleaned_response})
            else:
                # For non-travel queries, just use the general assistant
                logger.info(f"Processing with Assistant...")
                response = coordinator.process_message(user_message, "Assistant")
                logger.info(f"Assistant Response: {response.content}")
                
                # Clean the response
                cleaned_response = clean_response(response.content)
                
                return jsonify({'response': cleaned_response})
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"Error: {error_msg}")
            logger.error(error_traceback)
            
            return jsonify({'response': f"I'm sorry, but I encountered an error processing your request. Please try again or rephrase your query."})

    # Helper function to clean responses
    def clean_response(response_text):
        """Remove system prompts and instructions from the response"""
        # Remove the system prompt
        if "System: You are Assistant, a helpful AI assistant." in response_text:
            response_text = response_text.split("System: You are Assistant, a helpful AI assistant.", 1)[1].strip()
        
        # Remove the detailed assistant instructions if present
        if "You are a helpful general assistant and travel coordinator." in response_text:
            parts = response_text.split("User:", 1)
            if len(parts) > 1:
                response_text = parts[1].strip()
        
        return response_text

    return app 