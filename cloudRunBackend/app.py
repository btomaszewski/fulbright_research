import os
import json
import sys
import traceback
import shutil
import tempfile
import base64
import uuid
from pathlib import Path
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

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

app = Flask(__name__)

# With this more specific configuration:
CORS(app, resources={r"/*": {
    "origins": [
        "https://data-analysis-f3c06bb4f2cc.herokuapp.com", 
        "http://localhost:3000"
    ],
    "supports_credentials": True
}})

# Ensure the /tmp/processing directory exists 
BASE_DIR = "/tmp/processing"
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
RAW_JSON_DIR = os.path.join(BASE_DIR, "rawJson")

# Create all necessary directories
for directory in [BASE_DIR, SESSIONS_DIR, RAW_JSON_DIR]:
    os.makedirs(directory, exist_ok=True)

# Active sessions storage
active_sessions = {}

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
    
    # Import google_access module for the new functions
    import google_access
    
    # Import OpenAI client for GPT-4o (if not covered by loadAI)
    try:
        from openai import OpenAI
        openai_client = OpenAI()
        logger.info("OpenAI client loaded successfully")
    except ImportError:
        logger.info("OpenAI client not imported - may be using a different client")
    
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
            
            # Add source_file field to track which file the message came from
            if 'source_file' not in individualMessage:
                individualMessage['source_file'] = os.path.basename(processedDirPath)
            
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

# PHASE 1: Initialize processing session with JSON data
@app.route('/process-json-init', methods=['POST'])
def process_json_init():
    """
    API endpoint to initialize JSON processing session
    
    Expected request format:
    {
        "jsonContents": {
            "file1.json": "...", // JSON string content
            "file2.json": "..."
        },
        "mediaManifest": [
            {"relativePath": "file1.mp4", "size": 1024000},
            {"relativePath": "image1.jpg", "size": 512000}
        ],
        "outputDir": "optional_output_dir_name",
        "preserveStructure": true  // Whether to preserve directory structure
    }
    
    Response format:
    {
        "success": true,
        "message": "Processing session initialized",
        "sessionId": "unique-session-id",
        "needsMediaFiles": true  // Whether media files should be uploaded
    }
    """
    logs = []
    logs.append("Initializing JSON processing session")
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data or 'jsonContents' not in request_data:
            return jsonify({'success': False, 'error': 'Invalid request: missing jsonContents'}), 400
        
        json_contents = request_data['jsonContents']
        media_manifest = request_data.get('mediaManifest', [])
        output_dir = request_data.get('outputDir', 'processed')
        preserve_structure = request_data.get('preserveStructure', True)
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create a session directory
        session_dir = os.path.join(SESSIONS_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        logs.append(f"Created session directory: {session_dir}")
        
        # Create processed directory within the session directory
        processed_dir_path = os.path.join(session_dir, output_dir)
        os.makedirs(processed_dir_path, exist_ok=True)
        logs.append(f"Created processed directory: {processed_dir_path}")
        
        # Write JSON files to session directory
        for file_name, file_content in json_contents.items():
            file_path = os.path.join(processed_dir_path, file_name)
            logs.append(f"Writing file: {file_path}")
            
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        
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
        
        # Store session information
        active_sessions[session_id] = {
            'created': True,
            'status': 'initialized',
            'output_dir': processed_dir_path,
            'result_json_path': result_json_path,
            'media_manifest': media_manifest,
            'received_media': [],
            'logs': logs
        }
        
        # Determine if media files are needed
        needs_media_files = len(media_manifest) > 0
        
        # Return the session ID
        return jsonify({
            "success": True,
            "message": "Processing session initialized",
            "sessionId": session_id,
            "needsMediaFiles": needs_media_files
        })
    
    except Exception as e:
        logs.append(f"Error initializing session: {str(e)}")
        logger.error(f"Error in process_json_init: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "logs": logs
        }), 500

