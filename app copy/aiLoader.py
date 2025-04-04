import os
from openai import OpenAI
import logging

# Set up logging
logger = logging.getLogger("json-processor-api")

# Global client variable
_client = None

def loadAI():
    """
    Load and initialize OpenAI client
    """
    global _client
    
    # If we've already initialized a client, return it
    if _client is not None:
        return _client
    
    try:
        # Initialize OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Try different initialization methods
        try:
            # Method for newer OpenAI library versions
            _client = OpenAI(api_key=api_key)
        except TypeError:
            # Fallback for older OpenAI library versions
            _client = OpenAI()
            _client.api_key = api_key
            
        return _client
        
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        raise