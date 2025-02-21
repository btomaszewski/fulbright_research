import os
import shutil
import json
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frameExtraction import extractFrames
from videoAnalysis import summarize
from imageAnalysis import analyzePhoto
from aiLoader import loadAI
from helpers import translate, transcribe
from cleanJson import cleanJson
from vectorImplementation import categorize
from nerImplementation import getLocations


client = loadAI()

# Paths
rawJsonDir = Path("./rawJson")
processedJsonDir = Path("./processedJson")
processedJsonDir.mkdir(exist_ok=True)
currentDir = os.path.dirname(os.path.abspath(__file__)) # currentDir = production

# Helper Functions

# Takes a message Json object, loops through all text_entities for that message, calls translate() on text, and places the language/translation in processed Json file. 
def processText(individualMessage, text):
    result_JSON = translate(text)
    if result_JSON:
        individualMessage['LANGUAGE'] = result_JSON.get("language", "unknown")
        individualMessage['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
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
    summary = summarize(framesDir)
    if summary:
        individualMessage['VIDEO_SUMMARY'] = summary

    # Delete frames dir
    shutil.rmtree(framesDir)

def processImage(individualMessage, photo):
    analysis = analyzePhoto(photo)
    if analysis:
        individualMessage['PHOTO_ANALYSIS'] = analysis

def processCategories(individualMessage, fullText):
    categories = categorize(fullText)
    if categories:
        individualMessage['CATEGORIES'] = categories

def processLocations(individualMessage, fullText):
    locations = getLocations(fullText)
    if locations:
        individualMessage['LOCATIONS'] = locations

def processJson(messageData, processedDirPath):
    # Complete all processing on each message: translate text_entities, analyze/transcribe video, analyze images
    for individualMessage in messageData: # Loop through messages
        if individualMessage.get("type") == "service": # Remove "service" messages from destination file
            messageData.remove(individualMessage)
        
        text = individualMessage.get("text")
        if text:
            processText(individualMessage, text)
        
        video = individualMessage.get("file")
        if video and video != "(File exceeds maximum size. Change data exporting settings to download.)":
            video = (f"{processedDirPath}/{video}").replace("\\", "/")
            processVideo(individualMessage, video)

        photo = individualMessage.get("photo")
        if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
            photo = (f"{processedDirPath}/{photo}").replace("\\", "/")
            processImage(individualMessage, photo)

        fullText = "";
        if individualMessage.get("TRANSLATED_TEXT"):
            fullText += individualMessage["TRANSLATED_TEXT"]

        if individualMessage.get("TRANSCRIPTION_TRANSLATION"):
            fullText += individualMessage["TRANSCRIPTION_TRANSLATION"]

        if individualMessage.get("VIDEO_SUMMARY"):
            fullText += individualMessage["VIDEO_SUMMARY"]

        if individualMessage.get("PHOTO_ANALYSIS"):
            fullText += individualMessage["PHOTO_ANALYSIS"]

        if fullText:
            processCategories(individualMessage, fullText)
            processLocations(individualMessage, fullText)


def main(rawChatPath, procJsonPath): # put all main() functionality in a while True: if we want it to automatically add new chatDirs to the set while processing
    # Process files
    chatDir = os.path.basename(rawChatPath)
    chatDir = f"{chatDir}Processed"
    processedDirPath = os.path.join(procJsonPath, chatDir)
    shutil.copytree(rawChatPath, processedDirPath)
    
    resultJson = Path(processedDirPath) / "result.json"  # Construct the path
    if resultJson.is_file():  # Check if result.json exists
        try:
            cleanJson(resultJson)
            print(f"{resultJson} cleaned successfully")
        except Exception as e:
            print(f"Could not clean {resultJson}", e)

        print(f"Processing file: {resultJson.name}")
        with open(resultJson, 'r', encoding='utf-8') as f:
            jsonData = json.load(f)
            messageData = jsonData.get("messages", []) # Create array of message data

            processJson(messageData, processedDirPath)
                        
        # Write messages to destination file
        with open(resultJson, 'w', encoding='utf-8') as f:
            json.dump(jsonData, f, ensure_ascii=False, indent=4)

        print(f"Processing completed for {resultJson}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Error: No directory path provided.")