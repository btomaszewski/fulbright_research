import os
import shutil
import json
import sys
import traceback
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("processJson_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("processJson")

# Log startup information 
logger.info("Script started")
logger.info(f"Python version: {sys.version}")
logger.info(f"Script location: {os.path.abspath(__file__)}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Arguments: {sys.argv}")

try:
    # Try to add parent directory to path, but with error handling
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(parent_dir)
    logger.info(f"Added to sys.path: {parent_dir}")
    logger.info(f"Current sys.path: {sys.path}")

    # Try to import each module individually with error handling
    try:
        logger.info("Importing frameExtraction")
        from frameExtraction import extractFrames
        logger.info("Successfully imported frameExtraction")
    except ImportError as e:
        logger.error(f"Failed to import frameExtraction: {e}")
        
    try:
        logger.info("Importing videoAnalysis")
        from videoAnalysis import summarize
        logger.info("Successfully imported videoAnalysis")
    except ImportError as e:
        logger.error(f"Failed to import videoAnalysis: {e}")
        
    try:
        logger.info("Importing imageAnalysis")
        from imageAnalysis import analyzePhoto
        logger.info("Successfully imported imageAnalysis")
    except ImportError as e:
        logger.error(f"Failed to import imageAnalysis: {e}")
        
    try:
        logger.info("Importing aiLoader")
        from aiLoader import loadAI
        logger.info("Successfully imported aiLoader")
    except ImportError as e:
        logger.error(f"Failed to import aiLoader: {e}")
        
    try:
        logger.info("Importing helpers")
        from helpers import translate, transcribe
        logger.info("Successfully imported helpers")
    except ImportError as e:
        logger.error(f"Failed to import helpers: {e}")
        
    try:
        logger.info("Importing cleanJson")
        from cleanJson import cleanJson
        logger.info("Successfully imported cleanJson")
    except ImportError as e:
        logger.error(f"Failed to import cleanJson: {e}")
        
    try:
        logger.info("Importing vectorImplementation")
        from vectorImplementation import categorize
        logger.info("Successfully imported vectorImplementation")
    except ImportError as e:
        logger.error(f"Failed to import vectorImplementation: {e}")
        
    '''try:
        logger.info("Importing nerImplementation")
        from nerImplementation import getLocations
        logger.info("Successfully imported nerImplementation")
    except ImportError as e:
        logger.error(f"Failed to import nerImplementation: {e}")
    '''

    # Log before AI client initialization
    logger.info("About to initialize AI client")
    try:
        client = loadAI()
        logger.info("AI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI client: {e}")
        logger.error(traceback.format_exc())

    # Paths
    rawJsonDir = Path("./rawJson")
    processedJsonDir = Path("./processedJson")
    processedJsonDir.mkdir(exist_ok=True)
    currentDir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Current directory: {currentDir}")
    logger.info(f"rawJsonDir: {rawJsonDir.absolute()}")
    logger.info(f"processedJsonDir: {processedJsonDir.absolute()}")

    # Helper Functions
    def processText(individualMessage, text):
        logger.info(f"Processing text: {text[:50]}...")
        try:
            result_JSON = translate(text)
            if result_JSON:
                individualMessage['LANGUAGE'] = result_JSON.get("language", "unknown")
                individualMessage['TRANSLATED_TEXT'] = result_JSON.get("translation", "")
                logger.info(f"Text processed successfully. Detected language: {result_JSON.get('language', 'unknown')}")
            else:
                logger.warning("Translation returned None")
        except Exception as e:
            logger.error(f"Error in processText: {e}")
            logger.error(traceback.format_exc())

    def processVideo(individualMessage, video):
        logger.info(f"Processing video: {video}")
        try:
            video = os.path.join(processedJsonDir, video)
            logger.info(f"Full video path: {video}")
            
            # Get video transcription
            logger.info("Starting transcription")
            transcription = transcribe(video)
            if transcription:
                individualMessage['VIDEO_TRANSCRIPTION'] = transcription
                logger.info(f"Transcription successful: {transcription[:50]}...")
                
                logger.info("Starting transcription translation")
                transcriptionTranslation = translate(transcription)
                individualMessage['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation
                logger.info("Translation complete")

            # Extract frames
            framesDir = video + "Frames"
            logger.info(f"Extracting frames to: {framesDir}")
            extractFrames(video, framesDir)
            logger.info("Frame extraction complete")

            # Perform analysis of video frames
            logger.info("Starting video frame analysis")
            summary = summarize(framesDir)
            if summary:
                individualMessage['VIDEO_SUMMARY'] = summary
                logger.info(f"Video analysis complete: {summary[:50]}...")

            # Delete frames dir
            logger.info(f"Removing frames directory: {framesDir}")
            shutil.rmtree(framesDir)
            logger.info("Frames directory removed")
        except Exception as e:
            logger.error(f"Error in processVideo: {e}")
            logger.error(traceback.format_exc())

    def processImage(individualMessage, photo):
        logger.info(f"Processing image: {photo}")
        try:
            analysis = analyzePhoto(photo)
            if analysis:
                individualMessage['PHOTO_ANALYSIS'] = analysis
                logger.info(f"Image analysis complete: {analysis[:50]}...")
            else:
                logger.warning("Image analysis returned None")
        except Exception as e:
            logger.error(f"Error in processImage: {e}")
            logger.error(traceback.format_exc())

    def processCategories(individualMessage, fullText):
        logger.info(f"Processing categories for text: {fullText[:50]}...")
        try:
            categories = categorize(fullText)
            if categories:
                individualMessage['CATEGORIES'] = categories
                logger.info(f"Categories assigned: {categories}")
            else:
                logger.warning("Category processing returned None")
        except Exception as e:
            logger.error(f"Error in processCategories: {e}")
            logger.error(traceback.format_exc())

    '''
    def processLocations(individualMessage, fullText):
        logger.info(f"Processing locations for text: {fullText[:50]}...")
        try:
            locations = getLocations(fullText)
            if locations:
                individualMessage['LOCATIONS'] = locations
                logger.info(f"Locations found: {locations}")
            else:
                logger.warning("Location processing returned None")
        except Exception as e:
            logger.error(f"Error in processLocations: {e}")
            logger.error(traceback.format_exc())
    '''

    def processJson(messageData, processedDirPath):
        logger.info(f"Processing JSON with {len(messageData)} messages")
        try:
            # Count how many messages we'll actually process
            service_count = sum(1 for msg in messageData if msg.get("type") == "service")
            logger.info(f"Found {service_count} service messages to remove")
            
            # Use a new list for filtered messages to avoid modifying while iterating
            filtered_messages = [msg for msg in messageData if msg.get("type") != "service"]
            logger.info(f"After filtering, processing {len(filtered_messages)} messages")
            
            # Now process each message
            for i, individualMessage in enumerate(filtered_messages):
                logger.info(f"Processing message {i+1}/{len(filtered_messages)}")
                
                text = individualMessage.get("text")
                if text:
                    logger.info("Message contains text")
                    processText(individualMessage, text)
                
                video = individualMessage.get("file")
                if video and video != "(File exceeds maximum size. Change data exporting settings to download.)":
                    logger.info("Message contains video")
                    video_path = (f"{processedDirPath}/{video}").replace("\\", "/")
                    processVideo(individualMessage, video_path)

                photo = individualMessage.get("photo")
                if photo and photo != "(File exceeds maximum size. Change data exporting settings to download.)":
                    logger.info("Message contains photo")
                    photo_path = (f"{processedDirPath}/{photo}").replace("\\", "/")
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
                    logger.info(f"Processing full text of length {len(fullText)}")
                    processCategories(individualMessage, fullText)
                    #processLocations(individualMessage, fullText)
            
            # Replace the original messageData with our filtered and processed messages
            messageData.clear()
            messageData.extend(filtered_messages)
            logger.info("All messages processed successfully")
        except Exception as e:
            logger.error(f"Error in processJson: {e}")
            logger.error(traceback.format_exc())

    def main(rawChatPath=None, procJsonPath=None):
        logger.info(f"main() called with rawChatPath={rawChatPath}, procJsonPath={procJsonPath}")
        
        # Handle command-line arguments or use defaults
        if rawChatPath is None and len(sys.argv) > 1:
            rawChatPath = sys.argv[1]
        if procJsonPath is None and len(sys.argv) > 2:
            procJsonPath = sys.argv[2]
            
        if not rawChatPath or not procJsonPath:
            logger.error("Missing required paths: rawChatPath and/or procJsonPath")
            print("Error: Missing required paths. Usage: processJson <rawChatPath> <procJsonPath>")
            return 1
            
        logger.info(f"Processing chat from {rawChatPath} to {procJsonPath}")
        
        try:
            # Process files
            chatDir = os.path.basename(rawChatPath)
            chatDir = f"{chatDir}Processed"
            processedDirPath = os.path.join(procJsonPath, chatDir)
            logger.info(f"Processed directory path: {processedDirPath}")

            if os.path.exists(processedDirPath):
                logger.info(f"Removing existing directory: {processedDirPath}")
                shutil.rmtree(processedDirPath)

            logger.info(f"Copying from {rawChatPath} to {processedDirPath}")
            shutil.copytree(rawChatPath, processedDirPath)
            
            resultJson = Path(processedDirPath) / "result.json"
            logger.info(f"Looking for result.json at: {resultJson}")
            
            if resultJson.is_file():
                logger.info("result.json found")
                try:
                    logger.info("Cleaning JSON")
                    cleanJson(resultJson)
                    logger.info("JSON cleaned successfully")
                except Exception as e:
                    logger.error(f"Could not clean {resultJson}: {e}")
                    logger.error(traceback.format_exc())

                try:
                    logger.info("Reading JSON file")
                    with open(resultJson, 'r', encoding='utf-8') as f:
                        jsonData = json.load(f)
                        logger.info("JSON loaded successfully")
                        messageData = jsonData.get("messages", [])
                        logger.info(f"Found {len(messageData)} messages")

                        logger.info("Processing messages")
                        processJson(messageData, processedDirPath)
                        logger.info("Messages processed successfully")
                                
                    # Write messages to destination file
                    logger.info("Writing processed JSON back to file")
                    with open(resultJson, 'w', encoding='utf-8') as f:
                        json.dump(jsonData, f, ensure_ascii=False, indent=4)
                    logger.info("JSON written successfully")
                    
                except Exception as e:
                    logger.error(f"Error processing JSON: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.error(f"result.json not found at {resultJson}")
                print(f"Error: result.json not found at {resultJson}")
                return 1
                
            logger.info("Processing completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Unexpected error in main: {e}")
            logger.error(traceback.format_exc())
            return 1

    # Run main() if script is executed directly
    if __name__ == "__main__":
        logger.info("Script executed directly")
        if len(sys.argv) > 1:
            logger.info(f"Running main() with command line arguments: {sys.argv[1:]}")
            sys.exit(main(sys.argv[1], sys.argv[2]))
        else:
            logger.error("No directory path provided")
            print("Error: No directory path provided.")
            sys.exit(1)
    else:
        logger.info("Script imported as a module")

except Exception as e:
    logger.error(f"Critical error in script initialization: {e}")
    logger.error(traceback.format_exc())
    print(f"Critical error: {e}")
    sys.exit(1)