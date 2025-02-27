#!/usr/bin/env python
import os

# Create the main.py file for PyInstaller
main_py_content = '''#!/usr/bin/env python
import os
import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("main")

# Log startup info
logger.info(f"Starting application from {os.path.abspath(__file__)}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Arguments: {sys.argv}")

# Add src directory to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)
logger.info(f"Added to path: {src_dir}")

# Try to load environment variables
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(".env file not found")
except ImportError:
    logger.warning("python-dotenv not available, skipping .env loading")

# Import and run the main function
try:
    from src.processJson import main
    logger.info("Successfully imported processJson module")
    sys.exit(main())
except Exception as e:
    logger.error(f"Error in main application: {e}", exc_info=True)
    sys.exit(1)
'''

# Create the directory if it doesn't exist
os.makedirs("temp_build", exist_ok=True)

# Write the main.py file
with open("temp_build/main.py", "w") as f:
    f.write(main_py_content)

print("main.py created successfully")
