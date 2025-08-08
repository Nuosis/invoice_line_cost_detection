@echo off
setlocal enabledelayedexpansion

REM Invoice Rate Detection System - Windows Launcher Script
REM Description: Automated setup, update, and launcher for the invoice-checker system on Windows

REM Configuration
set "REPO_URL=https://github.com/nuosis/invoice_line_cost_detection.git"
set "PROJECT_DIR=invoice_line_cost_detection"
set "DB_FILE=invoice_data.db"
set "BACKUP_DIR=backups"

REM Colors for output (Windows doesn't support ANSI colors in basic cmd, but we'll use echo for clarity)
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

REM Check if we need to install first
if not exist "%PROJECT_DIR%" (
    echo.
    echo Invoice Rate Detection System not found in current directory.
    echo.
    echo %INFO_PREFIX% Recommended installation locations:
    echo   • %LOCALAPPDATA%\Programs\InvoiceRateDetector (recommended for Windows)
    echo   • %USERPROFILE%\Applications\InvoiceRateDetector
    echo   • Current directory: %CD%
    echo.
    
    set /p "install_choice=Would you like to install it in the current directory? (y/n): "
    if /i "!install_choice!"=="y" (
        call :check_requirements
        call :install_project
        call :setup_automatic_backup
    ) else (
        echo.
        echo %INFO_PREFIX% To install in a recommended location:
        echo   mkdir "%LOCALAPPDATA%\Programs" ^&^& cd /d "%LOCALAPPDATA%\Programs"
        echo   curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.bat
        echo   invoice-launcher.bat
        echo %ERROR_PREFIX% Installation cancelled. Please run this script from your desired installation directory.
        pause
        exit /b 1
    )
) else (
    REM Check for updates
    call :update_project
)

REM Verify backup system
call :verify_backup_system

REM Main application loop
:main_loop
cls
call :show_banner
call :show_main_menu

set /p "choice=Select option (1-4): "

if "%choice%"=="1" (
    call :launch_interactive_app
    pause
    goto main_loop
)
if "%choice%"=="2" (
    call :setup_workflow
    pause
    goto main_loop
)
if "%choice%"=="3" (
    call :show_help
    goto main_loop
)
if "%choice%"=="4" (
    echo %INFO_PREFIX% Thank you for using Invoice Rate Detection System!
    pause
    exit /b 0
)

echo %ERROR_PREFIX% Invalid option. Please select 1-4.
pause
goto main_loop

REM Function definitions

:get_app_version
set "app_version=1.0.0"
if exist "%PROJECT_DIR%" (
    cd /d "%PROJECT_DIR%"
    for /f "delims=" %%i in ('python -c "try: from cli.version import get_version; print(get_version()); except: print('1.0.0')" 2^>nul') do set "app_version=%%i"
    cd ..
)
goto :eof

:show_banner
call :get_app_version
echo.
echo ╔═══════════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                                   ║
echo ║    ██╗███╗   ██╗██╗   ██╗ ██████╗ ██╗ ██████╗███████╗                             ║
echo ║    ██║████╗  ██║██║   ██║██╔═══██╗██║██╔════╝██╔════╝                             ║
echo ║    ██║██╔██╗ ██║██║   ██║██║   ██║██║██║     █████╗                               ║
echo ║    ██║██║╚██╗██║╚██╗ ██╔╝██║   ██║██║██║     ██╔══╝                               ║
echo ║    ██║██║ ╚████║ ╚████╔╝ ╚██████╔╝██║╚██████╗███████╗                             ║
echo ║    ╚═╝╚═╝  ╚═══╝  ╚═══╝   ╚═════╝ ╚═╝ ╚═════╝╚══════╝                             ║
echo ║                                                                                   ║
echo ║                    ██████╗  █████╗ ████████╗███████╗                              ║
echo ║                    ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝                              ║
echo ║                    ██████╔╝███████║   ██║   █████╗                                ║
echo ║                    ██╔══██╗██╔══██║   ██║   ██╔══╝                                ║
echo ║                    ██║  ██║██║  ██║   ██║   ███████╗                              ║
echo ║                    ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝                              ║
echo ║                                                                                   ║
echo ║               ██████╗ ███████╗████████╗███████╗ ██████╗████████╗ ██████╗ ██████╗  ║
echo ║               ██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗ ║
echo ║               ██║  ██║█████╗     ██║   █████╗  ██║        ██║   ██║   ██║██████╔╝ ║
echo ║               ██║  ██║██╔══╝     ██║   ██╔══╝  ██║        ██║   ██║   ██║██╔══██╗ ║
echo ║               ██████╔╝███████╗   ██║   ███████╗╚██████╗   ██║   ╚██████╔╝██║  ██║ ║
echo ║               ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ║
echo ║                                                                                   ║
echo ║                          Advanced Invoice Rate Detection                          ║
echo ║                         marcus@claritybusinesssolutions.ca                        ║
echo ╚═══════════════════════════════════════════════════════════════════════════════════╝
echo                                 Version %app_version%
echo.
goto :eof

