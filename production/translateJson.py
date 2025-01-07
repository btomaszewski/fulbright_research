import os
import json
import shutil
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

# Process files
for rawJsonFile in rawJsonDir.iterdir():
    if rawJsonFile.is_file():
        print(f"Processing file: {rawJsonFile.name}")
        outputFile = rawJsonFile.stem + "Translated.json"
        destination = translatedJsonDir / outputFile

        # Copy raw JSON file to the destination directory
        shutil.copy(rawJsonFile, destination)

        with open(rawJsonFile, encoding='utf-8') as f:
            json_data = json.load(f)
            message_data = json_data.get("messages", [])

            # Loop through messages
            for individual_message in message_data:
                # Process only messages of type 'message'
                if individual_message.get("type") == "message":
                    # Translate main text (if applicable)
                    if "text" in individual_message and individual_message["text"]:
                        main_text = individual_message['text'][1]['text']
                        
                        try:
                            completion = client.chat.completions.create(
                                model="gpt-4o",
                                store=True,
                                messages=[
                                    {"role": "user", "content": PROMPT_PART_1 + main_text + PROMPT_PART_2 + PROMPT_PART_3}
                                ]
                            )
                            result_JSON = json.loads(completion.choices[0].message.content)
                            individual_message["text"][1]['LANGUAGE'] = result_JSON.get("language", "unknown")
                            individual_message["text"][1]['MESSAGE_ENG'] = result_JSON.get("translation", "")
                        except Exception as e:
                            print("Error translating main text:", e)

                    # Translate text entities
                    text_entities = individual_message.get("text_entities", [])
                    for entity in text_entities:
                        if "text" in entity and entity["text"]:
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
                                print("Error translating text entity:", e)

            # Save the updated JSON data
            with open(destination, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)

        print(f"Translation completed for {rawJsonFile.name}, output saved to {outputFile}")