#!/bin/bash

# Set working directory to script location
cd "$(dirname "$0")"

# Configuration - adjusted to match new file structure
SRC_DIR="python"  # Adjusted path relative to assets/
MAIN_SCRIPT="${SRC_DIR}/wrapper.py"  # Now using the wrapper script
OUTPUT_NAME="processJson"
VENV_DIR=".venv"  # Adjusted path relative to assets/

# Vector model configuration - use existing directory in same location as build.sh
VECTOR_MODEL_PACKAGE="vector_model_package"  # Name of existing vector model directory

# Platform detection
PLATFORM_ID="darwin"  # This script is specifically for macOS
TARGET_DIR="../dist-${PLATFORM_ID}"  # Output to parent directory (project root)

echo "Starting build process from $(pwd) for platform: ${PLATFORM_ID}"

# Clean previous builds but preserve vector model package
echo "Cleaning up previous builds..."
rm -rf build dist "${TARGET_DIR}" spacy_model temp_build

# Verify vector model package exists
if [ ! -d "${VECTOR_MODEL_PACKAGE}" ]; then
    echo "❌ Vector model package directory '${VECTOR_MODEL_PACKAGE}' not found in $(pwd)"
    echo "Please ensure the vector model package is in the same directory as this script."
    exit 1
fi

# Ensure the target directory exists
mkdir -p "${TARGET_DIR}"

# Activate virtual environment if available
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "No virtual environment found. Using system Python."
fi

# Verify Python and dependencies
echo "Python environment information:"
python --version
pip list

# Ensure required packages are installed
echo "Ensuring required packages are installed..."
pip install certifi sentence-transformers contractions

# Verify spaCy and model are installed
echo "Verifying spaCy installation..."
python -c "import spacy; print(f'spaCy version: {spacy.__version__}')" || {
    echo "❌ spaCy not installed. Please install it with: pip install spacy"
    exit 1
}

python -c "import en_core_web_sm; print(f'Model path: {en_core_web_sm.__path__[0]}')" || {
    echo "❌ spaCy model 'en_core_web_sm' not installed. Installing now..."
    python -m spacy download en_core_web_sm
}

# Verify contractions package and check its data files
echo "Verifying contractions package..."
python -c "
import contractions
import os
import pkgutil
import json

# Check if data files exist
data = pkgutil.get_data('contractions', 'data/contractions_dict.json')
if data:
    print(f'✅ Successfully loaded contractions data file')
    # Parse the JSON to ensure it's valid
    json_data = json.loads(data)
    print(f'✅ Loaded contractions dictionary with {len(json_data)} items')
else:
    print('❌ Could not load contractions data file')
" || {
    echo "❌ Issues with contractions package. Attempting to reinstall..."
    pip uninstall -y contractions
    pip install contractions
}

# Prepare spaCy model files
echo "Preparing spaCy model files..."
mkdir -p spacy_model
python -c "
import shutil
import os
import en_core_web_sm

model_path = en_core_web_sm.__path__[0]
target_path = 'spacy_model/en_core_web_sm'

if os.path.exists(target_path):
    shutil.rmtree(target_path)

shutil.copytree(model_path, target_path)
print(f'Copied model from {model_path} to {target_path}')
" || {
    echo "❌ Failed to prepare spaCy model files"
    exit 1
}

# Check if compression is needed for the vector model
echo "Checking vector model package..."

# Check if model is already compressed
if [ -f "${VECTOR_MODEL_PACKAGE}/sentence_transformer.tar.gz" ]; then
    echo "✅ Vector model is already compressed"
