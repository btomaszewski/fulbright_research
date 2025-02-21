#!/bin/bash
set -e  # Exit on error


# Activate the virtual environment
source .venv/bin/activate

# Run PyInstaller to package processJson.py
pyinstaller --onefile python/processJson.py

# Create the dist folder if it doesn't exist
mkdir -p python-scripts

# Move the compiled binary to the Electron project directory
mv dist/processJson python-scripts/processJson-mac

# Clean up unnecessary PyInstaller files
rm -rf build dist __pycache__ processJson.spec

echo "✅ Build complete! Executable moved to python-scripts/"