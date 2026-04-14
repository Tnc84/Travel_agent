import os
import requests
import json
from typing import Dict, Any, List, Union
from dotenv import load_dotenv
from agents.llm_provider import LLMProvider

load_dotenv()

class HuggingFaceProvider(LLMProvider):
    """Provider that uses HuggingFace's API to generate responses."""
    
    def __init__(self, model_id: str = "HuggingFaceH4/zephyr-7b-beta"):
        super().__init__(model_id)  # model_id is the model in HuggingFace's case
        self.model_id = model_id
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    def initialize(self) -> None:
        """Initialize the HuggingFace provider."""
        # Check if API key is set (optional for HuggingFace)
        if not self.api_key:
            print(f"Note: No HUGGINGFACE_API_KEY provided. Using free tier with rate limits.")
    
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate a response using HuggingFace's API."""
        try:
            # Format the conversation as a text prompt
            prompt = ""
            
            # Add system prompt if provided
            if system_prompt:
                prompt += f"System: {system_prompt}\n\n"
            
            # Add messages in a conversational format
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    prompt += f"User: {content}\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n"
            
            # Add final prompt for the assistant to continue
            prompt += "Assistant: "
            
            # Debug: print the formatted prompt
            print(f"Debug - Formatted prompt sent to HuggingFace:\n{prompt[:200]}...")
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add Authorization header if API key is provided
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Create the API request payload - use only text string
            payload = {
                "inputs": prompt
            }
            
            # Debug info
            print(f"Sending request to HuggingFace API for model {self.model_id}...")
            print(f"Payload format: inputs is a {type(payload['inputs']).__name__}")
            
            # Make the API request
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout since free tier can take time
            )
            
            # Debug info
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                
                # Debug the response structure
                print(f"Response type: {type(response_json).__name__}")
                if isinstance(response_json, list):
                    print(f"Response is a list with {len(response_json)} items")
                
                # Extract the generated text from the response
                if isinstance(response_json, list) and len(response_json) > 0:
                    if "generated_text" in response_json[0]:
                        return response_json[0]["generated_text"]
                elif isinstance(response_json, dict):
                    if "generated_text" in response_json:
                        return response_json["generated_text"]
                
                # Try to extract the response as a simple string
                if isinstance(response_json, str):
                    return response_json
                elif isinstance(response_json, list) and len(response_json) > 0:
                    if isinstance(response_json[0], str):
                        return response_json[0]
                
                # Last resort: convert the entire response to a string
                return str(response_json)
                
            else:
                # Handle API error with more details
                error_detail = "Unknown error"
                error_message = f"Sorry, I couldn't process your request. API error: {response.status_code}"
                
                try:
                    error_json = response.json()
                    error_detail = json.dumps(error_json, indent=2)
                    
                    # Check for model loading message
                    if "estimated_time" in response.text:
                        error_data = response.json()
                        wait_time = error_data.get("estimated_time", "unknown")
                        error_message = f"I'm still warming up. The model is being loaded and will be ready in approximately {wait_time} seconds. Please try again shortly."
                except:
                    error_detail = response.text
                
                print(f"API Error Details: {error_detail}")
                return error_message
                
        except Exception as e:
            # If something goes wrong, provide a fallback response
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Exception: {str(e)}\n{traceback_str}")
            
            return f"I apologize, but I encountered an error when trying to process your query: {str(e)}" 