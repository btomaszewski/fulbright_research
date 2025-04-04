import os
import json
import sys
import traceback
import shutil
import tempfile
import base64
from pathlib import Path
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("json-processor-api")

# Log startup information 
logger.info("Flask API started")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Files in directory: {os.listdir('.')}")

# Initialize Flask app
app = Flask(__name__)

# Import all necessary modules
try:
    # First, import the AI client
    from aiLoader import loadAI
    client = loadAI()
    logger.info("AI client loaded successfully")
    
    # Import other modules
    from helpers import translate, transcribe
    from frameExtraction import extractFrames
    from videoAnalysis import summarize
    from imageAnalysis import analyzePhoto
    from cleanJson import cleanJson
    from vectorImplementation import categorize
    from nerImplementation import getLocations
    
    logger.info("All modules imported successfully")
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error(traceback.format_exc())
    raise  # Re-raise to stop app startup since we need these modules
except Exception as e:
    logger.error(f"Unexpected error during initialization: {e}")
    logger.error(traceback.format_exc())
    raise  # Re-raise to stop app startup


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
                processLocations(individualMessage, fullText)
        
        # Replace the original messageData with our filtered and processed messages
        messageData.clear()
        messageData.extend(filtered_messages)
        logger.info("All messages processed successfully")
    except Exception as e:
        logger.error(f"Error in processJson: {e}")
        logger.error(traceback.format_exc())

# Define API endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/process-json', methods=['POST'])
def process_json_api():
    """
    API endpoint to process JSON data
    
    Expected request format:
    {
        "jsonContents": {
            "file1.json": "...", // JSON string content
            "file2.json": "..."
        },
        "mediaFiles": { // Optional
            "filename.mp4": "base64content...",
            "image.jpg": "base64content..."
        },
        "outputDir": "optional_output_dir_name"
    }
    
    Response format:
    {
        "message": "Processing completed successfully",
        "logs": [...], // Array of log messages
        "result": {...} // Processed JSON result
    }
    """
    logs = []
    logs.append("Starting JSON processing")
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data or 'jsonContents' not in request_data:
            return jsonify({'error': 'Invalid request: missing jsonContents'}), 400
        
        json_contents = request_data['jsonContents']
        media_files = request_data.get('mediaFiles', {})
        output_dir = request_data.get('outputDir', 'processed')
        
        # Create a temporary directory to store the files
        with tempfile.TemporaryDirectory() as temp_dir:
            logs.append(f"Created temporary directory: {temp_dir}")
            
            # Process directory path
            processed_dir_path = os.path.join(temp_dir, output_dir)
            os.makedirs(processed_dir_path, exist_ok=True)
            logs.append(f"Created processed directory: {processed_dir_path}")
            
            # Write JSON files to temp directory
            for file_name, file_content in json_contents.items():
                file_path = os.path.join(processed_dir_path, file_name)
                logs.append(f"Writing file: {file_path}")
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
            
            # Write media files if any
            for file_name, base64_content in media_files.items():
                file_path = os.path.join(processed_dir_path, file_name)
                logs.append(f"Writing media file: {file_path}")
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Decode and write the file
                try:
                    file_content = base64.b64decode(base64_content)
                    with open(file_path, 'wb') as f:
                        f.write(file_content)
                except Exception as e:
                    logs.append(f"Error writing media file {file_name}: {str(e)}")
            
            # Path to result.json file
            result_json_path = os.path.join(processed_dir_path, "result.json")
            
            # If result.json doesn't exist, create it from the first JSON file
            if not os.path.exists(result_json_path) and json_contents:
                first_json_file = next(iter(json_contents.values()))
                logs.append(f"Creating result.json from first JSON file")
                with open(result_json_path, 'w', encoding='utf-8') as f:
                    f.write(first_json_file)
            
            # Clean the JSON file
            try:
                if os.path.exists(result_json_path):
                    logs.append("Cleaning JSON")
                    cleanJson(result_json_path)
                    logs.append("JSON cleaned successfully")
            except Exception as e:
                logs.append(f"Error cleaning JSON: {str(e)}")
            
            # Process the messages
            try:
                # Read the JSON file
                with open(result_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    logs.append("JSON loaded successfully")
                    
                    # Get the messages array
                    message_data = json_data.get("messages", [])
                    logs.append(f"Found {len(message_data)} messages")
                    
                    # Process the messages
                    logs.append("Processing messages")
                    processJson(message_data, processed_dir_path)
                    logs.append("Messages processed successfully")
                
                # Write the processed JSON
                with open(result_json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                logs.append("Processed JSON written to file")
                
                # Read the processed result to return
                with open(result_json_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                logs.append("Result loaded for response")
                
                # Return the response
                return jsonify({
                    "message": "Processing completed successfully",
                    "logs": logs,
                    "result": result
                })
                
            except Exception as e:
                logs.append(f"Error processing JSON: {str(e)}")
                return jsonify({
                    "error": f"Error processing JSON: {str(e)}",
                    "logs": logs
                }), 500
    
    except Exception as e:
        logs.append(f"Server error: {str(e)}")
        logger.error(f"Error in process_json_api: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}",
            "logs": logs
        }), 500

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)