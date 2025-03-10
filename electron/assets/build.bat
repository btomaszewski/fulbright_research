@echo off
setlocal enabledelayedexpansion

echo Starting Windows build process for Python application...

:: Set working directory to script location
cd /d "%~dp0"

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found! Please install Python and make sure it's in your PATH.
    exit /b 1
)

:: Check Python version
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Using %PYTHON_VERSION%

:: Check if build_utils.py exists, if not create it
if not exist build_utils.py (
    echo build_utils.py not found! Please make sure it's in the same directory as this batch file.
    exit /b 1
)

:: Parse command line arguments
set CLEAN_ONLY=0
for %%a in (%*) do (
    if "%%a"=="--clean-only" set CLEAN_ONLY=1
)

if %CLEAN_ONLY%==1 (
    echo Running clean-up only...
    python build_utils.py --clean-only
    goto :end
)

:: Run the Python build utility
echo Running build process...
python build_utils.py %*

if %ERRORLEVEL% neq 0 (
    echo Build failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

:end
echo Build process completed.
exit /b 0