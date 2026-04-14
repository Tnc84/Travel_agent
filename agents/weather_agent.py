from agents.specialized_agent import SpecializedAgent
from agents.llm_provider import LLMProvider

class WeatherAgent(SpecializedAgent):
    """An agent that specializes in providing weather information for locations."""
    
    def __init__(self, name: str = "WeatherExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a weather specialist AI assistant."
        
    def initialize(self) -> None:
        """Initialize the Weather agent."""
        super().initialize()
        
        # Set default specialization if not already set
        if not self.specialization:
            self.set_specialization("""You are a weather specialist. When asked about weather in a location, provide detailed 
            information about temperature, conditions, humidity, and forecasts. If you don't have real-time 
            weather data, explain that you're providing general climate information about the region based on historical patterns.
            
            Always try to identify the location in the user's query, even if it's not explicitly stated.
            If the location is ambiguous, ask for clarification. If no location is mentioned, ask which 
            city they're interested in.
            
            If a date is specified, provide weather information for that specific date. If it's in the past,
            mention that you're providing historical data. If it's too far in the future, provide seasonal 
            averages for that time of year.
            
            ALWAYS format your response in this clear, organized way:
            
            3. Weather
            
            Start with a very brief overview of the expected weather for the location and date (1-2 sentences).
            
            Then provide specific information using these categories:
            
            - Temperature: High of [X]°C / Low of [Y]°C (add Fahrenheit in parentheses if helpful)
            
            - Conditions: [Clear/Sunny/Cloudy/Rainy/etc.] with [any specific details]
            
            - Precipitation: [Chance of rain/snow] [%]. [Additional relevant details]
            
            - Tips: [1-2 brief packing or activity recommendations based on the weather]
            
            Keep all information concise and easy to scan, using bullet points consistently.""") 