else
    # Check if uncompressed model exists
    if [ -d "${VECTOR_MODEL_PACKAGE}/sentence_transformer" ]; then
        echo "Compressing sentence transformer model..."
        # Create a backup copy of the original directory
        TEMP_DIR=$(mktemp -d)
        cp -r "${VECTOR_MODEL_PACKAGE}/sentence_transformer" "${TEMP_DIR}/"
        
        # Compress the model
        cd "${VECTOR_MODEL_PACKAGE}"
        tar -czf sentence_transformer.tar.gz sentence_transformer/
        rm -rf sentence_transformer/
        cd ..
        
        echo "✅ Compressed sentence transformer model"
        
        # Move backup back to original location for continued use outside of packaging
        cp -r "${TEMP_DIR}/sentence_transformer" "${VECTOR_MODEL_PACKAGE}/"
        rm -rf "${TEMP_DIR}"
    else
        echo "⚠️ Neither compressed nor uncompressed model found in ${VECTOR_MODEL_PACKAGE}"
        echo "Checking contents of vector model package directory:"
        ls -la "${VECTOR_MODEL_PACKAGE}"
    fi
fi

# Verify required files exist in vector model package
echo "Verifying vector model package contents..."
REQUIRED_FILES_FOUND=true

if [ ! -f "${VECTOR_MODEL_PACKAGE}/category_embeddings.json" ]; then
    echo "⚠️ Warning: category_embeddings.json not found in vector model package"
    REQUIRED_FILES_FOUND=false
fi

if [ ! -f "${VECTOR_MODEL_PACKAGE}/sentence_transformer.tar.gz" ] && [ ! -d "${VECTOR_MODEL_PACKAGE}/sentence_transformer" ]; then
    echo "⚠️ Warning: Neither sentence_transformer directory nor compressed archive found"
    REQUIRED_FILES_FOUND=false
fi

if [ "$REQUIRED_FILES_FOUND" = false ]; then
    echo "⚠️ Some required files are missing from vector model package"
    echo "Continue anyway? (y/n)"
    read -r answer
    if [ "$answer" != "y" ]; then
        echo "Aborting build process."
        exit 1
    fi
    echo "Continuing build process despite missing files..."
fi

# Create temp directory for build
mkdir -p temp_build/src

