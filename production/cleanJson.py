import json
import shutil

# Step 1: Filter messages
def filter_messages(jsonData):
    for message in jsonData["messages"]:
        if message.get("text") == "/n":
            message["text"] = None

# Step 2: Modify reply IDs
def modify_replies(jsonData):
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
def process_text_entities(jsonData):
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

def main():
    # File paths
    file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/testCode&Data/data/cleanJsonTestChat/result.json"
    cleanFile = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/testCode&Data/data/cleanJsonTestChat/cleanResult.json"

    # Copy the original file to the clean file
    shutil.copy(file, cleanFile)

    # Load the JSON data
    with open(cleanFile, 'r', encoding='utf-8') as f:
        jsonData = json.load(f)

    # Call each function sequentially
    filter_messages(jsonData)
    modify_replies(jsonData)
    process_text_entities(jsonData)

    # Write the cleaned data back to the file
    with open(cleanFile, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, ensure_ascii=False, indent=4)

    print(f"Processed and saved the cleaned data to {cleanFile}")

# Entry point
if __name__ == "__main__":
    main()


