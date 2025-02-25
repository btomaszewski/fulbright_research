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

REM Default arguments for the script
set DEFAULT_PROC_JSON=processJson
set DEFAULT_RAW_CHAT_PATH=input
set DEFAULT_PROC_JSON_PATH=output

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
    echo Failed to prepare spaCy model files
    exit /b 1
)

REM Create temp directory for build
mkdir temp_build\python

REM Copy all Python scripts to the correct location
echo Copying Python files from %SRC_DIR% to temp_build\python...
copy "%SRC_DIR%\*.py" temp_build\python\
copy copy_spacy_model.py temp_build\

REM Create an __init__.py file in the python directory to make it a proper package
echo. > temp_build\python\__init__.py

REM Add dotenv file if it exists
if exist ".env" (
    echo Copying .env file to build directory
    copy .env temp_build\
)

REM Create a Python script that will create our required files
echo import os > create_files.py
echo import sys >> create_files.py
echo. >> create_files.py
echo # Main script content >> create_files.py
echo main_content = """#!/usr/bin/env python >> create_files.py
echo import os >> create_files.py
echo import sys >> create_files.py
echo import logging >> create_files.py
echo. >> create_files.py
echo # Configure basic logging >> create_files.py
echo logging.basicConfig( >> create_files.py
echo     level=logging.INFO, >> create_files.py
echo     format='%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s', >> create_files.py
echo     handlers=[logging.StreamHandler()] >> create_files.py
echo ) >> create_files.py
echo logger = logging.getLogger("main") >> create_files.py
echo. >> create_files.py
echo # Log startup info >> create_files.py
echo logger.info(f"Starting application from {os.path.abspath(__file__)}") >> create_files.py
echo logger.info(f"Working directory: {os.getcwd()}") >> create_files.py
echo. >> create_files.py
echo # Add python directory to path >> create_files.py
echo python_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python") >> create_files.py
echo sys.path.insert(0, python_dir) >> create_files.py
echo sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) >> create_files.py
echo logger.info(f"Added to path: {python_dir}") >> create_files.py
echo. >> create_files.py
echo # Hardcode arguments >> create_files.py
echo PROC_JSON = "%DEFAULT_PROC_JSON%" >> create_files.py
echo RAW_CHAT_PATH = "%DEFAULT_RAW_CHAT_PATH%" >> create_files.py
echo PROC_JSON_PATH = "%DEFAULT_PROC_JSON_PATH%" >> create_files.py
echo. >> create_files.py
echo # Override sys.argv with the hardcoded paths >> create_files.py
echo if len(sys.argv) <= 1: >> create_files.py
echo     # No arguments provided, use defaults >> create_files.py
echo     logger.info(f"Using default arguments: {PROC_JSON}, {RAW_CHAT_PATH}, {PROC_JSON_PATH}") >> create_files.py
echo     sys.argv = [sys.argv[0], PROC_JSON, RAW_CHAT_PATH, PROC_JSON_PATH] >> create_files.py
echo     logger.info(f"Updated arguments: {sys.argv}") >> create_files.py
echo. >> create_files.py
echo # Try to load environment variables >> create_files.py
echo try: >> create_files.py
echo     from dotenv import load_dotenv >> create_files.py
echo     env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env") >> create_files.py
echo     if os.path.exists(env_file): >> create_files.py
echo         load_dotenv(env_file) >> create_files.py
echo         logger.info(f"Loaded environment from {env_file}") >> create_files.py
echo     else: >> create_files.py
echo         logger.warning(".env file not found") >> create_files.py
echo except ImportError: >> create_files.py
echo     logger.warning("python-dotenv not available, skipping .env loading") >> create_files.py
echo. >> create_files.py
echo # Create directory for output if it doesn't exist >> create_files.py
echo os.makedirs(PROC_JSON_PATH, exist_ok=True) >> create_files.py
echo os.makedirs(RAW_CHAT_PATH, exist_ok=True) >> create_files.py
echo. >> create_files.py
echo # Import and run the main function >> create_files.py
echo try: >> create_files.py
echo     # First try direct import >> create_files.py
echo     try: >> create_files.py
echo         from processJson import main >> create_files.py
echo         logger.info("Successfully imported processJson module directly") >> create_files.py
echo     except ImportError: >> create_files.py
echo         # Next try from python package >> create_files.py
echo         try: >> create_files.py
echo             from python.processJson import main >> create_files.py
echo             logger.info("Successfully imported processJson module from python package") >> create_files.py
echo         except ImportError as e: >> create_files.py
echo             logger.error(f"Failed to import processJson: {e}") >> create_files.py
echo             sys.exit(1) >> create_files.py
echo     sys.exit(main()) >> create_files.py
echo except Exception as e: >> create_files.py
echo     logger.error(f"Error in main application: {e}", exc_info=True) >> create_files.py
echo     sys.exit(1) >> create_files.py
echo """ >> create_files.py
echo. >> create_files.py
echo # Hook script content >> create_files.py
echo hook_content = """from PyInstaller.utils.hooks import collect_all, collect_submodules >> create_files.py
echo. >> create_files.py
echo # Collect all for important packages >> create_files.py
echo datas, binaries, hiddenimports = collect_all('spacy') >> create_files.py
echo datas2, binaries2, hiddenimports2 = collect_all('openai') >> create_files.py
echo datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers') >> create_files.py
echo. >> create_files.py
echo # Combine all collected items >> create_files.py
echo datas.extend(datas2) >> create_files.py
echo datas.extend(datas3) >> create_files.py
echo binaries.extend(binaries2) >> create_files.py
echo binaries.extend(binaries3) >> create_files.py
echo hiddenimports.extend(hiddenimports2) >> create_files.py
echo hiddenimports.extend(hiddenimports3) >> create_files.py
echo. >> create_files.py
echo # Add more specific hidden imports >> create_files.py
echo hiddenimports.extend([ >> create_files.py
echo     'en_core_web_sm', >> create_files.py
echo     'processJson', >> create_files.py
echo     'python', >> create_files.py
echo     'python.processJson', >> create_files.py
echo     'python.frameExtraction', >> create_files.py
echo     'python.videoAnalysis', >> create_files.py
echo     'python.imageAnalysis', >> create_files.py
echo     'python.aiLoader', >> create_files.py
echo     'python.helpers', >> create_files.py
echo     'python.cleanJson', >> create_files.py
echo     'python.vectorImplementation', >> create_files.py
echo     'dotenv', >> create_files.py
echo     'numpy', >> create_files.py
echo     'pandas', >> create_files.py
echo     'json', >> create_files.py
echo     'pathlib', >> create_files.py
echo     'shutil', >> create_files.py
echo     'torch', >> create_files.py
echo     'transformers', >> create_files.py
echo     'PIL', >> create_files.py
echo     'cv2', >> create_files.py
echo ]) >> create_files.py
echo """ >> create_files.py
echo. >> create_files.py
echo # Write files >> create_files.py
echo with open('temp_build/main.py', 'w') as f: >> create_files.py
echo     f.write(main_content) >> create_files.py
echo. >> create_files.py
echo with open('temp_build/hook-src.py', 'w') as f: >> create_files.py
echo     f.write(hook_content) >> create_files.py
echo. >> create_files.py
echo print("Successfully created required files") >> create_files.py

