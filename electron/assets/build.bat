@echo off
setlocal enabledelayedexpansion

REM Set working directory to script location
cd /d "%~dp0"

REM Configuration
set SRC_DIR=python
set MAIN_SCRIPT=%SRC_DIR%\processJson.py
set OUTPUT_NAME=processJson
set VENV_DIR=.venv
set PLATFORM_ID=windows
set TARGET_DIR=dist-%PLATFORM_ID%

echo Starting build process from %cd%

REM Clean previous builds
echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist temp_build rmdir /s /q temp_build
if exist %TARGET_DIR% rmdir /s /q %TARGET_DIR%
if exist spacy_model rmdir /s /q spacy_model

REM Ensure the target directory exists
mkdir %TARGET_DIR%

REM Activate virtual environment if available
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo No virtual environment found. Using system Python.
)

REM Verify Python and dependencies
echo Python environment information:
python --version
pip list

REM Verify spaCy and model are installed
echo Verifying spaCy installation...
python -c "import spacy; print(f'spaCy version: {spacy.__version__}')"
python -c "import en_core_web_sm; print(f'Model path: {en_core_web_sm.__path__[0]}')"

REM Prepare spaCy model files
echo Preparing spaCy model files...
python copy_spacy_model.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to prepare spaCy model files
    exit /b 1
)

REM Create temp directory for build
mkdir temp_build\src

REM Copy all Python scripts to temp_build/src
copy "%SRC_DIR%\*.py" temp_build\src\
copy copy_spacy_model.py temp_build\

REM Add dotenv file if it exists
if exist ".env" (
    echo Copying .env file to build directory
    copy .env temp_build\
)

REM Create a single entry-point script
echo Creating merged entry script...

REM Windows doesn't have here documents like bash, so we'll use a Python script to create the file
python -c "
with open('temp_build/main.py', 'w') as f:
    f.write('''#!/usr/bin/env python
import os
import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(\"main\")

# Log startup info
logger.info(f\"Starting application from {os.path.abspath(__file__)}\")
logger.info(f\"Working directory: {os.getcwd()}\")
logger.info(f\"Arguments: {sys.argv}\")

# Add src directory to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"src\")
sys.path.insert(0, src_dir)
logger.info(f\"Added to path: {src_dir}\")

# Try to load environment variables
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), \".env\")
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info(f\"Loaded environment from {env_file}\")
    else:
        logger.warning(\".env file not found\")
except ImportError:
    logger.warning(\"python-dotenv not available, skipping .env loading\")

# Import and run the main function
try:
    from src.processJson import main
    logger.info(\"Successfully imported processJson module\")
    sys.exit(main())
except Exception as e:
    logger.error(f\"Error in main application: {e}\", exc_info=True)
    sys.exit(1)
''')
"

REM Run PyInstaller
echo Running PyInstaller...

REM Create hook file in a similar way to the main script
python -c "
with open('temp_build/hook-src.py', 'w') as f:
    f.write('''from PyInstaller.utils.hooks import collect_all, collect_submodules

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
''')
"

cd temp_build

REM Modify your PyInstaller command
pyinstaller --onefile --clean ^
    --name "%OUTPUT_NAME%" ^
    --paths=src ^
    --additional-hooks-dir=. ^
    --add-data "..\spacy_model\en_core_web_sm;en_core_web_sm" ^
    --add-data "..\vector_model_package;vector_model_package" ^
    --add-data ".env;.env" ^
    --collect-all openai ^
    --collect-all spacy ^
    --collect-all sentence_transformers ^
    --log-level=DEBUG ^
    main.py

REM Verify build success
if exist "dist\%OUTPUT_NAME%.exe" (
    echo ✅ Build successful!
    
    REM Move executable to final location
    move "dist\%OUTPUT_NAME%.exe" "..\%TARGET_DIR%\" 
    
    echo Final executable: %TARGET_DIR%\%OUTPUT_NAME%.exe
) else (
    echo ❌ Build failed! Check the logs above.
    exit /b 1
)

REM Clean up
cd ..
rmdir /s /q temp_build

echo Build process completed.

