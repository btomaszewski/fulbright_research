import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
def loadAI():
    # Explicitly load environment variables
    load_dotenv()
    
    # First try to get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    # If not found, try to access it directly from process.env passed by Electron
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        
    client = OpenAI(api_key=api_key)
    return client 