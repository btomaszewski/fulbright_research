#!/usr/bin/env python3
"""
Wrapper script to handle credentials passed from Electron and
then launch the main processJson.py script.

This script should be placed in the same directory as processJson.py
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
import subprocess
import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("wrapper")

def find_process_json_py():
    """Find the processJson.py file in various possible locations"""
    possible_locations = [
        # Regular locations
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "processJson.py"),
        os.path.join(os.getcwd(), "processJson.py"),
        
        # PyInstaller bundle locations
        os.path.join(getattr(sys, '_MEIPASS', ''), "processJson.py"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "src", "processJson.py"),
        "processJson.py",  # Current directory
    ]
    
    # Log all paths we're checking
    logger.info("Searching for processJson.py in the following locations:")
    for loc in possible_locations:
        logger.info(f"  - {loc}")
    
    # Check each location
    for path in possible_locations:
        if os.path.exists(path):
            logger.info(f"Found processJson.py at: {path}")
            return path
    
    logger.error("Could not find processJson.py in any expected location")
    return None

def main():
    logger.info(f"Starting wrapper script from {os.path.abspath(__file__)}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Number of arguments: {len(sys.argv)}")
    
    # Check if we have enough arguments
    if len(sys.argv) < 3:
        logger.error("Not enough arguments. Expected: credentials_json input_dir output_dir")
        logger.error(f"Got {len(sys.argv)} arguments: {sys.argv}")
        return 1
    
    # Parse the first argument as JSON credentials
    try:
        credentials = json.loads(sys.argv[1])
        logger.info("Successfully parsed credentials JSON")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse credentials JSON: {e}")
        return 1
    
    # Get input and output directories
    input_dir = sys.argv[2]
    output_dir = sys.argv[3]
    
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    # Set environment variables from credentials
    temp_files = []  # Keep track of temporary files to clean up
    
    try:
        # Set OpenAI API key
        if 'OPENAI_API_KEY' in credentials:
            os.environ['OPENAI_API_KEY'] = credentials['OPENAI_API_KEY']
            logger.info("Set OPENAI_API_KEY environment variable")
        
        # Set Google Sheet ID
        if 'GOOGLE_SHEET_ID' in credentials:
            os.environ['GOOGLE_SHEET_ID'] = credentials['GOOGLE_SHEET_ID']
            logger.info("Set GOOGLE_SHEET_ID environment variable")
        
        # Handle Google credentials
        if 'GOOGLE_CREDENTIALS_JSON' in credentials and credentials['GOOGLE_CREDENTIALS_JSON']:
            # Write Google credentials JSON to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(credentials['GOOGLE_CREDENTIALS_JSON'], temp_file)
                google_creds_path = temp_file.name
                temp_files.append(google_creds_path)
                
            os.environ['GOOGLE_CREDENTIALS_PATH'] = google_creds_path
            logger.info(f"Google credentials written to temporary file: {google_creds_path}")
        
        # Verify required environment variables
        required_env_vars = ['OPENAI_API_KEY', 'GOOGLE_CREDENTIALS_PATH', 'GOOGLE_SHEET_ID']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            return 1
            
        # Find the processJson.py file
        process_json_path = find_process_json_py()
        if not process_json_path:
            return 1
            
        # Try to import and run processJson module
        try:
            logger.info(f"Attempting to import processJson from {process_json_path}")
            spec = importlib.util.spec_from_file_location("processJson", process_json_path)
            process_json = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(process_json)
            
            # Call the main function if it exists
            if hasattr(process_json, 'main'):
                logger.info("Calling processJson.main()")
                result = process_json.main(input_dir, output_dir)
                return result
            else:
                logger.error("processJson module does not have a main() function")
                return 1
                
        except Exception as e:
            logger.error(f"Error importing or running processJson module: {e}", exc_info=True)
            
            # Fallback to subprocess approach
            logger.info(f"Falling back to subprocess approach with {process_json_path}")
            
            result = subprocess.run(
                [sys.executable, process_json_path, input_dir, output_dir],
                env=os.environ,
                check=True
            )
            
            return result.returncode
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_file}: {e}")

if __name__ == "__main__":
    sys.exit(main())