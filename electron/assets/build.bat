@echo off
setlocal enabledelayedexpansion

:: Set working directory to script location
cd /d "%~dp0"

:: Configuration - adjusted to match new file structure
set SRC_DIR=python
set MAIN_SCRIPT=%SRC_DIR%\wrapper.py
set OUTPUT_NAME=processJson
set VENV_DIR=.venv

:: Vector model configuration - use existing directory in same location as build.bat
set VECTOR_MODEL_PACKAGE=vector_model_package
set NER_MODEL_PACKAGE=ner_model_package

:: Platform detection
set PLATFORM_ID=win32
set TARGET_DIR=..\dist-%PLATFORM_ID%

echo Starting build process from %cd% for platform: %PLATFORM_ID%

:: Clean previous builds but preserve vector model package
echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
if exist spacy_model rmdir /s /q spacy_model
if exist temp_build rmdir /s /q temp_build

:: Verify vector model package exists
if not exist "%VECTOR_MODEL_PACKAGE%" (
    echo ❌ Vector model package directory '%VECTOR_MODEL_PACKAGE%' not found in %cd%
    echo Please ensure the vector model package is in the same directory as this script.
    exit /b 1
)

:: Ensure the target directory exists
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

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

:: Ensure required packages are installed
echo Ensuring required packages are installed...
pip install certifi sentence-transformers contractions spacy geopy

:: Verify spaCy and model are installed
echo Verifying spaCy installation...
python -c "import spacy; print(f'spaCy version: {spacy.__version__}')" || (
    echo ❌ spaCy not installed. Please install it with: pip install spacy
    exit /b 1
)

python -c "import en_core_web_sm; print(f'Model path: {en_core_web_sm.__path__[0]}')" || (
    echo ❌ spaCy model 'en_core_web_sm' not installed. Installing now...
    python -m spacy download en_core_web_sm
)

:: Verify contractions package and check its data files
echo Verifying contractions package...
python -c "import contractions; import os; import pkgutil; import json; data = pkgutil.get_data('contractions', 'data/contractions_dict.json'); print('✅ Successfully loaded contractions data file') if data else print('❌ Could not load contractions data file'); json_data = json.loads(data) if data else {}; print(f'✅ Loaded contractions dictionary with {len(json_data)} items') if data else print('')" || (
    echo ❌ Issues with contractions package. Attempting to reinstall...
    pip uninstall -y contractions
    pip install contractions
)

:: Package spaCy model files as a tarball
echo Packaging spaCy model files...
if not exist spacy_model mkdir spacy_model
python -c "import shutil; import os; import tarfile; import en_core_web_sm; import sys; model_path = en_core_web_sm.__path__[0]; target_dir = 'spacy_model'; os.makedirs(target_dir, exist_ok=True); tarball_path = os.path.join(target_dir, 'en_core_web_sm.tar.gz'); print(f'Original model path: {model_path}'); print('Files in original model directory:'); [print(f'  {os.path.join(os.path.relpath(root, model_path), file)}') for root, dirs, files in os.walk(model_path) for file in files]; original_dir = os.getcwd(); try: os.chdir(model_path); with tarfile.open(os.path.join(original_dir, tarball_path), 'w:gz') as tar: [tar.add(os.path.join(root, file), arcname=os.path.join(os.path.relpath(root, '.'), file)) for root, dirs, files in os.walk('.') for file in files]; finally: os.chdir(original_dir); print(f'Created spaCy model tarball at {tarball_path}'); print(f'Tarball size: {os.path.getsize(tarball_path) / 1024 / 1024:.2f} MB'); print('Contents of the spaCy model tarball:'); [print(f'  {member.name} ({member.size} bytes)') for member in tarfile.open(tarball_path, 'r:gz').getmembers()]" || (
    echo ❌ Failed to package spaCy model files
    exit /b 1
)

