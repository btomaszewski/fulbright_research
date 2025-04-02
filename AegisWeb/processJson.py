import os
import shutil
import json
import sys
import traceback
from pathlib import Path
import logging


# Try to add parent directory to path, but with error handling
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

# Try to import each module individually with error handling
try:
    from frameExtraction import extractFrames
    print("Successfully imported frameExtraction")
except ImportError as e:
    print(f"Failed to import frameExtraction: {e}")
    
try:
    from videoAnalysis import summarize
    print("Successfully imported videoAnalysis")
except ImportError as e:
    print(f"Failed to import videoAnalysis: {e}")
    
try:
    from imageAnalysis import analyzePhoto
    print("Successfully imported imageAnalysis")
except ImportError as e:
    print(f"Failed to import imageAnalysis: {e}")
    
try:
    from aiLoader import loadAI
    print("Successfully imported aiLoader")
except ImportError as e:
    print(f"Failed to import aiLoader: {e}")
    
try:
    from helpers import translate, transcribe
    print("Successfully imported helpers")
except ImportError as e:
    print(f"Failed to import helpers: {e}")
    
try:
    from cleanJson import cleanJson
    print("Successfully imported cleanJson")
except ImportError as e:
    print(f"Failed to import cleanJson: {e}")
    
try:
    from vectorImplementation import categorize
    print("Successfully imported vectorImplementation")
except ImportError as e:
    print(f"Failed to import vectorImplementation: {e}")
    
    
try:
    from nerImplementation import getLocations
    print("Successfully imported nerImplementation")
except ImportError as e:
    print(f"Failed to import nerImplementation: {e}")


# Log before AI client initialization
try:
    client = loadAI()
    print("AI client initialized successfully")
except Exception as e:
    print(f"Failed to initialize AI client: {e}")
    print(traceback.format_exc())

# Helper Functions
def processText(individualMessage, text):
    print(f"Processing text: {text[:50]}...")
    try:
        result_JSON = translate(text)
        if result_JSON:
            individualMessage['LANGUAGE'] = result_JSON.get("language", "unknown")
            individualMessage['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
            print(f"Text processed successfully. Detected language: {result_JSON.get('language', 'unknown')}")
        else:
            print("Translation returned None")
    except Exception as e:
        print(f"Error in processText: {e}")
        print(traceback.format_exc())

def processVideo(individualMessage, video):
    print(f"Processing video: {video}")
    try:
        print(f"Full video path: {video}")
        
        # Get video transcription
        print("Starting transcription")
        transcription = transcribe(video)
        if transcription:
            individualMessage['VIDEO_TRANSCRIPTION'] = transcription
            print(f"Transcription successful: {transcription[:50]}...")
            
            print("Starting transcription translation")
            transcriptionTranslation = translate(transcription)
            individualMessage['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation
            print("Translation complete")

        # Extract frames
        framesDir = video + "Frames"
        print(f"Extracting frames to: {framesDir}")
        extractFrames(video, framesDir)
        print("Frame extraction complete")

        # Perform analysis of video frames
        print("Starting video frame analysis")
        summary = summarize(framesDir)
        if summary:
            individualMessage['VIDEO_SUMMARY'] = summary
            print(f"Video analysis complete: {summary[:50]}...")

        # Delete frames dir
        print(f"Removing frames directory: {framesDir}")
        shutil.rmtree(framesDir)
        print("Frames directory removed")
    except Exception as e:
        print(f"Error in processVideo: {e}")
        print(traceback.format_exc())

def processImage(individualMessage, photo):
    print(f"Processing image: {photo}")
    try:
        analysis = analyzePhoto(photo)
        if analysis:
            individualMessage['PHOTO_ANALYSIS'] = analysis
            print(f"Image analysis complete: {analysis[:50]}...")
        else:
            print("Image analysis returned None")
    except Exception as e:
        print(f"Error in processImage: {e}")
        print(traceback.format_exc())

def processCategories(individualMessage, fullText):
    print(f"Processing categories for text: {fullText[:50]}...")
    try:
        categories = categorize(fullText)
        if categories:
            individualMessage['CATEGORIES'] = categories
            print(f"Categories assigned: {categories}")
        else:
            print("Category processing returned None")
    except Exception as e:
        print(f"Error in processCategories: {e}")
        print(traceback.format_exc())


def processLocations(individualMessage, fullText):
    print(f"Processing locations for text: {fullText[:50]}...")
    try:
        locations = getLocations(fullText)
        if locations:
            individualMessage['LOCATIONS'] = locations
            print(f"Locations found: {locations}")
        else:
            print("Location processing returned None")
    except Exception as e:
        print(f"Error in processLocations: {e}")
        print(traceback.format_exc())


def processJson(datasetPath):
    resultJson = Path(datasetPath)/"result.json"
    if resultJson.is_file():
        try:
            cleanJson(resultJson)
        except Exception as e:
            print("Error cleaning json:", e)

        try:
            with open(resultJson, 'r', encoding='utf-8') as f:
                jsonData = json.load(f)
                messageData = jsonData.get("messages", [])
        except Exception as e:
            print("Error getting message data:", e)

        print(f"Processing JSON with {len(messageData)} messages")
        try:
            # Now process each message
            for i, individualMessage in enumerate(messageData):
                print(f"Processing message {i+1}/{len(messageData)}")
                
                text = individualMessage.get("text")
                if text:
                    print("Message contains text")
                    processText(individualMessage, text)
                
                video = individualMessage.get("file")
                if video and video != "(File exceeds maximum size. Change data exporting settings to download.)":
                    print("Message contains video")
                    video_path = Path(datasetPath) / Path(video)
                    processVideo(individualMessage, video_path)

                photo = individualMessage.get("photo")
                if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
                    print("Message contains photo")
                    photo_path = Path(datasetPath) / Path(photo)
                    processImage(individualMessage, photo_path)

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
                    print(f"Processing full text of length {len(fullText)}")
                    processCategories(individualMessage, fullText)
                    processLocations(individualMessage, fullText)
            print("All messages processed successfully")

            with open(resultJson, 'w', encoding='utf-8') as f:
                    json.dump(jsonData, f, ensure_ascii=False, indent=4)
                    print("JSON written successfully")
        except Exception as e:
            print(f"Error in processJson: {e}")
            print(traceback.format_exc())