# PHASE 2: Upload media files in batches
@app.route('/upload-media-batch', methods=['POST'])
def upload_media_batch():
    """
    API endpoint to upload media files in batches
    
    Expected request format:
    {
        "sessionId": "unique-session-id",
        "mediaFiles": {
            "file1.mp4": "base64content...",
            "image1.jpg": "base64content..."
        }
    }
    
    Response format:
    {
        "success": true,
        "message": "Media batch uploaded successfully",
        "receivedCount": 5,
        "totalReceived": 10,
        "totalExpected": 20
    }
    """
    logs = []
    logs.append("Processing media batch upload")
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data or 'sessionId' not in request_data or 'mediaFiles' not in request_data:
            return jsonify({
                'success': False, 
                'error': 'Invalid request: missing sessionId or mediaFiles'
            }), 400
        
        session_id = request_data['sessionId']
        media_files = request_data['mediaFiles']
        
        # Check if session exists
        if session_id not in active_sessions:
            return jsonify({
                'success': False, 
                'error': f'Session {session_id} not found'
            }), 404
        
        session = active_sessions[session_id]
        processed_dir_path = session['output_dir']
        
        # Update logs
        logs = session['logs']
        logs.append(f"Processing media batch with {len(media_files)} files")
        
        # Write media files
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
                    
                # Track received files
                session['received_media'].append(file_name)
            except Exception as e:
                logs.append(f"Error writing media file {file_name}: {str(e)}")
        
        # Update session status
        session['status'] = 'uploading'
        session['logs'] = logs
        
        # Calculate progress
        total_expected = len(session['media_manifest'])
        total_received = len(session['received_media'])
        
        return jsonify({
            "success": True,
            "message": "Media batch uploaded successfully",
            "receivedCount": len(media_files),
            "totalReceived": total_received,
            "totalExpected": total_expected
        })
    
    except Exception as e:
        logs.append(f"Error uploading media batch: {str(e)}")
        logger.error(f"Error in upload_media_batch: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "logs": logs
        }), 500

# PHASE 3: Finalize processing
@app.route('/finalize-processing', methods=['POST'])
def finalize_processing():
    """
    API endpoint to finalize JSON processing
    
    Expected request format:
    {
        "sessionId": "unique-session-id"
    }
    
    Response format:
    {
        "success": true,
        "message": "Processing completed successfully",
        "logs": [...], // Array of log messages
        "result": {...} // Processed JSON result
    }
    """
    logs = []
    logs.append("Finalizing JSON processing")
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data or 'sessionId' not in request_data:
            return jsonify({'success': False, 'error': 'Invalid request: missing sessionId'}), 400
        
        session_id = request_data['sessionId']
        
        # Check if session exists
        if session_id not in active_sessions:
            return jsonify({'success': False, 'error': f'Session {session_id} not found'}), 404
        
        session = active_sessions[session_id]
        processed_dir_path = session['output_dir']
        result_json_path = session['result_json_path']
        
        # Update logs
        logs = session['logs']
        logs.append("Starting final processing phase")
        
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
            
            # Update session status
            session['status'] = 'completed'
            session['logs'] = logs
            
            # Return the response
            return jsonify({
                "success": True,
                "message": "Processing completed successfully",
                "logs": logs,
                "result": result
            })
            
        except Exception as e:
            logs.append(f"Error processing JSON: {str(e)}")
            session['status'] = 'error'
            session['logs'] = logs
            return jsonify({
                "success": False,
                "error": f"Error processing JSON: {str(e)}",
                "logs": logs
            }), 500
    
    except Exception as e:
        logs.append(f"Server error: {str(e)}")
        logger.error(f"Error in finalize_processing: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "logs": logs
        }), 500

# Legacy endpoint (keep for backward compatibility)
@app.route('/process-json', methods=['POST'])
def process_json_api():
    """
    Legacy API endpoint to process JSON data
    Note: This is kept for backward compatibility but will issue warnings
    """
    logs = []
    logs.append("WARNING: Using legacy process-json endpoint. Consider switching to the new multi-phase approach for improved reliability.")
    
    try:
        # Get request data
        request_data = request.get_json()
        
        if not request_data or 'jsonContents' not in request_data:
            return jsonify({'success': False, 'error': 'Invalid request: missing jsonContents'}), 400
        
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