:: Check vector model package
echo Checking vector model package...
if exist "%VECTOR_MODEL_PACKAGE%\sentence_transformer.tar.gz" (
    echo ✅ Vector model is already compressed
) else (
    :: Check if uncompressed model exists
    if exist "%VECTOR_MODEL_PACKAGE%\sentence_transformer" (
        echo Compressing sentence transformer model...
        
        :: Create a temporary directory for backup
        set "TEMP_DIR=%TEMP%\temp_model_%RANDOM%"
        mkdir "%TEMP_DIR%"
        xcopy /E /I /Q "%VECTOR_MODEL_PACKAGE%\sentence_transformer" "%TEMP_DIR%\sentence_transformer"
        
        :: Compress the model using Python since Windows doesn't have tar natively
        cd "%VECTOR_MODEL_PACKAGE%"
        python -c "import tarfile; import os; with tarfile.open('sentence_transformer.tar.gz', 'w:gz') as tar: [tar.add(os.path.join(root, file), arcname=os.path.join('sentence_transformer', os.path.relpath(os.path.join(root, file), 'sentence_transformer'))) for root, dirs, files in os.walk('sentence_transformer') for file in files]"
        cd ..
        
        :: Clean up original directory after compression
        rmdir /s /q "%VECTOR_MODEL_PACKAGE%\sentence_transformer"
        
        echo ✅ Compressed sentence transformer model
        
        :: Move backup back to original location for continued use outside of packaging
        xcopy /E /I /Q "%TEMP_DIR%\sentence_transformer" "%VECTOR_MODEL_PACKAGE%\sentence_transformer"
        rmdir /s /q "%TEMP_DIR%"
    ) else (
        echo ⚠️ Neither compressed nor uncompressed model found in %VECTOR_MODEL_PACKAGE%
        echo Checking contents of vector model package directory:
        dir "%VECTOR_MODEL_PACKAGE%"
    )
)

:: Handle NER model
echo Checking NER model package...
if not exist "%NER_MODEL_PACKAGE%" (
    echo ⚠️ NER model package directory '%NER_MODEL_PACKAGE%' not found in %cd%
    set /p answer=Do you want to continue without the NER model? (y/n)
    if /i not "%answer%"=="y" (
        echo Aborting build process.
        exit /b 1
    )
    echo Continuing build process without NER model...
) else (
    :: Check if model structure is correct
    echo Checking NER model structure...
    dir "%NER_MODEL_PACKAGE%"
    
    :: Check if meta.json exists - this is critical for spaCy models
    if exist "%NER_MODEL_PACKAGE%\meta.json" (
        echo ✅ Found meta.json in NER model package
        
        :: Create a proper compressed model tarball
        echo Creating NER model tarball...
        
        :: Create a clean temporary directory with just the model files
        set "TEMP_NER_DIR=%TEMP%\ner_model_%RANDOM%"
        mkdir "%TEMP_NER_DIR%"
        
        :: Copy required files to temp directory
        if exist "%NER_MODEL_PACKAGE%\meta.json" copy "%NER_MODEL_PACKAGE%\meta.json" "%TEMP_NER_DIR%\"
        if exist "%NER_MODEL_PACKAGE%\config.cfg" copy "%NER_MODEL_PACKAGE%\config.cfg" "%TEMP_NER_DIR%\"
        if exist "%NER_MODEL_PACKAGE%\tokenizer" xcopy /E /I /Q "%NER_MODEL_PACKAGE%\tokenizer" "%TEMP_NER_DIR%\tokenizer"
        if exist "%NER_MODEL_PACKAGE%\vocab" xcopy /E /I /Q "%NER_MODEL_PACKAGE%\vocab" "%TEMP_NER_DIR%\vocab"
        
        :: Copy ner directory if it exists
        if exist "%NER_MODEL_PACKAGE%\ner" xcopy /E /I /Q "%NER_MODEL_PACKAGE%\ner" "%TEMP_NER_DIR%\ner"
        
        :: Create tarball from temp directory using Python
        cd "%TEMP_NER_DIR%"
        python -c "import tarfile; import os; with tarfile.open('ner_model.tar.gz', 'w:gz') as tar: [tar.add(item) for item in os.listdir('.') if os.path.isfile(item) or os.path.isdir(item)]"
        move "ner_model.tar.gz" "%cd%\..\%NER_MODEL_PACKAGE%\"
        cd ..
        
        :: Clean up
        rmdir /s /q "%TEMP_NER_DIR%"
        
        echo ✅ Created NER model tarball at %NER_MODEL_PACKAGE%\ner_model.tar.gz
    ) else (
        echo ⚠️ No meta.json found in NER model package. This will likely cause loading errors.
        set /p answer=Do you want to continue anyway? (y/n)
        if /i not "%answer%"=="y" (
            echo Aborting build process.
            exit /b 1
        )
    )
)

:: Verify required files for vector model
echo Verifying vector model package contents...
set REQUIRED_FILES_FOUND=true

