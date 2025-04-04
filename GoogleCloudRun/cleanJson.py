import json
import shutil

# Step 1: Filter messages
def filterMessages(jsonData):
    for message in jsonData["messages"]:
        if message.get("text") == "/n":
            message["text"] = None
        if message.get('reactions'):
            del message['reactions']
    return jsonData

def modifyIds(jsonData):
    resultId = str(jsonData["id"])
    resultId = resultId + "-"
    for message in jsonData["messages"]:
        messageId = str(message['id'])
        newId = resultId + messageId
        message['id'] = newId
    return jsonData

# Step 3: Process text entities
def processTextEntities(jsonData):
    for message in jsonData["messages"]:
        textEntities = message.get("text_entities", [])
        fullText = ""
        for entity in textEntities:
            if "text" in entity:
                fullText += entity['text']
        if fullText:
            message['text'] = fullText
        else:
            message.pop('text', None)  # Safely remove 'text' if it doesn't exist
        message.pop('text_entities', None)  # Safely remove 'text_entities'
    return jsonData

def cleanJson(resultJson):
    with open(resultJson, 'r', encoding='utf-8') as f:
        jsonData = json.load(f)

        jsonData = filterMessages(jsonData)
        jsonData = processTextEntities(jsonData)
        jsonData = modifyIds(jsonData)

    with open(resultJson, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, ensure_ascii=False, indent=4)