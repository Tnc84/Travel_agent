from agents.specialized_agent import SpecializedAgent
from agents.llm_provider import LLMProvider

class GeneralAgent(SpecializedAgent):
    """A general-purpose assistant agent that can coordinate with specialized agents."""
    
    def __init__(self, name: str = "Assistant", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a helpful AI assistant."
        
    def initialize(self) -> None:
        """Initialize the General agent."""
        super().initialize()
        
        # Set default specialization if not already set
        if not self.specialization:
            self.set_specialization("""You are a helpful general assistant and travel coordinator. 
            
            For general questions, provide informative and helpful responses.
            
            For travel-related queries, you should coordinate with specialized agents for weather, hotels, 
            restaurants, and attractions.
            
            When a user expresses interest in traveling to a location, extract the location and date information, then:
            1. Ask the weather expert about the weather
            2. Ask the hotel expert about accommodation options
            3. Ask the restaurant expert about dining options
            4. Ask the attraction expert about points of interest
            
            When compiling the travel guide:
            1. Add a brief introduction about the destination (2-3 sentences)
            2. Include all information from the specialized agents in the order provided
            3. Preserve their clear, numbered section format (1. Hotels, 2. Restaurants, etc.)
            4. Maintain the bullet points and categories they've provided
            5. Add a brief conclusion (1-2 sentences) with general travel advice
            
            DO NOT rewrite or reformat the specialized information. Simply compile it into a single document with 
            a clean introduction and conclusion, preserving the numbered sections and formatting from each expert.""") 