if not exist "%VECTOR_MODEL_PACKAGE%\category_embeddings.json" (
    echo ⚠️ Warning: category_embeddings.json not found in vector model package
    set REQUIRED_FILES_FOUND=false
)

if not exist "%VECTOR_MODEL_PACKAGE%\sentence_transformer.tar.gz" (
    if not exist "%VECTOR_MODEL_PACKAGE%\sentence_transformer" (
        echo ⚠️ Warning: Neither sentence_transformer directory nor compressed archive found
        set REQUIRED_FILES_FOUND=false
    )
)

if "%REQUIRED_FILES_FOUND%"=="false" (
    echo ⚠️ Some required files are missing from vector model package
    set /p answer=Continue anyway? (y/n)
    if /i not "%answer%"=="y" (
        echo Aborting build process.
        exit /b 1
    )
    echo Continuing build process despite missing files...
)

:: Create temp directory for build
if not exist temp_build\src mkdir temp_build\src

:: Copy all Python scripts to temp_build/src
xcopy /Y "%SRC_DIR%\*.py" "temp_build\src\"

:: Create a custom hook file for certifi
echo Creating certifi hook for SSL certificate handling...
echo from PyInstaller.utils.hooks import collect_data_files> "temp_build\hook-certifi.py"
echo import certifi>> "temp_build\hook-certifi.py"
echo import os>> "temp_build\hook-certifi.py"
echo.>> "temp_build\hook-certifi.py"
echo # This will collect all certifi's data files>> "temp_build\hook-certifi.py"
echo datas = collect_data_files('certifi')>> "temp_build\hook-certifi.py"
echo.>> "temp_build\hook-certifi.py"
echo # Add the CA bundle specifically>> "temp_build\hook-certifi.py"
echo datas.append((certifi.where(), 'certifi'))>> "temp_build\hook-certifi.py"

:: Create a hook for sentence_transformers
echo Creating sentence_transformers hook...
echo from PyInstaller.utils.hooks import collect_all> "temp_build\hook-sentence_transformers.py"
echo.>> "temp_build\hook-sentence_transformers.py"
echo datas, binaries, hiddenimports = collect_all('sentence_transformers')>> "temp_build\hook-sentence_transformers.py"
echo.>> "temp_build\hook-sentence_transformers.py"
echo # Add specific modules that might be missed>> "temp_build\hook-sentence_transformers.py"
echo hiddenimports.extend([>> "temp_build\hook-sentence_transformers.py"
echo     'sentence_transformers.models',>> "temp_build\hook-sentence_transformers.py"
echo     'torch',>> "temp_build\hook-sentence_transformers.py"
echo     'transformers',>> "temp_build\hook-sentence_transformers.py"
echo     'numpy',>> "temp_build\hook-sentence_transformers.py"
echo ])>> "temp_build\hook-sentence_transformers.py"

:: Create a hook for contractions package
echo Creating contractions hook...
echo from PyInstaller.utils.hooks import collect_data_files, collect_all> "temp_build\hook-contractions.py"
echo.>> "temp_build\hook-contractions.py"
echo # Collect all data files for contractions package>> "temp_build\hook-contractions.py"
echo datas, binaries, hiddenimports = collect_all('contractions')>> "temp_build\hook-contractions.py"
echo.>> "temp_build\hook-contractions.py"
echo # Add explicit data file>> "temp_build\hook-contractions.py"
echo import os>> "temp_build\hook-contractions.py"
echo import contractions>> "temp_build\hook-contractions.py"
echo import inspect>> "temp_build\hook-contractions.py"
echo.>> "temp_build\hook-contractions.py"
echo package_path = os.path.dirname(inspect.getfile(contractions))>> "temp_build\hook-contractions.py"
echo data_path = os.path.join(package_path, 'data')>> "temp_build\hook-contractions.py"
echo.>> "temp_build\hook-contractions.py"
echo if os.path.exists(data_path):>> "temp_build\hook-contractions.py"
echo     # Add all files in the data directory>> "temp_build\hook-contractions.py"
echo     for file in os.listdir(data_path):>> "temp_build\hook-contractions.py"
echo         full_path = os.path.join(data_path, file)>> "temp_build\hook-contractions.py"
echo         if os.path.isfile(full_path):>> "temp_build\hook-contractions.py"
echo             datas.append((full_path, os.path.join('contractions', 'data')))>> "temp_build\hook-contractions.py"
echo             print(f"Added data file: {full_path}")>> "temp_build\hook-contractions.py"
echo else:>> "temp_build\hook-contractions.py"
echo     print(f"Warning: Contractions data directory not found at {data_path}")>> "temp_build\hook-contractions.py"

