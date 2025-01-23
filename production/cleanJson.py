import json
import shutil

file = "../testCode&Data/data/cleanJsonTestChat/result.json"

cleanFile = "../testCode&Data/data/cleanJsonTestChat/cleanResult.json"

shutil.copy(file, cleanFile)

messageData = []

with open(cleanFile, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", []) # Create array of message data


for message in messageData:
    # del(message['text'])
    
    textEntities = message.get("text_entities", [])
    fullText = ""
    textTypes = {"plain", "bold", "italic", "hashtag"}
    for entity in textEntities:
        if "text" in entity:
            fullText += entity['text']
    if fullText:
        message['text'] = fullText
    else:
        del(message['text'])
    del(message['text_entities'])

# combine videos/photos into one message

# Write messages to destination file
with open(cleanFile, 'w', encoding='utf-8') as f:
    json.dump(jsonData, f, ensure_ascii=False, indent=4)

