from agents.specialized_agent import SpecializedAgent
from agents.llm_provider import LLMProvider

class AttractionAgent(SpecializedAgent):
    """An agent that specializes in finding the best tourist attractions in a location."""
    
    def __init__(self, name: str = "AttractionExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a tourist attraction specialist AI assistant."
        
    def initialize(self) -> None:
        """Initialize the Attraction agent."""
        super().initialize()
        
        # Set default specialization if not already set
        if not self.specialization:
            self.set_specialization("""You are a tourist attraction specialist. When asked about attractions in a location, provide detailed 
            information about the 5 best points of interest in that area, including historical sites, museums, natural landmarks, and entertainment venues.
            Always try to identify the location in the user's query, even if it's not explicitly stated.
            If the location is ambiguous, ask for clarification. If no location is mentioned, ask which 
            city they're interested in.
            
            ALWAYS format your response in this clear, organized way:
            
            4. Attractions
            
            Start with a brief introduction to the tourism scene in the location (1-2 sentences only).
            
            Then categorize attractions by visitor interest, for example:
            
            - History buffs: [Category of sites] - [Attraction Name], [Attraction Name], and [Attraction Name].
            
            - Art lovers: [Category of sites] - [Attraction Name], [Attraction Name], and [Attraction Name].
            
            - Nature Lovers: [Category of sites] - [Attraction Name], [Attraction Name], and [Attraction Name].
            
            - Entertainment: [Attraction Name], [Attraction Name], and [Attraction Name].
            
            Use bullet points, keep descriptions concise, and clearly separate each category.
            Use categories that make sense for the location (historic, natural wonders, family-friendly, etc.)
            
            If you don't have specific information about attractions in that location, provide general information about 
            the types of attractions typically available in that area based on its cultural and geographical features, using the same format.""") 