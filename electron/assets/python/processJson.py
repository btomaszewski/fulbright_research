import os
import shutil
import json
import sys
from pathlib import Path
from assets.frameExtraction import extractFrames
from assets.videoAnalysis import summarize
from assets.imageAnalysis import analyzePhoto
from assets.aiLoader import loadAI
from assets.helpers import translate, transcribe
from assets.cleanJson import cleanJson
from assets.vectorImplementation import categorize


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
    categoriesObj = categorize(fullText)
    if categoriesObj:
        individualMessage['CATEGORIES'] = categoriesObj['categories']
        individualMessage['CONFIDENCE'] = categoriesObj['confidence_scores']

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

def main(rawChatPath, procJsonPath):

    # Configure batch size
    BATCH_SIZE = 50  # Adjust this number based on your needs
    
    # Process files
    chatDir = os.path.basename(rawChatPath)
    chatDir = f"{chatDir}Processed"
    processedDirPath = os.path.join(procJsonPath, chatDir)
    shutil.copytree(rawChatPath, processedDirPath)
    
    resultJson = Path(processedDirPath) / "result.json"
    if resultJson.is_file():
        try:
            cleanJson(resultJson)
            print(f"{resultJson} cleaned successfully")
        except Exception as e:
            print(f"Could not clean {resultJson}", e)

        print(f"Processing file: {resultJson.name}")
        with open(resultJson, 'r', encoding='utf-8') as f:
            jsonData = json.load(f)
            messageData = jsonData.get("messages", [])
            
            # Remove service messages first (as in your original code)
            messageData = [msg for msg in messageData if msg.get("type") != "service"]
            
            # Process messages in batches
            for i in range(0, len(messageData), BATCH_SIZE):
                batch = messageData[i:i + BATCH_SIZE]
                print(f"Processing batch {i//BATCH_SIZE + 1} of {(len(messageData) + BATCH_SIZE - 1)//BATCH_SIZE}")
                
                for individualMessage in batch:
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

                    fullText = ""
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
            
            # Update the messages in the original JSON
            jsonData["messages"] = messageData
                        
        # Write final result to the destination file
        with open(resultJson, 'w', encoding='utf-8') as f:
            json.dump(jsonData, f, ensure_ascii=False, indent=4)
    
        print(f"Processing completed for {resultJson}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Error: No directory path provided.") 