:show_main_menu
echo ╔═══════════════════════════════════════════════════════════════════════════════════╗
echo ║                                     MAIN MENU                                     ║
echo ╚═══════════════════════════════════════════════════════════════════════════════════╝
echo.
echo 1) Launch Application  - Start the interactive Invoice Rate Detection System
echo 2) Setup               - Install, update, and configure system
echo 3) Help                - Show help and documentation
echo 4) Exit                - Exit the launcher
echo.
echo Note: All invoice processing, parts management, and database operations
echo are available through the interactive application (option 1).
echo.
goto :eof

:check_requirements
echo %INFO_PREFIX% Checking system requirements...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %ERROR_PREFIX% Python 3 is required but not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check UV
uv --version >nul 2>&1
if errorlevel 1 (
    echo %WARNING_PREFIX% UV package manager not found. Please install UV manually.
    echo Visit: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

REM Check Git
git --version >nul 2>&1
if errorlevel 1 (
    echo %WARNING_PREFIX% Git not found. Installing Git...
    echo %INFO_PREFIX% Downloading Git for Windows...
    
    REM Try to install Git using winget (Windows Package Manager)
    winget install --id Git.Git -e --source winget >nul 2>&1
    if errorlevel 1 (
        echo %WARNING_PREFIX% Winget installation failed. Trying chocolatey...
        choco install git -y >nul 2>&1
        if errorlevel 1 (
            echo %ERROR_PREFIX% Could not install Git automatically.
            echo Please install Git manually from: https://git-scm.com/download/win
            pause
            exit /b 1
        )
    )
    
    REM Refresh PATH to include Git
    call refreshenv >nul 2>&1
    
    REM Check if Git is now available
    git --version >nul 2>&1
    if errorlevel 1 (
        echo %ERROR_PREFIX% Git installation failed. Please install Git manually.
        echo Download from: https://git-scm.com/download/win
        pause
        exit /b 1
    )
    echo %SUCCESS_PREFIX% Git installed successfully
)

echo %SUCCESS_PREFIX% All requirements satisfied
goto :eof

:install_project
echo %INFO_PREFIX% Installing Invoice Rate Detection System...

if exist "%PROJECT_DIR%" (
    echo %WARNING_PREFIX% Project directory already exists. Use update option instead.
    goto :eof
)

REM Clone repository
echo %INFO_PREFIX% Cloning repository...
git clone "%REPO_URL%" "%PROJECT_DIR%"
if errorlevel 1 (
    echo %ERROR_PREFIX% Failed to clone repository
    goto :eof
)

cd "%PROJECT_DIR%"

REM Install dependencies
echo %INFO_PREFIX% Installing dependencies...
uv sync
if errorlevel 1 (
    echo %ERROR_PREFIX% Failed to install dependencies
    cd ..
    goto :eof
)

REM Install package
echo %INFO_PREFIX% Installing package...
uv pip install .
if errorlevel 1 (
    echo %ERROR_PREFIX% Failed to install package
    cd ..
    goto :eof
)

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

cd ..
echo %SUCCESS_PREFIX% Installation completed successfully
goto :eof

:update_project
echo %INFO_PREFIX% Checking for updates...

if not exist "%PROJECT_DIR%" (
    echo %ERROR_PREFIX% Project not found. Please install first.
    goto :eof
)

cd "%PROJECT_DIR%"

REM Simple update - pull latest changes
echo %INFO_PREFIX% Updating from repository...
git fetch origin
git reset --hard origin/main

REM Update dependencies
uv sync

REM Reinstall package
uv pip install .

cd ..
echo %SUCCESS_PREFIX% Update completed successfully
goto :eof

:setup_automatic_backup
echo %INFO_PREFIX% Setting up automatic backup...
echo %WARNING_PREFIX% Automatic backup setup requires manual configuration on Windows.
echo Please set up a scheduled task to run backup operations daily.
goto :eof

:verify_backup_system
echo %INFO_PREFIX% Verifying backup system...

if not exist "%PROJECT_DIR%" (
    echo %ERROR_PREFIX% Project not found.
    goto :eof
)

REM Check if backup directory exists
if not exist "%PROJECT_DIR%\%BACKUP_DIR%" (
    mkdir "%PROJECT_DIR%\%BACKUP_DIR%"
    echo %INFO_PREFIX% Created backup directory
)

echo %SUCCESS_PREFIX% Backup system verified
goto :eof

:launch_interactive_app
echo %INFO_PREFIX% Launching Invoice Rate Detection System...

cd "%PROJECT_DIR%"

REM Check system status first
echo %INFO_PREFIX% Checking system status...
uv run invoice-checker status

REM Launch the Python interactive mode (this handles all application operations)
echo %INFO_PREFIX% Starting interactive application...
uv run invoice-checker

cd ..
echo %SUCCESS_PREFIX% Application session completed
goto :eof

:setup_workflow
echo %INFO_PREFIX% Starting setup workflow...

echo Setup Options:
echo 1) Initial system setup
echo 2) Configure automatic backup
echo 3) Verify system status
echo 4) Update system
echo 5) Return to main menu

