import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access the API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

client = OpenAI(api_key=api_key)

completion = client.chat.completions.create(
    model="gpt-4o",
    store=True,
    messages=[
        {"role": "user", "content": "write a haiku about ai"}
    ]
)

print(completion.choices[0].message) 