# Copy all Python scripts to temp_build/src
cp -r "${SRC_DIR}"/*.py temp_build/src/

# Create a custom hook file for certifi
echo "Creating certifi hook for SSL certificate handling..."
cat > "temp_build/hook-certifi.py" << EOL
from PyInstaller.utils.hooks import collect_data_files
import certifi
import os

# This will collect all certifi's data files
datas = collect_data_files('certifi')

# Add the CA bundle specifically
datas.append((certifi.where(), 'certifi'))
EOL

# Create a hook for sentence_transformers
echo "Creating sentence_transformers hook..."
cat > "temp_build/hook-sentence_transformers.py" << EOL
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('sentence_transformers')

# Add specific modules that might be missed
hiddenimports.extend([
    'sentence_transformers.models',
    'torch',
    'transformers',
    'numpy',
])
EOL

# Create a hook for contractions package
echo "Creating contractions hook..."
cat > "temp_build/hook-contractions.py" << EOL
from PyInstaller.utils.hooks import collect_data_files, collect_all

# Collect all data files for contractions package
datas, binaries, hiddenimports = collect_all('contractions')

# Add explicit data file
import os
import contractions
import inspect

package_path = os.path.dirname(inspect.getfile(contractions))
data_path = os.path.join(package_path, 'data')

if os.path.exists(data_path):
    # Add all files in the data directory
    for file in os.listdir(data_path):
        full_path = os.path.join(data_path, file)
        if os.path.isfile(full_path):
            datas.append((full_path, os.path.join('contractions', 'data')))
            print(f"Added data file: {full_path}")
else:
    print(f"Warning: Contractions data directory not found at {data_path}")
EOL

# Create the spec file for PyInstaller to explicitly include processJson.py
echo "Creating PyInstaller spec file..."
cat > "temp_build/process.spec" << EOL
# -*- mode: python ; coding: utf-8 -*-
import certifi  # Import certifi for SSL certificate path
import os
import contractions
import inspect

block_cipher = None

# Get contractions package path and data files
contractions_path = os.path.dirname(inspect.getfile(contractions))
contractions_data_path = os.path.join(contractions_path, 'data')
contractions_dict_path = os.path.join(contractions_data_path, 'contractions_dict.json')
contractions_slang_path = os.path.join(contractions_data_path, 'slang_dict.json')

a = Analysis(
    ['src/wrapper.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/processJson.py', '.'),  # Explicitly include processJson.py in the root
        ('../spacy_model/en_core_web_sm', 'en_core_web_sm'),
        ('../${VECTOR_MODEL_PACKAGE}', '${VECTOR_MODEL_PACKAGE}'),
        (certifi.where(), 'certifi'),  # Include SSL certificates
        (contractions_dict_path, os.path.join('contractions', 'data')),  # Include contractions dictionary
        (contractions_slang_path, os.path.join('contractions', 'data')),  # Include slang dictionary
    ],
    hiddenimports=[
        'en_core_web_sm',
        'src.frameExtraction',
        'src.videoAnalysis',
        'src.imageAnalysis',
        'src.aiLoader',
        'src.helpers',
        'src.cleanJson',
        'src.vectorImplementation',
        'src.processJson',
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
        'tempfile',
        'subprocess',
        'openai',
        'spacy',
        'sentence_transformers',
        'certifi',
        'tarfile',
        'contractions',
        'contractions.contractions',
        'contractions.data',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='${OUTPUT_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
)
EOL

# Run PyInstaller
echo "Running PyInstaller..."
cd temp_build

# Create a custom hook file for module dependencies 
cat > "hook-src.py" << EOL
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all for important packages
datas, binaries, hiddenimports = collect_all('spacy')
datas2, binaries2, hiddenimports2 = collect_all('openai')
datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')
datas4, binaries4, hiddenimports4 = collect_all('certifi')
datas5, binaries5, hiddenimports5 = collect_all('contractions')

# Combine all collected items
datas.extend(datas2)
datas.extend(datas3)
datas.extend(datas4)
datas.extend(datas5)
binaries.extend(binaries2)
binaries.extend(binaries3)
binaries.extend(binaries4)
binaries.extend(binaries5)
hiddenimports.extend(hiddenimports2)
hiddenimports.extend(hiddenimports3)
hiddenimports.extend(hiddenimports4)
hiddenimports.extend(hiddenimports5)

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
    'src.processJson',
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
    'tempfile',
    'subprocess',
    'certifi',
    'tarfile',
    'sentence_transformers.models',
    'contractions',
    'contractions.contractions',
])
EOL

# Run PyInstaller with the spec file
pyinstaller --clean --log-level=INFO process.spec

# Verify build success
if [ -f "dist/${OUTPUT_NAME}" ]; then
    echo "✅ Build successful!"
    
    # Create target directory if it doesn't exist
    mkdir -p "${TARGET_DIR}"
    
    # Move executable to final location
    mv "dist/${OUTPUT_NAME}" "${TARGET_DIR}/"
    chmod +x "${TARGET_DIR}/${OUTPUT_NAME}"
    
    echo "Final executable: ${TARGET_DIR}/${OUTPUT_NAME}"
    
    # Create a file listing all required files/directories for Electron packaging
    echo "Creating electron-assets.json for Electron packager..."
    cat > "../electron-assets.json" << EOL
{
  "pyInstaller": {
    "executablePath": "dist-${PLATFORM_ID}/${OUTPUT_NAME}",
    "platform": "${PLATFORM_ID}"
  }
}
EOL

    # Also create a copy in the project root
    cat > "../../electron-assets.json" << EOL
{
  "pyInstaller": {
    "executablePath": "dist-${PLATFORM_ID}/${OUTPUT_NAME}",
    "platform": "${PLATFORM_ID}"
  }
}
EOL
else
    echo "❌ Build failed! Check the logs above."
    exit 1
fi

# Clean up
cd ..
rm -rf temp_build build dist

echo "Build process completed."