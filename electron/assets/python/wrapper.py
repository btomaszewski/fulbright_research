
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

def looks_like_valid_path(path_str):
    """Check if a string looks like a valid file path"""
    if os.name == 'nt':  # Windows
        # Windows paths should have backslashes or drive letters
        return '\\' in path_str or (':' in path_str and len(path_str) > 2)
    else:
        # Unix paths typically start with /
        return path_str.startswith('/') or '/' in path_str

def load_credentials_json(arg):
    """
    Load credentials JSON from either a file path or a JSON string
    with enhanced robustness for Windows command-line argument passing
    """
    try:
        # First, clean up the argument
        if arg is None:
            raise ValueError("Credentials argument is None")
            
        # Remove any surrounding quotes that might be present
        arg = arg.strip()
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            arg = arg[1:-1]
        
        # Print the first few characters for debugging
        logger.info(f"Credentials argument (first 30 chars): {arg[:30]}...")
        
        # Try to parse as JSON first
        try:
            return json.loads(arg)
        except json.JSONDecodeError as e:
            logger.info(f"JSON parsing failed: {e}")
            
            # If it looks like JavaScript object notation without quotes
            if arg.startswith('{') and ':' in arg:
                logger.info("Attempting to fix unquoted JavaScript object keys")
                # Convert JavaScript object to proper JSON by adding quotes to keys
                import re
                # Add quotes around keys
                fixed_json = re.sub(r'(\w+):', r'"\1":', arg)
                # Add quotes around string values not already quoted
                fixed_json = re.sub(r':\s*([^",{\[\d][^,}\]]*)', r': "\1"', fixed_json)
                
                logger.info(f"Fixed JSON: {fixed_json[:50]}...")
                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    logger.error(f"Fixed JSON also failed to parse: {e2}")
                    
        # If it might be a file path
        if os.path.exists(arg):
            logger.info(f"Trying to read credentials from file: {arg}")
            with open(arg, 'r') as f:
                return json.loads(f.read())
        
        logger.error(f"Failed to parse credentials: {arg[:100]}...")
        raise ValueError("Could not parse credentials as JSON or file path")
        
    except Exception as e:
        logger.error(f"Error processing credentials: {str(e)}")
        raise

def reconstruct_paths(remaining_args):
    """Better handling of paths with spaces that may have been split"""
    logger.info(f"Attempting to reconstruct paths from: {remaining_args}")
    
    # First check if we just have two clean arguments
    if len(remaining_args) == 2:
        return remaining_args[0], remaining_args[1]
    
    # Try to find a valid split point by checking if paths exist
    for i in range(1, len(remaining_args)):
        potential_input = " ".join(remaining_args[:i])
        potential_output = " ".join(remaining_args[i:])
        
        # Remove any quotes that might be present
        potential_input = potential_input.strip('"\'')
        potential_output = potential_output.strip('"\'')
        
        # Check if both paths exist or at least look like valid paths
        input_exists = os.path.exists(potential_input)
        output_dir_exists = os.path.exists(os.path.dirname(potential_output))
        
        logger.info(f"Trying split at {i}: Input='{potential_input}' (exists={input_exists}), Output='{potential_output}' (parent exists={output_dir_exists})")
        
        if input_exists or output_dir_exists:
            return potential_input, potential_output
    
    # Fallback: just use the first and last parts
    logger.warning("Could not find valid path split, using fallback approach")
    return remaining_args[0], remaining_args[-1]

def run_process_json(process_json_path, input_dir, output_dir):
    """Run the processJson.py script with better handling of Windows paths"""
    try:
        # Normalize all paths
        process_json_path = os.path.normpath(process_json_path)
        input_dir = os.path.normpath(input_dir)
        output_dir = os.path.normpath(output_dir)
        
        logger.info(f"Running processJson with normalized paths:")
        logger.info(f"  Script: {process_json_path}")
        logger.info(f"  Input:  {input_dir}")
        logger.info(f"  Output: {output_dir}")
        
        if os.name == 'nt':  # Windows
            # On Windows, use a list of arguments with proper shell mode
            cmd = [sys.executable, process_json_path, input_dir, output_dir]
            logger.info(f"Windows command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env=os.environ,
                shell=True,  # Using shell=True on Windows for better path handling
                check=True
            )
        else:
            # On Unix, we can use the list form without shell
            cmd = [sys.executable, process_json_path, input_dir, output_dir]
            logger.info(f"Unix command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env=os.environ,
                check=True
            )
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess execution failed: {e}")
        return e.returncode
    except Exception as e:
        logger.error(f"Failed to run processJson script: {e}", exc_info=True)
        return 1

def main():
    logger.info(f"Starting wrapper script from {os.path.abspath(__file__)}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Number of arguments: {len(sys.argv)}")
    
    # Print args for debugging (redact sensitive info)
    for i, arg in enumerate(sys.argv):
        if i == 1:  # Credentials JSON
            logger.info(f"Arg {i}: [CREDENTIALS REDACTED]")
        else:
            logger.info(f"Arg {i}: {arg}")
    
    # Check if we have enough arguments
    if len(sys.argv) < 3:
        logger.error("Not enough arguments. Expected: credentials_json input_dir output_dir")
        logger.error(f"Got {len(sys.argv)} arguments: {sys.argv}")
        return 1
    
    # Parse the first argument as JSON credentials with improved handling
    try:
        credentials = load_credentials_json(sys.argv[1])
        logger.info("Successfully parsed credentials")
    except Exception as e:
        logger.error(f"Failed to parse credentials: {e}")
        return 1
    
    # Handle paths with improved reconstruction logic
    remaining_args = sys.argv[2:]
    input_path, output_path = reconstruct_paths(remaining_args)
    
    # Normalize paths
    input_dir = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_path)
    
    logger.info(f"Input directory (reconstructed): {input_path}")
    logger.info(f"Output directory (reconstructed): {output_path}")
    logger.info(f"Input directory (normalized): {input_dir}")
    logger.info(f"Output directory (normalized): {output_dir}")
    
    # Verify that paths look reasonable
    if not looks_like_valid_path(input_dir) or not looks_like_valid_path(output_dir):
        logger.warning(f"Reconstructed paths don't look like valid paths, this might indicate an issue")
    
    # Set environment variables from credentials
    temp_files = []  # Keep track of temporary files to clean up
    
    try:
        # Set OpenAI API key
        if 'OPENAI_API_KEY' in credentials:
            os.environ['OPENAI_API_KEY'] = credentials['OPENAI_API_KEY'].strip()
            logger.info("Set OPENAI_API_KEY environment variable")
        
        # Set Google Sheet ID
        if 'GOOGLE_SHEET_ID' in credentials:
            os.environ['GOOGLE_SHEET_ID'] = credentials['GOOGLE_SHEET_ID'].strip()
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
            
            # Fallback to subprocess approach with improved Windows handling
            logger.info(f"Falling back to subprocess approach with {process_json_path}")
            return run_process_json(process_json_path, input_dir, output_dir)
            
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