import os
import shutil
import json
from pathlib import Path
from frameExtraction import extractFrames
from videoAnalysis import summarize
from imageAnalysis import analyzeImage
from aiLoader import loadAI
from helpers import translate, transcribe
#from thematicAnalysis import writeThemes

client = loadAI()

cleanFile = "../testCode&Data/data/cleanJsonTestChat/cleanResult.json"

# Define the static system prompt
system_prompt = {
    "role": "system",
    "content": "You are a translator. Translate the given text to English. Return back two things. The first is your translation to English of text. The second is a one word description of the language of text. Put the two items you return into a JSON structure. Your translation to English of text placed inside a JSON tag named translation. Your one word description of the language of inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."
}
prompts = [system_prompt]

texts_to_analyze = []
messageData = []

with open(cleanFile, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", [])

# Simulate sending multiple queries
for message in messageData:
    if message.get('text'):
        texts_to_analyze.append(message['text'])

for text in texts_to_analyze:
    # Add the new user query
    new_user_prompt = {"role": "user", "content": f"Analyze this text: {text}"}
    prompts.append(new_user_prompt)
    
    # Call the OpenAI API
    completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=prompts
    )

    response = (completion.choices[0].message.content)
    
    # Add the model's response to the conversation
    assistant_prompt = {"role": "assistant", "content": response}
    prompts.append(assistant_prompt)
    
    # Optionally truncate older messages
    if len(prompts) > 10:
       prompts = [system_prompt] + prompts[-10:]

print(prompts)
