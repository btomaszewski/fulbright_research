@echo off
setlocal enabledelayedexpansion

:: Set working directory to script location
cd /d "%~dp0"

:: Configuration
set SRC_DIR=python
set OUTPUT_NAME=processJson
set VENV_DIR=.venv
set PLATFORM_ID=windows
set TARGET_DIR=dist-%PLATFORM_ID%

echo Starting build process from %cd%

:: Clean previous builds
echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist temp_build rmdir /s /q temp_build
if exist %TARGET_DIR% rmdir /s /q %TARGET_DIR%
if exist spacy_model rmdir /s /q spacy_model

:: Ensure the target directory exists
mkdir %TARGET_DIR%

:: Activate virtual environment if available
if exist "%VENV_DIR%" (
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo No virtual environment found. Using system Python.
)

:: Verify Python and dependencies
echo Python environment information:
python --version
pip list

:: Verify spaCy and model are installed
echo Verifying spaCy installation...
python -c "import spacy; print(f'spaCy version: {spacy.__version__}')"
python -c "import en_core_web_sm; print(f'Model path: {en_core_web_sm.__path__[0]}')"

:: Prepare spaCy model files
echo Preparing spaCy model files...
python copy_spacy_model.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to prepare spaCy model files
    exit /b 1
)

:: Create temp directory for build
mkdir temp_build\src

:: Copy all Python scripts to temp_build/src
xcopy /y "%SRC_DIR%\*.py" temp_build\src\
copy /y copy_spacy_model.py temp_build\

:: Add dotenv file if it exists
if exist ".env" (
    echo Copying .env file to build directory
    copy /y .env temp_build\
)

:: Run the Python file generators
echo Creating main.py file...
python create_main.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to create main.py
    exit /b 1
)

echo Creating hook-src.py file...
python create_hook.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to create hook-src.py
    exit /b 1
)

:: Verify files were created
if not exist "temp_build\main.py" (
    echo ❌ main.py was not created properly
    exit /b 1
)
if not exist "temp_build\hook-src.py" (
    echo ❌ hook-src.py was not created properly
    exit /b 1
)

:: Run PyInstaller
echo Running PyInstaller...
cd temp_build

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

:: Verify build success
if exist "dist\%OUTPUT_NAME%.exe" (
    echo ✅ Build successful!
    
    :: Move executable to final location
    move "dist\%OUTPUT_NAME%.exe" "..\%TARGET_DIR%\"
    echo Final executable: %TARGET_DIR%\%OUTPUT_NAME%.exe
) else (
    echo ❌ Build failed! Check the logs above.
    exit /b 1
)

:: Clean up
cd ..
rmdir /s /q temp_build

echo Build process completed.