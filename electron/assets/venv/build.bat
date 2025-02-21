@echo off
setlocal enabledelayedexpansion

REM Exit on error
set ERRORLEVEL=0

REM Activate the virtual environment
call .venv\Scripts\activate

REM Run PyInstaller to package processJson.py
pyinstaller --onefile python\processJson.py

REM Create the python-scripts folder if it doesn't exist
if not exist python-scripts mkdir python-scripts

REM Move the compiled binary to the Electron project directory
move /Y dist\processJson.exe python-scripts\processJson-win.exe

REM Clean up unnecessary PyInstaller files
rmdir /s /q build dist
del /q processJson.spec

echo ✅ Build complete! Executable moved to python-scripts\
endlocal
