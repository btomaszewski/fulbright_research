@echo off
setlocal enabledelayedexpansion

REM Set working directory to where the script is located (assets folder)
cd /d "%~dp0"

REM Configuration
set PYTHON_DIR=python
set MAIN_SCRIPT=%PYTHON_DIR%\processJson.py
set OUTPUT_NAME=processJson
set VENV_DIR=.venv

echo Starting build process from %cd%

REM Clean up any previous builds
echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /f /q *.spec

REM Clean up any previous python-scripts output
echo Cleaning up previous python-scripts output...
if exist python-scripts rmdir /s /q python-scripts

REM Verify directory structure
if not exist "%PYTHON_DIR%" (
    echo Error: Python directory not found at: %PYTHON_DIR%
    exit /b 1
)

if not exist "%MAIN_SCRIPT%" (
    echo Error: Main script not found at: %MAIN_SCRIPT%
    exit /b 1
)

REM Activate virtual environment
if not exist "%VENV_DIR%" (
    echo Error: Virtual environment not found at: %VENV_DIR%
    exit /b 1
)
call "%VENV_DIR%\Scripts\activate.bat"

REM Find all Python files in the python directory
echo Scanning for Python modules in %PYTHON_DIR%...
set MODULE_NAMES=
for /r "%PYTHON_DIR%" %%F in (*.py) do (
    set "filepath=%%F"
    set "filename=%%~nxF"
    if not "!filename!"=="processJson.py" (
        REM Convert file path to module name
        set "module=!filepath:%CD%\%PYTHON_DIR%\=!"
        set "module=!module:.py=!"
        set "module=!module:\=.!"
        echo Found module: !module!
        set "MODULE_NAMES=!MODULE_NAMES!        '!module!',!CR!"
    )
)

REM Remove trailing comma
set "MODULE_NAMES=!MODULE_NAMES:~0,-2!"

REM Set platform-specific identifier
set PLATFORM_NAME=processJson-win

REM Get spaCy model path and ensure it's installed
echo Checking spaCy model...
python -c "import spacy; spacy.cli.download('en_core_web_sm') if not spacy.util.is_package('en_core_web_sm') else print('SpaCy model already installed')"
for /f "delims=" %%i in ('python -c "import spacy; print(spacy.util.get_package_path('en_core_web_sm'))"') do set SPACY_MODEL_PATH=%%i
echo Using spaCy model path: %SPACY_MODEL_PATH%

REM Create spacy_model directory
echo Creating spaCy model directory...
if not exist "assets\spacy_model" mkdir "assets\spacy_model"

REM Copy spaCy model using the Python script
echo Copying spaCy model to project directory...
python copy_spacy_model.py
if %ERRORLEVEL% neq 0 (
    echo Failed to copy spaCy model
    exit /b 1
)

