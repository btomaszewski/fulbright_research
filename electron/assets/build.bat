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

REM Create a single entry-point script - FIX: properly escape log format string
echo Creating merged entry script...
(
echo #!/usr/bin/env python
echo import os
echo import sys
echo import logging
echo.
echo # Configure basic logging
echo logging.basicConfig(
echo     level=logging.INFO,
echo     format='%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s',
echo     handlers=[logging.StreamHandler()]
echo )
echo logger = logging.getLogger("main")
echo.
echo # Log startup info
echo logger.info(f"Starting application from {os.path.abspath(__file__)}")
echo logger.info(f"Working directory: {os.getcwd()}")
echo logger.info(f"Arguments: {sys.argv}")
echo.
echo # Add src directory to path
echo src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
echo sys.path.insert(0, src_dir)
echo logger.info(f"Added to path: {src_dir}")
echo.
echo # Try to load environment variables
echo try:
echo     from dotenv import load_dotenv
echo     env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
echo     if os.path.exists(env_file):
echo         load_dotenv(env_file)
echo         logger.info(f"Loaded environment from {env_file}")
echo     else:
echo         logger.warning(".env file not found")
echo except ImportError:
echo     logger.warning("python-dotenv not available, skipping .env loading")
echo.
echo # Import and run the main function
echo try:
echo     from src.processJson import main
echo     logger.info("Successfully imported processJson module")
echo     sys.exit(main())
echo except Exception as e:
echo     logger.error(f"Error in main application: {e}", exc_info=True)
echo     sys.exit(1)
) > temp_build\main.py

REM Run PyInstaller
echo Running PyInstaller...
REM Copy the hook file to the temp build directory
copy hook-src.py temp_build\
cd temp_build

REM Create a custom hook file for your module dependencies
(
echo from PyInstaller.utils.hooks import collect_all, collect_submodules
echo.
echo # Collect all for important packages
echo datas, binaries, hiddenimports = collect_all('spacy')
echo datas2, binaries2, hiddenimports2 = collect_all('openai')
echo datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')
echo.
echo # Combine all collected items
echo datas.extend(datas2)
echo datas.extend(datas3)
echo binaries.extend(binaries2)
echo binaries.extend(binaries3)
echo hiddenimports.extend(hiddenimports2)
echo hiddenimports.extend(hiddenimports3)
echo.
echo # Add more specific hidden imports
echo hiddenimports.extend([
echo     'en_core_web_sm',
echo     'src.frameExtraction',
echo     'src.videoAnalysis',
echo     'src.imageAnalysis',
echo     'src.aiLoader',
echo     'src.helpers',
echo     'src.cleanJson',
echo     'src.vectorImplementation',
echo     'dotenv',
echo     'numpy',
echo     'pandas',
echo     'json',
echo     'pathlib',
echo     'shutil',
echo     'torch',
echo     'transformers',
echo     'PIL',
echo     'cv2',
echo ])
) > hook-src.py

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

