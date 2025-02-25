#!/bin/bash

# Set working directory to script location
cd "$(dirname "$0")"

# Configuration
SRC_DIR="python"
MAIN_SCRIPT="${SRC_DIR}/processJson.py"
OUTPUT_NAME="processJson"
VENV_DIR=".venv"
PLATFORM_ID=$(uname -s | tr '[:upper:]' '[:lower:]')
TARGET_DIR="dist-${PLATFORM_ID}"

echo "Starting build process from $(pwd)"

# Clean previous builds
echo "Cleaning up previous builds..."
rm -rf build dist temp_build "${TARGET_DIR}" spacy_model

# Ensure the target directory exists
mkdir -p "${TARGET_DIR}"

# Activate virtual environment if available
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "No virtual environment found. Using system Python."
fi

# Verify Python and dependencies
echo "Python environment information:"
python --version
pip list

# Verify spaCy and model are installed
echo "Verifying spaCy installation..."
python -c "import spacy; print(f'spaCy version: {spacy.__version__}')"
python -c "import en_core_web_sm; print(f'Model path: {en_core_web_sm.__path__[0]}')"

# Prepare spaCy model files
echo "Preparing spaCy model files..."
python copy_spacy_model.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to prepare spaCy model files"
    exit 1
fi

# Create temp directory for build
mkdir -p temp_build/src

# Copy all Python scripts to temp_build/src
cp "${SRC_DIR}"/*.py temp_build/src/
cp copy_spacy_model.py temp_build/

# Add dotenv file if it exists
if [ -f ".env" ]; then
    echo "Copying .env file to build directory"
    cp .env temp_build/
fi

# Create a single entry-point script
echo "Creating merged entry script..."
cat > "temp_build/main.py" << EOL
#!/usr/bin/env python
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
EOL

# Run PyInstaller
echo "Running PyInstaller..."
# Copy the hook file to the temp build directory
cp hook-src.py temp_build/
cd temp_build

# Create a custom hook file for your module dependencies
cat > "hook-src.py" << EOL
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all for important packages
datas, binaries, hiddenimports = collect_all('spacy')
datas2, binaries2, hiddenimports2 = collect_all('openai')
datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')

# Combine all collected items
datas.extend(datas2)
datas.extend(datas3)
binaries.extend(binaries2)
binaries.extend(binaries3)
hiddenimports.extend(hiddenimports2)
hiddenimports.extend(hiddenimports3)

# Add more specific hidden imports
hiddenimports.extend([
    'en_core_web_sm',
    'src.frameExtraction',
    'src.videoAnalysis',
    'src.imageAnalysis',
    'src.aiLoader',
    'src.helpers',
    'src.cleanJson',
    'src.vectorImplementation',
    'dotenv',
    'numpy',
    'pandas',
    'json',
    'pathlib',
    'shutil',
    'torch',
    'transformers',
    'PIL',
    'cv2',
])
EOL

# Modify your PyInstaller command
pyinstaller --onefile --clean \
    --name "${OUTPUT_NAME}" \
    --paths=src \
    --additional-hooks-dir=. \
    --add-data "../spacy_model/en_core_web_sm:en_core_web_sm" \
    --add-data "../vector_model_package:vector_model_package" \
    --add-data ".env:.env" \
    --collect-all openai \
    --collect-all spacy \
    --collect-all sentence_transformers \
    --log-level=DEBUG \
    main.py

# Verify build success
if [ -f "dist/${OUTPUT_NAME}" ]; then
    echo "✅ Build successful!"
    
    # Move executable to final location
    mv "dist/${OUTPUT_NAME}" "../${TARGET_DIR}/"
    chmod +x "../${TARGET_DIR}/${OUTPUT_NAME}"
    
    echo "Final executable: ${TARGET_DIR}/${OUTPUT_NAME}"
else
    echo "❌ Build failed! Check the logs above."
    exit 1
fi

# Clean up
cd ..
rm -rf temp_build

echo "Build process completed." 