REM Run the Python script to create our files
echo Creating required files...
python create_files.py
if %ERRORLEVEL% neq 0 (
    echo Failed to create required files
    exit /b 1
)

cd temp_build

REM Create hook-python.py file for Python directory imports
echo from PyInstaller.utils.hooks import collect_submodules > hook-python.py
echo hiddenimports = collect_submodules('python') >> hook-python.py

REM Create directories in the target folder
mkdir ..\%TARGET_DIR%\input
mkdir ..\%TARGET_DIR%\output

REM Create a README file for the executable
echo # %OUTPUT_NAME% Executable > ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo This executable is configured with the following default arguments: >> ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo - processJson: %DEFAULT_PROC_JSON% >> ..\%TARGET_DIR%\README.txt
echo - rawchatpath: %DEFAULT_RAW_CHAT_PATH% >> ..\%TARGET_DIR%\README.txt
echo - procJsonPath: %DEFAULT_PROC_JSON_PATH% >> ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo The program will automatically create the input and output directories if they don't exist. >> ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo ## Advanced Usage >> ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo You can also override these defaults by providing command-line arguments: >> ..\%TARGET_DIR%\README.txt
echo. >> ..\%TARGET_DIR%\README.txt
echo ```>> ..\%TARGET_DIR%\README.txt
echo %OUTPUT_NAME%.exe [processJson] [rawchatpath] [procJsonPath] >> ..\%TARGET_DIR%\README.txt
echo ``` >> ..\%TARGET_DIR%\README.txt

REM Modify your PyInstaller command
pyinstaller --onefile --clean ^
    --name "%OUTPUT_NAME%" ^
    --paths=. ^
    --paths=python ^
    --additional-hooks-dir=. ^
    --add-data "..\spacy_model\en_core_web_sm;en_core_web_sm" ^
    --add-data "..\vector_model_package;vector_model_package" ^
    --add-data ".env;.env" ^
    --hidden-import=python ^
    --hidden-import=python.processJson ^
    --collect-all openai ^
    --collect-all spacy ^
    --collect-all sentence_transformers ^
    --log-level=DEBUG ^
    main.py

REM Verify build success
if exist "dist\%OUTPUT_NAME%.exe" (
    echo Build successful!
    
    REM Move executable to final location
    move "dist\%OUTPUT_NAME%.exe" "..\%TARGET_DIR%\" 
    
    echo Final executable: %TARGET_DIR%\%OUTPUT_NAME%.exe
    echo Created README file with usage instructions: %TARGET_DIR%\README.txt
) else (
    echo Build failed! Check the logs above.
    exit /b 1
)

REM Clean up
cd ..
rmdir /s /q temp_build
del create_files.py

echo Build process completed.
echo.
echo NOTE: The executable is configured with the following default arguments:
echo   - processJson: %DEFAULT_PROC_JSON%
echo   - rawchatpath: %DEFAULT_RAW_CHAT_PATH%
echo   - procJsonPath: %DEFAULT_PROC_JSON_PATH%
echo.
echo The program will automatically create the input and output directories.

