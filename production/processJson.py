import os
import json
import shutil
from pathlib import Path
from frameExtraction import extractFrames
from videoAnalysis import summarize
from imageAnalysis import analyzeImage
from aiLoader import loadAI
from helpers import translate, transcribe

client = loadAI()

# Paths
rawJsonDir = Path("./rawJson")
processedJsonDir = Path("./processedJson")
processedJsonDir.mkdir(exist_ok=True)
currentDir = os.path.dirname(os.path.abspath(__file__)) # currentDir = production

filesToProcess = set()

# Helper Functions

# Takes a message Json object, loops through all text_entities for that message, calls translate() on text, and places the language/translation in processed Json file. 
def processTextEntities(text_entities):
    textTypes = {"plain", "bold", "italic", "hashtag"} #add any text types to be translated to this set
    for entity in text_entities:
        if "text" in entity and len(entity['text']) > 3 and entity["type"] in textTypes: #filters out non-text entities
            result_JSON = translate(entity["text"])
            entity['LANGUAGE'] = result_JSON.get("language", "unknown")
            entity['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
# Takes a message Json object and the directory containing all data for the exported chat, converts file to .mp4 if necessary, returns AI generated transcription. 

def processVideo(individualMessage, video):
    # Get video transcription
    transcription = transcribe(video)
    if transcription:
        individualMessage['VIDEO_TRANSCRIPTION'] = transcription
        transcriptionTranslation = translate(transcription)
        individualMessage['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation

    # Extract frames
    extractFrames(video, currentDir)

    # Perform analysis of video frames
    summary = summarize()
    if summary:
        individualMessage['VIDEO_SUMMARY'] = summary

def processImage(individualMessage, photo):
    analysis = analyzeImage(photo)
    if analysis:
        individualMessage['PHOTO_ANALYSIS'] = analysis

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

                            # Complete all processing on each message: translate text_entities, analyze/transcribe video, analyze images
                            for individualMessage in messageData: # Loop through messages
                                if individualMessage.get("type") == "service": # Remove "service" messages from destination file
                                    messageData.remove(individualMessage)

                                print(f"Processing message id: {individualMessage.get('id')}")

                                text_entities = individualMessage.get("text_entities", [])
                                if text_entities:
                                    processTextEntities(text_entities)

                                video = individualMessage.get("file")
                                if video and video != "(File exceeds maximum size. Change data exporting settings to download.)":
                                    video = (f"{chatExportDir}/{video}").replace("\\", "/")
                                    processVideo(individualMessage, video)

                                photo = individualMessage.get("photo")
                                if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
                                    photo = (f"{chatExportDir}/{photo}").replace("\\", "/")
                                    processImage(individualMessage, photo)

                                        
                            # Write messages to destination file
                            with open(destination, 'w', encoding='utf-8') as f:
                                json.dump(jsonData, f, ensure_ascii=False, indent=4)

                            print(f"Translation completed for {rawJsonFile.name}, output saved to {outputFile}")
                
main()