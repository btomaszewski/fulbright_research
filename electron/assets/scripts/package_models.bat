@echo off
:: Package spaCy model files and verify model packages

:: Package spaCy model files as a tarball
echo Packaging spaCy model files...
if not exist "%SPACY_MODEL_DIR%" mkdir "%SPACY_MODEL_DIR%"
python -c "import shutil; import os; import tarfile; import en_core_web_sm; import sys; model_path = en_core_web_sm.__path__[0]; target_dir = '%SPACY_MODEL_DIR%'; os.makedirs(target_dir, exist_ok=True); tarball_path = os.path.join(target_dir, 'en_core_web_sm.tar.gz'); print(f'Original model path: {model_path}'); print('Files in original model directory:'); [print(f'  {os.path.join(os.path.relpath(root, model_path), file)}') for root, dirs, files in os.walk(model_path) for file in files]; original_dir = os.getcwd(); try: os.chdir(model_path); with tarfile.open(os.path.join(original_dir, tarball_path), 'w:gz') as tar: [tar.add(os.path.join(root, file), arcname=os.path.join(os.path.relpath(root, '.'), file)) for root, dirs, files in os.walk('.') for file in files]; finally: os.chdir(original_dir); print(f'Created spaCy model tarball at {tarball_path}'); print(f'Tarball size: {os.path.getsize(tarball_path) / 1024 / 1024:.2f} MB'); print('Contents of the spaCy model tarball:'); [print(f'  {member.name} ({member.size} bytes)') for member in tarfile.open(tarball_path, 'r:gz').getmembers()]" || (
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