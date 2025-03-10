@echo off
:: Verify prerequisites, Python environment and dependencies

:: Verify vector model package exists
if not exist "%VECTOR_MODEL_PACKAGE%" (
    echo ❌ Vector model package directory '%VECTOR_MODEL_PACKAGE%' not found in %cd%
    echo Please ensure the vector model package is in the same directory as this script.
    exit /b 1
)

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