:: Create hook for geopy
echo Creating geopy hook...
echo from PyInstaller.utils.hooks import collect_all> "temp_build\hook-geopy.py"
echo.>> "temp_build\hook-geopy.py"
echo datas, binaries, hiddenimports = collect_all('geopy')>> "temp_build\hook-geopy.py"
echo.>> "temp_build\hook-geopy.py"
echo # Add specific modules that might be missed>> "temp_build\hook-geopy.py"
echo hiddenimports.extend([>> "temp_build\hook-geopy.py"
echo     'geopy.geocoders',>> "temp_build\hook-geopy.py"
echo     'geopy.geocoders.nominatim',>> "temp_build\hook-geopy.py"
echo ])>> "temp_build\hook-geopy.py"

:: Create the spec file for PyInstaller
echo Creating PyInstaller spec file...

:: Generate process.spec file
(
    echo # -*- mode: python ; coding: utf-8 -*-
    echo import certifi  # Import certifi for SSL certificate path
    echo import os
    echo import contractions
    echo import inspect
    echo.
    echo block_cipher = None
    echo.
    echo # Get contractions package path and data files
    echo contractions_path = os.path.dirname^(inspect.getfile^(contractions^)^)
    echo contractions_data_path = os.path.join^(contractions_path, 'data'^)
    echo contractions_dict_path = os.path.join^(contractions_data_path, 'contractions_dict.json'^)
    echo contractions_slang_path = os.path.join^(contractions_data_path, 'slang_dict.json'^)
    echo.
    echo # Path to this spec file's directory
    echo spec_dir = os.path.dirname^(os.path.abspath^(SPEC^)^)
    echo.
    echo # Define paths relative to spec file
    echo vector_model_path = os.path.join^(spec_dir, '..', '%VECTOR_MODEL_PACKAGE%'^)
    echo ner_model_path = os.path.join^(spec_dir, '..', '%NER_MODEL_PACKAGE%'^)
    echo spacy_model_tarball = os.path.join^(spec_dir, '..', 'spacy_model/en_core_web_sm.tar.gz'^)
    echo.
    echo a = Analysis^(
    echo     ['src/wrapper.py'],
    echo     pathex=['src'],
    echo     binaries=[],
    echo     datas=[
    echo         ^('src/processJson.py', '.'^),  # Explicitly include processJson.py in the root
    echo         ^(spacy_model_tarball, '.'^),  # Include spaCy model as a tarball in the root
    echo         ^(vector_model_path, '%VECTOR_MODEL_PACKAGE%'^),
    echo         ^(ner_model_path, '%NER_MODEL_PACKAGE%'^),
    echo         ^(certifi.where^(^), 'certifi'^),  # Include SSL certificates
    echo         ^(contractions_dict_path, os.path.join^('contractions', 'data'^)^),  # Include contractions dictionary
    echo         ^(contractions_slang_path, os.path.join^('contractions', 'data'^)^),  # Include slang dictionary
    echo     ],
    echo     hiddenimports=[
    echo         'en_core_web_sm',
    echo         'src.frameExtraction',
    echo         'src.videoAnalysis',
    echo         'src.imageAnalysis',
    echo         'src.aiLoader',
    echo         'src.helpers',
    echo         'src.cleanJson',
    echo         'src.vectorImplementation',
    echo         'src.nerImplementation',
    echo         'src.processJson',
    echo         'dotenv',
    echo         'numpy',
    echo         'pandas',
    echo         'json',
    echo         'pathlib', 
    echo         'shutil',
    echo         'torch',
    echo         'transformers',
    echo         'PIL',
    echo         'cv2',
    echo         'tempfile',
    echo         'subprocess',
    echo         'openai',
    echo         'spacy',
    echo         'geopy',
    echo         'geopy.geocoders',
    echo         'geopy.geocoders.nominatim',
    echo         'sentence_transformers',
    echo         'certifi',
    echo         'tarfile',
    echo         'contractions',
    echo         'contractions.contractions',
    echo         'contractions.data',
    echo         'logging',
    echo     ],
    echo     hookspath=['.'],
    echo     hooksconfig={},
    echo     runtime_hooks=[],
    echo     excludes=[],
    echo     win_no_prefer_redirects=False,
    echo     win_private_assemblies=False,
    echo     cipher=block_cipher,
    echo     noarchive=False,
    echo ^)
    echo.
    echo pyz = PYZ^(a.pure, a.zipped_data, cipher=block_cipher^)
    echo.
    echo exe = EXE^(
    echo     pyz,
    echo     a.scripts,
    echo     a.binaries,
    echo     a.zipfiles,
    echo     a.datas,
    echo     name='%OUTPUT_NAME%',
    echo     debug=False,
    echo     bootloader_ignore_signals=False,
    echo     strip=False,
    echo     upx=True,
    echo     upx_exclude=[],
    echo     runtime_tmpdir=None,
    echo     console=True,
    echo     disable_windowed_traceback=False,
    echo ^)
) > "temp_build\process.spec"

