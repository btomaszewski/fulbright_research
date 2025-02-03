import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
def loadAI():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
    client = OpenAI(api_key=api_key)
    return client