set /p "setup_choice=Select option (1-5): "

if "%setup_choice%"=="1" (
    call :check_requirements
    if not exist "%PROJECT_DIR%" (
        call :install_project
    ) else (
        echo %INFO_PREFIX% System already installed
    )
    call :setup_automatic_backup
) else if "%setup_choice%"=="2" (
    call :setup_automatic_backup
) else if "%setup_choice%"=="3" (
    call :check_requirements
    call :verify_backup_system
    if exist "%PROJECT_DIR%" (
        cd "%PROJECT_DIR%"
        uv run invoice-checker status
        cd ..
    )
) else if "%setup_choice%"=="4" (
    call :update_project
) else if "%setup_choice%"=="5" (
    goto :eof
) else (
    echo %ERROR_PREFIX% Invalid option
)

goto :eof

:show_help
echo %INFO_PREFIX% Displaying help and documentation...

echo ╔═════════════════════════════════════════════════════════════════════════════════╗
echo ║                              HELP ^& DOCUMENTATION                               ║
echo ╚═════════════════════════════════════════════════════════════════════════════════╝
echo.

echo OVERVIEW
echo The Clarity Invoice Validator is an advanced invoice rate detection system
echo designed to help businesses identify pricing anomalies in their invoices.
echo.

echo MAIN FEATURES
echo • Process Invoices: Analyze PDF invoices for pricing discrepancies
echo • Manage Parts: Maintain a database of parts with authorized prices
echo • Database Management: Backup, restore, and maintain your data
echo • Interactive Discovery: Automatically discover new parts from invoices
echo.

echo GETTING STARTED
echo 1. First time users should run 'Setup' to install and configure the system
echo 2. Launch the interactive application to access all features
echo 3. Use the guided workflows for invoice processing and parts management
echo 4. Review generated reports in CSV format (can be opened in Excel)
echo.

echo WORKFLOW TIPS
echo • Start with a small batch of invoices to test the system
echo • Use interactive discovery to build your parts database quickly
echo • Regular backups are automatically configured but can be run manually
echo • Reports are saved in the project directory and can be opened in Excel
echo.

echo TROUBLESHOOTING
echo • If processing fails, check that PDF files are readable and not encrypted
echo • Ensure Python 3.8+ and UV package manager are installed
echo • Use 'Setup ^> Verify system status' to check for issues
echo • Database backups are created automatically before major operations
echo.

echo SUPPORT
echo • Documentation: Check the docs/ folder in the project directory
echo • User Manual: docs/USER_MANUAL.md contains detailed instructions
echo • Contact: marcus@claritybusinesssolutions.ca
echo • GitHub: https://github.com/Nuosis/invoice_line_cost_detection
echo.

if exist "%PROJECT_DIR%" (
    echo QUICK COMMANDS
    echo You can also run commands directly from the project directory:
    echo • cd %PROJECT_DIR%
    echo • uv run invoice-checker status          # Check system status
    echo • uv run invoice-checker parts list      # List all parts
    echo • uv run invoice-checker --help          # Show CLI help
    echo.
)

pause
goto :eof