import json
import shutil

# Step 1: Filter messages
def filterMessages(jsonData):
    for message in jsonData["messages"]:
        if message.get("text") == "/n":
            message["text"] = None
        if message.get('reactions'):
            del message['reactions']

# Step 2: Modify reply IDs
def modifyReplies(jsonData):
    incrementing_value = 100
    for message in jsonData["messages"]:
        if "reply_to_message_id" in message:
            # Update 'id' to the value of 'reply_to_message_id'
            message["id"] = message["reply_to_message_id"]

            # Rename 'reply_to_message_id' to 'reply_id' with the new incremented value
            message["reply_id"] = incrementing_value
            incrementing_value += 1

            # Remove the old 'reply_to_message_id' field
            del message["reply_to_message_id"]

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

def cleanJson(resultJson):
    with open(resultJson, 'r', encoding='utf-8') as f:
        jsonData = json.load(f)

        # Call each function sequentially
        print(f"Cleaning file {resultJson}")
        filterMessages(jsonData)
        modifyReplies(jsonData)
        processTextEntities(jsonData)

    with open(resultJson, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, ensure_ascii=False, indent=4)