:: Run PyInstaller
echo Running PyInstaller...
cd temp_build

:: Create a custom hook file for module dependencies 
(
    echo from PyInstaller.utils.hooks import collect_all, collect_submodules
    echo.
    echo # Collect all for important packages
    echo datas, binaries, hiddenimports = collect_all^('spacy'^)
    echo datas2, binaries2, hiddenimports2 = collect_all^('openai'^)
    echo datas3, binaries3, hiddenimports3 = collect_all^('sentence_transformers'^)
    echo datas4, binaries4, hiddenimports4 = collect_all^('certifi'^)
    echo datas5, binaries5, hiddenimports5 = collect_all^('contractions'^)
    echo datas6, binaries6, hiddenimports6 = collect_all^('geopy'^)
    echo.
    echo # Combine all collected items
    echo datas.extend^(datas2^)
    echo datas.extend^(datas3^)
    echo datas.extend^(datas4^)
    echo datas.extend^(datas5^)
    echo datas.extend^(datas6^)
    echo binaries.extend^(binaries2^)
    echo binaries.extend^(binaries3^)
    echo binaries.extend^(binaries4^)
    echo binaries.extend^(binaries5^)
    echo binaries.extend^(binaries6^)
    echo hiddenimports.extend^(hiddenimports2^)
    echo hiddenimports.extend^(hiddenimports3^)
    echo hiddenimports.extend^(hiddenimports4^)
    echo hiddenimports.extend^(hiddenimports5^)
    echo hiddenimports.extend^(hiddenimports6^)
    echo.
    echo # Add more specific hidden imports
    echo hiddenimports.extend^([
    echo     'en_core_web_sm',
    echo     'src.frameExtraction',
    echo     'src.videoAnalysis',
    echo     'src.imageAnalysis',
    echo     'src.aiLoader',
    echo     'src.helpers',
    echo     'src.cleanJson',
    echo     'src.vectorImplementation',
    echo     'src.nerImplementation',
    echo     'src.processJson',
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
    echo     'tempfile',
    echo     'subprocess',
    echo     'certifi',
    echo     'tarfile',
    echo     'sentence_transformers.models',
    echo     'contractions',
    echo     'contractions.contractions',
    echo     'geopy',
    echo     'geopy.geocoders',
    echo     'geopy.geocoders.nominatim',
    echo     'logging',
    echo ]^)
) > "hook-src.py"

:: Run PyInstaller with the spec file
pyinstaller --clean --log-level=INFO process.spec

:: Verify build success
if exist "dist\%OUTPUT_NAME%.exe" (
    echo ✅ Build successful!
    
    :: Create target directory if it doesn't exist
    if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
    
    :: Move executable to final location
    move "dist\%OUTPUT_NAME%.exe" "%TARGET_DIR%\"
    
    echo Final executable: %TARGET_DIR%\%OUTPUT_NAME%.exe
    
    :: Create a file listing all required files/directories for Electron packaging
    echo Creating electron-assets.json for Electron packager...
    (
        echo {
        echo   "pyInstaller": {
        echo     "executablePath": "dist-%PLATFORM_ID%/%OUTPUT_NAME%.exe",
        echo     "platform": "%PLATFORM_ID%"
        echo   }
        echo }
    ) > "..\electron-assets.json"

    :: Also create a copy in the project root
    (
        echo {
        echo   "pyInstaller": {
        echo     "executablePath": "dist-%PLATFORM_ID%/%OUTPUT_NAME%.exe",
        echo     "platform": "%PLATFORM_ID%"
        echo   }
        echo }
    ) > "..\..\electron-assets.json"
) else (
    echo ❌ Build failed! Check the logs above.
    exit /b 1
)

:: Clean up
cd ..
rmdir /s /q temp_build build dist

echo Build process completed.