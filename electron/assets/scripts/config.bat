@echo off
:: Configuration settings for the build process

:: Core configuration
set SRC_DIR=python
set MAIN_SCRIPT=%SRC_DIR%\wrapper.py
set OUTPUT_NAME=processJson
set VENV_DIR=.venv

:: Model configuration
set VECTOR_MODEL_PACKAGE=vector_model_package
set NER_MODEL_PACKAGE=ner_model_package

:: Platform detection
set PLATFORM_ID=win32
set TARGET_DIR=..\dist-%PLATFORM_ID%

:: Temporary build directories
set TEMP_BUILD_DIR=temp_build
set SPACY_MODEL_DIR=spacy_model