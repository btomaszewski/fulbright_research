@echo off
:: Clean previous builds but preserve vector model package

echo Cleaning up previous builds...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
if exist "%SPACY_MODEL_DIR%" rmdir /s /q "%SPACY_MODEL_DIR%"
if exist "%TEMP_BUILD_DIR%" rmdir /s /q "%TEMP_BUILD_DIR%"

:: Ensure the target directory exists
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"