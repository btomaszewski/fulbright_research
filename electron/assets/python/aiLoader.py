import os
import sys
import certifi
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
def loadAI():
    # Explicitly load environment variables
    load_dotenv()
    
    # Set up SSL certificates for both PyInstaller bundle and development
    # This needs to be done ALWAYS (not just in PyInstaller mode)
    cert_path = certifi.where()
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    print(f"Using SSL certificates from: {cert_path}")
    
    # First try to get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    # If not found, try to access it directly from process.env passed by Electron
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        
    client = OpenAI(api_key=api_key)
    return client
