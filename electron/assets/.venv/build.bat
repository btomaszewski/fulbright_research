@echo off
setlocal enabledelayedexpansion
echo 🚀 Starting Windows build...

:: Activate the virtual environment
call venv\Scripts\activate

:: Run PyInstaller to package main.py
pyinstaller --onefile python\processJson.py

:: Create the dist folder if it doesn't exist
if not exist ..\python-scripts mkdir ..\python-scripts

:: Move the compiled binary to the Electron project directory
move /Y dist\main.exe ..\python-scripts\main-win.exe

:: Clean up unnecessary PyInstaller files
rmdir /S /Q build
rmdir /S /Q dist
del main.spec

echo ✅ Build complete! Executable moved to python-scripts\
endlocal