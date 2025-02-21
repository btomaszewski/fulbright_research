#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Activate the virtual environment
source venv/bin/activate

# Run PyInstaller to package main.py as a single executable
pyinstaller --onefile python/processJson.py

# Create the dist folder if it doesn't exist
mkdir -p ../python-scripts

# Move the compiled binary to the Electron project directory
mv dist/main ../python-scripts/main-mac

# Clean up unnecessary PyInstaller files
rm -rf build dist __pycache__ main.spec

echo "✅ Build complete! Executable moved to python-scripts/"