REM Create spec file with discovered modules and include spaCy model
echo Creating PyInstaller spec file...
(
echo # -*- mode: python ; coding: utf-8 -*-
echo import os
echo import sys
echo from PyInstaller.utils.hooks import collect_data_files, collect_submodules
echo.
echo # Get all spaCy language modules
echo spacy_imports = collect_submodules('spacy'^)
echo spacy_data = collect_data_files('spacy'^)
echo.
echo # Add specific model
echo model_name = 'en_core_web_sm'
echo model_imports = []
echo try:
echo     # Try to collect model submodules
echo     model_imports = collect_submodules(model_name^)
echo except ImportError:
echo     print(f"Warning: Could not collect submodules for {model_name}"^)
echo.
echo # Define main analysis
echo a = Analysis(
echo     ['%MAIN_SCRIPT:\=/%'],
echo     pathex=['%PYTHON_DIR:\=/%'],
echo     binaries=[],
echo     datas=[
echo         ('%PYTHON_DIR:\=/%/*', '.'^),
echo         ('assets/spacy_model/en_core_web_sm', 'en_core_web_sm'^),
echo         ('vector_model_package/sentence_transformer', 'vector_model_package/sentence_transformer'^),
echo         ('vector_model_package/category_embeddings.json', 'vector_model_package/category_embeddings.json'^),
echo     ] + spacy_data,
echo     hiddenimports=[
echo         'numpy',
echo         'numpy.core.multiarray',
echo         'numpy.core.numeric',
echo         'numpy.core.umath',
echo         'sklearn',
echo         'pandas',
echo         'spacy',
echo         'spacy.language',
echo         'spacy.lang.en',
echo         'spacy.pipeline',
echo         'spacy.tokens',
echo         'spacy.tokens.underscore',
echo         'spacy.lexeme',
echo         'spacy.util',
echo         'spacy.displacy',
echo         'spacy.scorer',
echo         'spacy.gold',
echo         'spacy.kb',
echo         'spacy.matcher',
echo         'spacy.tokenizer',
echo         'thinc',
echo         'cymem',
echo         'preshed',
echo         'blis',
echo         'murmurhash',
echo         'wasabi',
echo         'srsly',
echo         'catalogue',
echo         'thinc.layers',
echo         'thinc.loss',
echo         'thinc.optimizers',
echo         'thinc.model',
echo         'thinc.config',
echo         'transformers',
echo         'sentence_transformers',
echo         'en_core_web_sm',
echo         # Local module imports
echo %MODULE_NAMES%
echo     ] + spacy_imports + model_imports,
echo     hookspath=[],
echo     hooksconfig={},
echo     runtime_hooks=[],
echo     excludes=[],
echo     noarchive=False,
echo ^)
echo.
echo pyz = PYZ(a.pure^)
echo.
echo exe = EXE(
echo     pyz,
echo     a.scripts,
echo     [],
echo     exclude_binaries=True,
echo     name='%OUTPUT_NAME%',
echo     debug=False,
echo     bootloader_ignore_signals=False,
echo     strip=False,
echo     upx=True,
echo     console=True,
echo     disable_windowed_traceback=False,
echo     argv_emulation=False,
echo     target_arch=None,
echo     codesign_identity=None,
echo     entitlements_file=None,
echo ^)
echo.
echo coll = COLLECT(
echo     exe,
echo     a.binaries,
echo     a.datas,
echo     strip=False,
echo     upx=True,
echo     upx_exclude=[],
echo     name='%OUTPUT_NAME%',
echo ^)
) > "%OUTPUT_NAME%.spec"

REM Run PyInstaller with the spec file
echo Starting PyInstaller build...
pyinstaller "%OUTPUT_NAME%.spec" --noconfirm

REM Check if build was successful
if exist "dist\%OUTPUT_NAME%" (
    echo Build successful! Executable is in dist\%OUTPUT_NAME%\
    
    REM Create output directory structure that matches the path in JavaScript
    set TARGET_DIR=python-scripts\%PLATFORM_NAME%
    echo Creating directory: %TARGET_DIR%
    if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
    
    REM Copy build to final location
    echo Copying executable to: %TARGET_DIR%
    xcopy /s /e /i /y "dist\%OUTPUT_NAME%\*" "%TARGET_DIR%"
    
    REM Verify executable exists
    if exist "%TARGET_DIR%\%OUTPUT_NAME%.exe" (
        echo ✅ Executable confirmed at %TARGET_DIR%\%OUTPUT_NAME%.exe
    ) else (
        echo ❌ Warning: Executable not found at expected location!
        echo Looking for executable in the target directory...
        dir /s /b "%TARGET_DIR%\*.exe"
    )
    
    REM Verify spaCy model was included in the build
    echo Checking for spaCy model in the build...
    if exist "%TARGET_DIR%\en_core_web_sm" (
        echo ✅ spaCy model confirmed at %TARGET_DIR%\en_core_web_sm
    ) else (
        echo ❌ Warning: spaCy model not found in expected location!
        echo Looking for spaCy model in the target directory...
        dir /s /b /ad "%TARGET_DIR%\*en_core_web_sm*"
    )
    
    echo Final executable location: %TARGET_DIR%\%OUTPUT_NAME%.exe
    echo Contents of final directory:
    dir "%TARGET_DIR%"
    
    REM Print the directory structure to help debug issues
    echo Directory structure of final package:
    dir /s /b "%TARGET_DIR%" | findstr /v "__pycache__" | sort
) else (
    echo Build failed!
    exit /b 1
)

endlocal

