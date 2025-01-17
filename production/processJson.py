import os
import shutil
import json
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
    video = os.path.join(processedJsonDir, video)
    # Get video transcription
    transcription = transcribe(video)
    if transcription:
        individualMessage['VIDEO_TRANSCRIPTION'] = transcription
        transcriptionTranslation = translate(transcription)
        individualMessage['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation

    # Extract frames
    framesDir = video + "Frames"
    extractFrames(video, framesDir)

    # Perform analysis of video frames
    summary = summarize()
    if summary:
        individualMessage['VIDEO_SUMMARY'] = summary

    # Delete frames dir
    shutil.rmtree(framesDir)

def processImage(individualMessage, photo):
    analysis = analyzeImage(photo)
    if analysis:
        individualMessage['PHOTO_ANALYSIS'] = analysis

def processJson(messageData, chatDir):
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
            video = (f"{chatDir}/{video}").replace("\\", "/")
            processVideo(individualMessage, video)

        photo = individualMessage.get("photo")
        if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
            photo = (f"{chatDir}/{photo}").replace("\\", "/")
            processImage(individualMessage, photo)


chatsToProcess = set()

def main(): # put all main() functionality in a while True: if we want it to automatically add new chatDirs to the set while processing
    # Scan for all files in directory and add to set
    for chatExportDir in rawJsonDir.iterdir():
        if chatExportDir.is_dir() and chatExportDir.name not in chatsToProcess:
            chatsToProcess.add(chatExportDir.name)
            print(chatsToProcess)

    # Process files
    for chatDir in chatsToProcess:
        chatDirPath = os.path.join(rawJsonDir, chatDir)
        chatDir = f"{chatDir}Processed"
        processedDirPath = os.path.join(processedJsonDir, chatDir)
        shutil.copytree(chatDirPath, processedDirPath)
        
        resultJson = Path(processedDirPath) / "result.json"  # Construct the path
        print(resultJson)
        if resultJson.is_file():  # Check if result.json exists
            print(f"Processing file: {resultJson.name}")

            with open(resultJson, 'r', encoding='utf-8') as f:
                jsonData = json.load(f)
                messageData = jsonData.get("messages", []) # Create array of message data

                processJson(messageData, chatDir)
                            
            # Write messages to destination file
            with open(resultJson, 'w', encoding='utf-8') as f:
                json.dump(jsonData, f, ensure_ascii=False, indent=4)

            print(f"Translation completed for {resultJson}")

main()