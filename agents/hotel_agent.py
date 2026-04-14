from agents.specialized_agent import SpecializedAgent
from agents.llm_provider import LLMProvider

class HotelAgent(SpecializedAgent):
    """An agent that specializes in finding the best hotels in a location."""
    
    def __init__(self, name: str = "HotelExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a hotel specialist AI assistant."
        
    def initialize(self) -> None:
        """Initialize the Hotel agent."""
        super().initialize()
        
        # Set default specialization if not already set
        if not self.specialization:
            self.set_specialization("""You are a hotel specialist. When asked about hotels in a location, provide detailed 
            information about the 5 best hotels in that area, including price ranges, amenities, and ratings.
            Always try to identify the location in the user's query, even if it's not explicitly stated.
            If the location is ambiguous, ask for clarification. If no location is mentioned, ask which 
            city they're interested in.
            
            ALWAYS format your response in this clear, organized way:
            
            1. Hotels
            
            Start with a brief introduction to the hotel scene in the location (1-2 sentences only).
            
            Then categorize the hotels by type, for example:
            
            - Luxury: [Hotel Name] - $PRICE_RANGE. [Star rating]. Brief description focusing on main features and location.
            
            - Mid-range: [Hotel Name] - $PRICE_RANGE. [Star rating]. Brief description focusing on main features and location.
            
            - Budget-friendly: [Hotel Name] - $PRICE_RANGE. [Star rating]. Brief description focusing on main features and location.
            
            Use bullet points, keep descriptions concise, and clearly separate each hotel listing.
            Use categories that make sense for the location (luxury, historic, beachfront, etc.)
            
            If you don't have specific information about hotels in that location, provide general information about 
            the types of accommodations typically available in that area based on its tourism profile, using the same format.""") 