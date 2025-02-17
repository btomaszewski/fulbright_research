import os
import shutil
import json
import sys
from pathlib import Path
from frameExtraction import extractFrames
from videoAnalysis import summarize
from imageAnalysis import analyzePhoto
from aiLoader import loadAI
from helpers import translate, transcribe
from cleanJson import cleanJson
from vectorImplementation import categorize


client = loadAI()

# Paths
rawJsonDir = Path("./rawJson")
processedJsonDir = Path("./processedJson")
processedJsonDir.mkdir(exist_ok=True)
currentDir = os.path.dirname(os.path.abspath(__file__)) # currentDir = production

# Batch Processing Functions

def batch_translate(texts, batch_size=10):
    """Process text translations in batches"""
    results = {}
    
    # Process texts in batches
    for i in range(0, len(texts), batch_size):
        batch = list(texts.items())[i:i + batch_size]
        batch_inputs = [text for _, text in batch]
        
        # Call translate function in batch
        batch_results = []
        for text in batch_inputs:
            batch_results.append(translate(text))
        
        # Map results back to message IDs
        for j, (msg_id, _) in enumerate(batch):
            results[msg_id] = batch_results[j]
    
    return results

def batch_categorize(texts, batch_size=10):
    """Process text categorizations in batches"""
    results = {}
    
    # Process texts in batches
    for i in range(0, len(texts), batch_size):
        batch = list(texts.items())[i:i + batch_size]
        batch_inputs = [text for _, text in batch]
        
        # Call categorize function in batch
        batch_results = []
        for text in batch_inputs:
            batch_results.append(categorize(text))
        
        # Map results back to message IDs
        for j, (msg_id, _) in enumerate(batch):
            results[msg_id] = batch_results[j]
    
    return results

# The processing functions remain largely the same but will be called with batched results

def processText(individualMessage, translation_result):
    if translation_result:
        individualMessage['LANGUAGE'] = translation_result.get("language", "unknown")
        individualMessage['TRANSLATED_TEXT'] = translation_result.get("translation", "")

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

def processCategories(individualMessage, category_result):
    if category_result:
        individualMessage['CATEGORIES'] = category_result

def processJson(messageData, processedDirPath):
    # Collect data for batch processing
    text_batch = {}
    video_messages = []
    photo_messages = []
    categorize_batch = {}
    
    # First pass: collect data for batch processing
    for individualMessage in messageData[:]:  # Copy the list to iterate safely
        if individualMessage.get("type") == "service":  # Remove "service" messages
            messageData.remove(individualMessage)
            continue
        
        msg_id = individualMessage.get("id", str(id(individualMessage)))  # Use unique identifier
        
        # Collect texts for batch translation
        text = individualMessage.get("text")
        if text:
            text_batch[msg_id] = text
        
        # Collect videos for processing (these are processed individually because of file operations)
        video = individualMessage.get("file")
        if video and video != "(File exceeds maximum size. Change data exporting settings to download.)":
            video_path = (f"{processedDirPath}/{video}").replace("\\", "/")
            video_messages.append((individualMessage, video_path))
        
        # Collect photos for analysis (could be batched if analyzePhoto supports it)
        photo = individualMessage.get("photo")
        if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
            photo_path = (f"{processedDirPath}/{photo}").replace("\\", "/")
            photo_messages.append((individualMessage, photo_path))
    
    # Batch process translations
    if text_batch:
        translation_results = batch_translate(text_batch)
        for msg_id, result in translation_results.items():
            for message in messageData:
                if message.get("id") == msg_id or str(id(message)) == msg_id:
                    processText(message, result)
    
    # Process videos (not batched due to file operations)
    for message, video_path in video_messages:
        processVideo(message, video_path)
    
    # Process photos (not batched if analyzePhoto doesn't support it)
    for message, photo_path in photo_messages:
        processImage(message, photo_path)
    
    # Second pass: collect full text for categorization
    for individualMessage in messageData:
        msg_id = individualMessage.get("id", str(id(individualMessage)))
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
            categorize_batch[msg_id] = fullText
    
    # Batch process categorizations
    if categorize_batch:
        category_results = batch_categorize(categorize_batch)
        for msg_id, result in category_results.items():
            for message in messageData:
                if message.get("id") == msg_id or str(id(message)) == msg_id:
                    processCategories(message, result)


def main(rawChatPath, procJsonPath):
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
        
'''
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
    categories = categorize(fullText)
    if categories:
        individualMessage['CATEGORIES'] = categories

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
'''