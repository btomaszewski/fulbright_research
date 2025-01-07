import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import json
import shutil

MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']

PROMPT_PART_1 = "Translate this text to English <start> " 
PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. "
PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

# Load environment variables from the .env file
load_dotenv()
# Access the API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key)

# for each file within rawJson directory
    # get fileName
    # outputFile = fileName + "Translated.csv"
rawJsonDir = Path("./rawJson")


for rawJsonFile in rawJsonDir.iterdir():
    if rawJsonFile.is_file():
        print(f"Found file: {rawJsonFile.name}")
        outputFile = rawJsonFile.stem + "Translated.json"
        print(outputFile)

        source = "./" + rawJsonDir.name + "/" + rawJsonFile.name
        destination = "./translatedJson/" + outputFile
        shutil.copy(source, destination)

        with open(rawJsonDir.name + "/" + rawJsonFile.name, encoding='utf-8') as f:
            json_data = json.load(f)
            #get messages array from JSON
            message_data = json_data["messages"]
            
            #loop through the individual messages
            for individual_message in message_data:
                #only process messages of type 'message' (for now)
                if (individual_message["type"] == "message"):
                    #get the plain text message from the current message
                    current_text = individual_message["text_entities"]
                    #only go forward with text messages
                    #TODO - process pictures/audio/video
                    if (len(current_text) > 0): 
                        
                        message_text = current_text[0]["text"] # [text index][text key]
                        completion = client.chat.completions.create(
                            model="gpt-4o",
                            store=True,
                            messages=[
                                {"role": "user", "content": PROMPT_PART_1 + message_text + PROMPT_PART_2 + PROMPT_PART_3}
                            ]
                    )
                    final_result = completion.choices[0].message.content # str

                    try:
                        result_JSON = json.loads(final_result)
                        aiDetectedLang = result_JSON["language"]
                        aiTranslation = result_JSON["translation"]
                        # print(aiTranslation, aiDetectedLang)
                        individual_message['LANGUAGE'] = aiDetectedLang
                        individual_message['MESSAGE_ENG'] = aiTranslation

                        with open(destination, "w", encoding="utf-8") as f:
                            json.dump(json_data, f, ensure_ascii=False, indent=4)
                        
                    #json.decoder.JSONDecodeError
                    except Exception as inst:
                        print("***translation and/or formatting error")
                        continue
                    