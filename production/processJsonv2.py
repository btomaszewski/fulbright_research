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
    "content": "You are a translator. Translate the given text to English. Return back two things. The first is your translation to English of text. The second is a one word description of the language of text. Put the two items you return into a JSON structure. Your translation to English of text placed inside a JSON tag named translation. Your one word description of the language of inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters. Do not include excape characters or new lines"
}
prompts = [system_prompt]
ids = [None]
responses = [None]

texts = []
messageData = []

with open(cleanFile, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", [])

# Simulate sending multiple queries
for message in messageData:
    if message.get('text'):
        texts.append(message['text'])
        ids.append(message['id'])


for text in texts:
    # Add the new user query
    new_user_prompt = {"role": "user", "content": f"{text}"}
    prompts.append(new_user_prompt)
    
    # Call the OpenAI API
    completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=prompts
    )

    response = (completion.choices[0].message.content)
    print(response)
    
    # Add the model's response to the conversation
    #assistant_prompt = {"role": "assistant", "content": response}
    responses.append(response)
    
    
for message in messageData:
    id = message.get('id')
    if id in ids:
        i = ids.index(id)
        response = responses[i]

        message['TRANSLATION'] = json.loads(response)

# Write messages to destination file
with open(cleanFile, 'w', encoding='utf-8') as f:
    json.dump(jsonData, f, ensure_ascii=False, indent=4)