# ANALYSIS ROUTES FROM SECOND FLASK APP
@app.route('/get-prompts', methods=['GET'])
def get_prompts():
    """API endpoint to fetch available prompts from Google Sheets"""
    try:
        # Load prompts from Google Sheets
        prompt_data = google_access.GetPromptsFromGoogleSheet()
        
        # Convert to list of dictionaries for JSON response
        prompts = []
        for _, row in prompt_data.iterrows():
            prompts.append({
                "id": int(row['ID']),
                "name": row['PROMPT_NAME'],
                "text": row['PROMPT_TEXT']
            })
        
        return jsonify({"success": True, "prompts": prompts})
    
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get-prompt/<prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """API endpoint to fetch a specific prompt text by ID"""
    try:
        prompt_text = google_access.GetPromptFromID(prompt_id)
        return jsonify({"success": True, "text": prompt_text})
    
    except Exception as e:
        logger.error(f"Error retrieving prompt: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to analyze data based on a user question"""
    try:
        # Load dataset for context
        prompt_data = google_access.GetData()
        
        # Get request data (handle both form data and JSON)
        if request.is_json:
            data = request.get_json()
            user_input = data.get('user_input', '')
        else:
            user_input = request.form.get('user_input', '')
        
        if not user_input:
            return jsonify({"success": False, "error": "No user input provided"}), 400
        
        # ChatGPT prompt
        prompt = (
            "Analyze the following CSV dataset of Telegram messages. "
            "The prompt between the <start> and <end> tags is user-generated. "
            "Use your analysis of the dataset to respond to the prompt.\n\n"
            f"{prompt_data}\n\n"
            f"<start>{user_input}<end>"
        )
        
        # Get AI response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500  # Increased for more detailed responses
        )
        
        ai_response = response.choices[0].message.content
        
        return jsonify({
            "success": True, 
            "response": ai_response,
            "query": user_input
        })
    
    except Exception as e:
        logger.error(f"Error in ask API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    """API endpoint to generate a summary of the dataset"""
    try:
        # Get request data
        if request.is_json:
            data = request.get_json()
            query = data.get("query", "Generate a comprehensive summary of this Telegram data")
        else:
            query = request.form.get("query", "Generate a comprehensive summary of this Telegram data")
        
        prompt_data = google_access.GetData()
        
        # Call AI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Generate a summary report of the following dataframe:" + prompt_data},
                {"role": "user", "content": query},
                {"role": "system", "content": 
                    "You are a humanitarian researcher and data analyst. Your goal is to generate a report of the data that will be useful in identifying the concerns of potential beneficiaries, their biggest questions, and what aid needs to be provided. Return only the summary, do not add trailing characters such as *** to your response. Structure your summary based on the following example:"
                    "Date Range: xx/xx/xxxx - xx/xx/xxxx"
                    "Top Categories: (List most commonly listed categories here.)"
                    "Top Locations: (List most commonly listed locations here.)"
                    "Top Questions: (List most commonly asked questions here.)"
                    "Data Inferences: (Use your skills as an advanced data analyst to make inferences about and highlight trends in the data. List trends and inferences here.)"
                }
            ],
            max_tokens=1000  # Allow for longer summaries
        )
        
        summary_text = response.choices[0].message.content.strip()
        
        return jsonify({
            "success": True,
            "summary": summary_text,
            "query": query
        })
    
    except Exception as e:
        logger.error(f"Error in generate_summary API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

# Session management endpoint
@app.route('/session-status/<session_id>', methods=['GET'])
def session_status(session_id):
    """API endpoint to check the status of a processing session"""
    try:
        if session_id not in active_sessions:
            return jsonify({'success': False, 'error': f'Session {session_id} not found'}), 404
        
        session = active_sessions[session_id]
        
        # Calculate progress
        total_expected = len(session['media_manifest'])
        total_received = len(session['received_media'])
        progress = (total_received / total_expected * 100) if total_expected > 0 else 100
        
        return jsonify({
            "success": True,
            "status": session['status'],
            "progress": progress,
            "totalReceived": total_received,
            "totalExpected": total_expected
        })
    
    except Exception as e:
        logger.error(f"Error checking session status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500