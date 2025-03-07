import os
import sys
import json
import shutil
import logging
import traceback
from pathlib import Path

# Clear the SSL_CERT_FILE environment variable to avoid SSL errors
if "SSL_CERT_FILE" in os.environ:
    print(f"Removing SSL_CERT_FILE environment variable (was: {os.environ['SSL_CERT_FILE']})")
    del os.environ["SSL_CERT_FILE"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_your_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_your_data")

# CONFIGURATION - Change these to match your actual paths
INPUT_DIR = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/ChatExport_2025-02-17"
RAW_DIR = "./rawJson"
PROCESSED_DIR = "./processedJson"
SCRIPT_PATH = "assets/python/processJson.py"  # Path to your main script

def check_for_result_json(input_dir):
    """Check if result.json exists in the input directory"""
    input_path = Path(input_dir)
    result_json = input_path / "result.json"
    
    if result_json.exists():
        logger.info(f"✅ Found result.json in {input_dir}")
        return True
    else:
        logger.error(f"❌ result.json NOT found in {input_dir}")
        # List files in the directory to help diagnose
        logger.info(f"Files in {input_dir}:")
        for file in input_path.iterdir():
            logger.info(f"  - {file.name}")
        return False

def prepare_test_environment():
    """Prepare the test environment by setting up directories"""
    logger.info("Preparing test environment")
    
    # Create raw and processed directories
    raw_path = Path(RAW_DIR)
    processed_path = Path(PROCESSED_DIR)
    
    # Clear existing directories if they exist
    if raw_path.exists():
        logger.info(f"Clearing existing {RAW_DIR}")
        shutil.rmtree(raw_path)
    if processed_path.exists():
        logger.info(f"Clearing existing {PROCESSED_DIR}")
        shutil.rmtree(processed_path)
    
    # Create fresh directories
    raw_path.mkdir(parents=True)
    processed_path.mkdir(parents=True)
    
    # Get basename of input directory for the raw chat dir
    input_basename = os.path.basename(INPUT_DIR)
    
    # Create a directory in raw_path with the same basename as input
    test_chat_dir = raw_path / input_basename
    
    # Don't use the full path as directory name
    if not check_for_result_json(INPUT_DIR):
        logger.error("Input directory must contain result.json")
        return None
    
    # Copy everything from input to test_chat_dir
    logger.info(f"Copying from {INPUT_DIR} to {test_chat_dir}")
    shutil.copytree(INPUT_DIR, test_chat_dir)
    
    logger.info(f"Test environment prepared in {test_chat_dir}")
    return test_chat_dir

def run_main_script(raw_chat_path):
    """Run the main script with the given path"""
    logger.info(f"Running main script with paths: {raw_chat_path}, {PROCESSED_DIR}")
    
    try:
        # Find and load the main script
        if not os.path.exists(SCRIPT_PATH):
            logger.error(f"Script not found at {SCRIPT_PATH}")
            return 1
        
        script_abs_path = os.path.abspath(SCRIPT_PATH)
        script_dir = os.path.dirname(script_abs_path)
        
        # Add script directory to path so imports work
        sys.path.append(script_dir)
        
        # Import the module
        sys.path.append(os.path.dirname(script_abs_path))
        module_name = os.path.splitext(os.path.basename(script_abs_path))[0]
        
        try:
            # Use importlib to load the module dynamically
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Run the main function
            result = module.main(str(raw_chat_path), PROCESSED_DIR)
            logger.info(f"Main script completed with result code: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error running main function: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback to subprocess if import fails
            import subprocess
            logger.info("Falling back to subprocess execution")
            
            cmd = [sys.executable, script_abs_path, str(raw_chat_path), PROCESSED_DIR]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            logger.info(f"Subprocess stdout: {result.stdout}")
            logger.error(f"Subprocess stderr: {result.stderr}")
            
            return result.returncode
            
    except Exception as e:
        logger.error(f"Error setting up main script: {e}")
        logger.error(traceback.format_exc())
        return 1

def validate_results():
    """Validate that the main script produced expected results"""
    logger.info(f"Validating results in {PROCESSED_DIR}")
    
    # Get the name of the input dir with "Processed" appended
    input_basename = os.path.basename(INPUT_DIR)
    processed_dir_name = f"{input_basename}Processed"
    processed_path = Path(PROCESSED_DIR) / processed_dir_name
    
    if not processed_path.exists():
        logger.error(f"Processed directory not found: {processed_path}")
        return False
    
    # Check for result.json
    result_json_path = processed_path / "result.json"
    if not result_json_path.exists():
        logger.error(f"result.json not found in processed directory: {result_json_path}")
        return False
    
    # Load and check result.json
    try:
        with open(result_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "messages" not in data or not data["messages"]:
            logger.error("No messages found in processed result.json")
            return False
        
        # Check for processed fields in messages
        processed_fields = ["CATEGORIES", "LANGUAGE", "TRANSLATED_TEXT"]
        field_counts = {field: 0 for field in processed_fields}
        
        for msg in data["messages"]:
            for field in processed_fields:
                if field in msg:
                    field_counts[field] += 1
        
        # Log statistics
        total_messages = len(data["messages"])
        logger.info(f"Total messages: {total_messages}")
        
        for field, count in field_counts.items():
            percentage = (count / total_messages) * 100 if total_messages > 0 else 0
            logger.info(f"  {field}: {count}/{total_messages} ({percentage:.1f}%)")
        
        # Display sample of processed message
        for i, msg in enumerate(data["messages"]):
            if "CATEGORIES" in msg:
                logger.info(f"\nExample processed message {i+1}:")
                logger.info(f"  Text: {msg.get('text', '')[:100]}...")
                logger.info(f"  Language: {msg.get('LANGUAGE', 'N/A')}")
                
                # Format category info for readability
                categories = msg.get('CATEGORIES', [])
                if categories and len(categories) > 0:
                    category_info = categories[0].get('classification', {})
                    confidence_scores = category_info.get('confidence_scores', {})
                    
                    if confidence_scores:
                        top_scores = sorted(
                            [(cat, score) for cat, score in confidence_scores.items()],
                            key=lambda x: x[1],
                            reverse=True
                        )[:3]
                        
                        logger.info("  Top categories:")
                        for cat, score in top_scores:
                            logger.info(f"    {cat}: {score:.4f}")
                
                break
        
        # Consider success if at least some messages were processed
        success = field_counts["CATEGORIES"] > 0 or field_counts["LANGUAGE"] > 0
        if success:
            logger.info("✅ Validation successful: Processed messages found")
        else:
            logger.error("❌ Validation failed: No processed messages found")
        
        return success
        
    except Exception as e:
        logger.error(f"Error validating results: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main test function"""
    logger.info("Starting test with your data")
    
    try:
        # Check that input directory exists
        if not os.path.exists(INPUT_DIR):
            logger.error(f"Input directory not found: {INPUT_DIR}")
            return 1
        
        # Prepare test environment
        test_chat_dir = prepare_test_environment()
        if not test_chat_dir:
            logger.error("Failed to prepare test environment")
            return 1
        
        # Run main script
        result = run_main_script(test_chat_dir)
        if result != 0:
            logger.error(f"Main script execution failed with exit code {result}")
            return 1
        
        # Validate results
        validation_result = validate_results()
        
        if validation_result:
            logger.info("✅ Test PASSED: Your script executed successfully with your data")
            print("\n✅ Test PASSED: Your script executed successfully with your data\n")
        else:
            logger.error("❌ Test FAILED: Validation of results failed")
            print("\n❌ Test FAILED: Validation of results failed\n")
        
        return 0 if validation_result else 1
        
    except Exception as e:
        logger.error(f"Error in test execution: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())