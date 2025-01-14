import os
import json
import shutil
import ffmpeg
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Constants
MESSAGE_DOCUMENTATION_FIELDS = ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR', 'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME', 'MESSAGE_SOURCE_LANGUAGE', 'MESSAGE_DETECTED_LANGUAGE', 'MESSAGE_TRANSLATED_ENG']
PROMPT_PART_1 = "Translate this text to English <start> " 
PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. If the text between the <start> and <end> tags is only whitespace, escape characters, or non-alphanumeric characters, as in not real words, return an empty string for both the translation and the description."
PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

# Load environment variables from the .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key)

# Paths
rawJsonDir = Path("./rawJson")
processedJsonDir = Path("./processedJson")
processedJsonDir.mkdir(exist_ok=True)

filesToProcess = set()

def translate(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + text + PROMPT_PART_2 + PROMPT_PART_3}
            ]
        )
        return json.loads(completion.choices[0].message.content)

    except Exception as e:
        print(f"Error translating text.", e)
        return None

def translateTextEntities(individualMessage):
    text_entities = individualMessage.get("text_entities", [])
    for entity in text_entities:
        if "text" in entity and len(entity['text']) > 3 and (entity["type"] == "plain" or entity["type"] == "bold" or entity["type"] == "italic" or entity["type"] == "hashtag"):
            result_JSON = translate(entity["text"])
            entity['LANGUAGE'] = result_JSON.get("language", "unknown")
            entity['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
    
def transcribe(individualMessage, chatExportDir):
    file = individualMessage.get("file")
    print(file)

    if file and file != "(File exceeds maximum size. Change data exporting settings to download.)":
        fExtension = os.path.splitext(file)[1]
        outputFile = (f"{chatExportDir}/{file}").replace("\\", "/")
        if fExtension == ".MOV" or fExtension == ".mov":
            # Input and output file paths
            inputFile = (f"{chatExportDir}/{file}").replace("\\", "/")
            stem = os.path.splitext(file)[0]
            outputFile = (f"{chatExportDir}/{stem}.mp4").replace("\\", "/")

            try:
                # Convert MOV to MP4
                ffmpeg.input(inputFile).output(outputFile, vcodec="h264", acodec="aac").run()
                print(f"Conversion complete: {outputFile}")

            except Exception as e:
                    print("Error converting file to .mp4", e)

        try:
            audio_file= open(outputFile, "rb")
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
            return transcription

        except Exception as e:
            print("Error transcribing audio", e)
            return None

def main():
    # Scan for all files in directory and add to set
    while True:
        # List all files in the directory
        for chatExportDir in rawJsonDir.iterdir():
            for rawJsonFile in chatExportDir.iterdir():
                if rawJsonFile.is_file() and rawJsonFile.name not in filesToProcess:
                    filesToProcess.add(rawJsonFile.name)
                    # Process files
                    if rawJsonFile.is_file():
                        print(f"Processing file: {rawJsonFile.name}")
                        outputFile = rawJsonFile.stem + "Processed.json"
                        destination = processedJsonDir / outputFile

                        # Copy raw JSON file to the destination directory
                        shutil.copy(rawJsonFile, destination)

                        with open(destination, 'r', encoding='utf-8') as f:
                            jsonData = json.load(f)
                            messageData = jsonData.get("messages", []) # Create array of message data
                            for individualMessage in messageData: # Loop through messages
                                if individualMessage.get("type") == "service": # Remove "service" messages from destination file
                                    messageData.remove(individualMessage)

                            # Complete all processing on each message: translate text_entities, transcribe audio/video
                            for individualMessage in messageData: # Loop through messages
                                print(individualMessage.get('id'))

                                translateTextEntities(individualMessage)

                                transcription = transcribe(individualMessage, chatExportDir)
                                print(transcription)
                                individualMessage['VIDEO_TRANSCRIPTION'] = transcription

                                if transcription:
                                    transcriptionTranslation = translate(transcription)
                                    print(transcriptionTranslation)
                                    individualMessage['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation

                            # Write messages to destination file
                            with open(destination, 'w', encoding='utf-8') as f:
                                json.dump(jsonData, f, ensure_ascii=False, indent=4)

                            print(f"Translation completed for {rawJsonFile.name}, output saved to {outputFile}")
                
main()