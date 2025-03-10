@echo off
setlocal enabledelayedexpansion

:: Set working directory to script location
cd /d "%~dp0"

:: Import configuration variables
call scripts\config.bat

echo Starting build process from %cd% for platform: %PLATFORM_ID%

:: Clean previous builds
call scripts\clean.bat

:: Verify prerequisites
call scripts\verify_prereqs.bat
if errorlevel 1 (
    echo ❌ Prerequisite verification failed
    exit /b 1
)

:: Package models
call scripts\package_models.bat
if errorlevel 1 (
    echo ❌ Model packaging failed
    exit /b 1
)

:: Prepare build environment
call scripts\prepare_build.bat
if errorlevel 1 (
    echo ❌ Build preparation failed
    exit /b 1
)

:: Run PyInstaller build
call scripts\run_build.bat
if errorlevel 1 (
    echo ❌ PyInstaller build failed
    exit /b 1
)

:: Finalize build
call scripts\finalize.bat
if errorlevel 1 (
    echo ❌ Build finalization failed
    exit /b 1
)

echo ✅ Build process completed successfully!