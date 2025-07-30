@echo off
setlocal enabledelayedexpansion

REM Clarity Invoice Validator - Bootstrap Script
REM This file automatically sets up and launches the Invoice Rate Detection System
REM Version: 1.0.0

REM Configuration
set "APP_NAME=Clarity Invoice Validator"
set "EXPECTED_LOCATION=%LOCALAPPDATA%\Programs\InvoiceRateDetector"
set "LAUNCHER_URL=https://raw.githubusercontent.com/Nuosis/invoice_line_cost_detection/main/invoice-launcher.bat"
set "PROJECT_DIR=invoice_line_cost_detection"

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Colors for output
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

REM Show banner
echo.
echo ================================================================================
echo                        CLARITY INVOICE VALIDATOR                              
echo                     Advanced Invoice Rate Detection System                   
echo                              Bootstrap Launcher                               
echo ================================================================================
echo.

REM Check if CLI is installed in expected location
if exist "%EXPECTED_LOCATION%\%PROJECT_DIR%" (
    echo %SUCCESS_PREFIX% Found existing installation at %EXPECTED_LOCATION%
    echo %INFO_PREFIX% Launching Clarity Invoice Validator...
    
    REM Change to the expected location and run the launcher
    cd /d "%EXPECTED_LOCATION%"
    if exist "invoice-launcher.bat" (
        call invoice-launcher.bat
    ) else (
        echo %WARNING_PREFIX% Launcher script not found. Setting up...
        goto setup_installation
    )
) else (
    echo %INFO_PREFIX% No existing installation found.
    echo %INFO_PREFIX% Setting up Clarity Invoice Validator for first-time use...
    
    REM Create the expected directory
    if not exist "%EXPECTED_LOCATION%" (
        mkdir "%EXPECTED_LOCATION%"
    )
    
    REM Change to the expected location
    cd /d "%EXPECTED_LOCATION%"
    
    :setup_installation
    REM First try to copy from local source if available
    if exist "%SCRIPT_DIR%invoice-launcher.bat" (
        echo %INFO_PREFIX% Copying launcher script from local source...
        goto copy_from_local
    ) else (
        echo %INFO_PREFIX% Local source not found. Downloading from GitHub...
        goto download_launcher
    )
    
    :copy_from_local
    REM Copy the launcher script
    copy "%SCRIPT_DIR%invoice-launcher.bat" "invoice-launcher.bat" >nul
    if errorlevel 1 (
        echo %ERROR_PREFIX% Failed to copy launcher script from local source.
        echo %INFO_PREFIX% Falling back to download from GitHub...
        goto download_launcher
    )
    
    echo %SUCCESS_PREFIX% Launcher script copied successfully.
    echo %INFO_PREFIX% Starting setup process...
    
    REM Run the launcher script
    call invoice-launcher.bat
    goto end_script
    
    :download_launcher
    echo %INFO_PREFIX% Downloading launcher script from GitHub...
    
    REM Try to download the launcher script
    curl --version >nul 2>&1
    if errorlevel 1 (
        echo %ERROR_PREFIX% curl is not available. Please install curl or download manually.
        echo %INFO_PREFIX% Manual download URL: %LAUNCHER_URL%
        pause
        exit /b 1
    )
    
    curl -L -o "invoice-launcher.bat" "%LAUNCHER_URL%"
    if errorlevel 1 (
        echo %ERROR_PREFIX% Failed to download launcher script.
        echo %INFO_PREFIX% Please check your internet connection and try again.
        echo %INFO_PREFIX% Manual download URL: %LAUNCHER_URL%
        pause
        exit /b 1
    )
    
    echo %SUCCESS_PREFIX% Launcher script downloaded successfully.
    echo %INFO_PREFIX% Starting setup process...
    
    REM Run the launcher script
    call invoice-launcher.bat
    
    :end_script
)

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo %ERROR_PREFIX% An error occurred. Press any key to exit.
    pause >nul
)

exit /b 0