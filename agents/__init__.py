# Main agents package initialization
# This file handles importing and exposing agent classes from submodules

# LLM Providers
from agents.huggingface_provider import HuggingFaceProvider

# Specialized Agents
from agents.general_agent import GeneralAgent
from agents.weather_agent import WeatherAgent
from agents.hotel_agent import HotelAgent
from agents.restaurant_agent import RestaurantAgent
from agents.attraction_agent import AttractionAgent

# For backward compatibility
from agents.specialized_agent import SpecializedAgent

__all__ = [
    'HuggingFaceProvider',
    'GeneralAgent',
    'WeatherAgent', 
    'HotelAgent', 
    'RestaurantAgent', 
    'AttractionAgent',
    'SpecializedAgent'
] 