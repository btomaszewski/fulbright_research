import os
import json
import shutil
import time
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Constants
MESSAGE_DOCUMENTATION_FIELDS = ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR', 'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME', 'MESSAGE_SOURCE_LANGUAGE', 'MESSAGE_DETECTED_LANGUAGE', 'MESSAGE_TRANSLATED_ENG']
PROMPT_PART_1 = "Translate this text to English <start> " 
PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. "
PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

# Load environment variables from the .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key)

# Paths
rawJsonDir = Path("./rawJson")
translatedJsonDir = Path("./translatedJson")
translatedJsonDir.mkdir(exist_ok=True)

files_to_process = set()

# Scan for all files in directory and add to set
while True:
    # List all files in the directory
    for rawJsonFile in rawJsonDir.iterdir():
        if rawJsonFile.is_file() and rawJsonFile.name not in files_to_process:
            print(f"Processing file: {rawJsonFile.name}")
            files_to_process.add(rawJsonFile.name)
            # Process files
            if rawJsonFile.is_file():
                print(f"Processing file: {rawJsonFile.name}")
                outputFile = rawJsonFile.stem + "Translated.json"
                destination = translatedJsonDir / outputFile

                # Copy raw JSON file to the destination directory
                shutil.copy(rawJsonFile, destination)

                with open(destination, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    message_data = json_data.get("messages", []) # Create array of message data
                    for individual_message in message_data: # Loop through messages
                        if individual_message.get("type") == "service": # Remove "service" messages from destination file
                            message_data.remove(individual_message)

                    # Translate text entities
                    for individual_message in message_data: # Loop through messages
                        print(individual_message.get('id'))
                        text_entities = individual_message.get("text_entities", [])
                        for entity in text_entities:
                            if "text" in entity and entity["text"] and (entity["type"] == "plain" or entity["type"] == "bold"):
                                try:
                                    completion = client.chat.completions.create(
                                        model="gpt-4o",
                                        store=True,
                                        messages=[
                                            {"role": "user", "content": PROMPT_PART_1 + entity["text"] + PROMPT_PART_2 + PROMPT_PART_3}
                                        ]
                                    )
                                    result_JSON = json.loads(completion.choices[0].message.content)
                                    entity['LANGUAGE'] = result_JSON.get("language", "unknown")
                                    entity['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
                                except Exception as e:
                                    print(f"Error translating text entity {individual_message.get('id')}:", e)

                                # Write messages to destination file
                    with open(destination, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=4)

                    print(f"Translation completed for {rawJsonFile.name}, output saved to {outputFile}")
            
    # Wait before re-scanning the directory for new files
    time.sleep(1)