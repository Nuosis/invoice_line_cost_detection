@echo off
setlocal enabledelayedexpansion

REM Invoice Rate Detection System - Windows Launcher Script
REM Version: 1.0.0
REM Description: Automated setup, update, and launcher for the invoice-checker system on Windows

REM Configuration
set "REPO_URL=https://github.com/your-username/invoice_line_cost_detection.git"
set "PROJECT_DIR=invoice_line_cost_detection"
set "DB_FILE=invoice_data.db"
set "BACKUP_DIR=backups"

REM Colors for output (Windows doesn't support ANSI colors in basic cmd, but we'll use echo for clarity)
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

REM Show banner
call :show_banner

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

set /p "choice=Select option (1-5): "

if "%choice%"=="1" (
    call :process_invoices
    pause
    goto main_loop
)
if "%choice%"=="2" (
    call :manage_parts
    pause
    goto main_loop
)
if "%choice%"=="3" (
    call :manage_database
    pause
    goto main_loop
)
if "%choice%"=="4" (
    call :setup_workflow
    pause
    goto main_loop
)
if "%choice%"=="5" (
    echo %INFO_PREFIX% Thank you for using Invoice Rate Detection System!
    pause
    exit /b 0
)

echo %ERROR_PREFIX% Invalid option. Please select 1-5.
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
echo ================================================================================
echo                           INVOICE RATE DETECTOR
echo                     Advanced Invoice Rate Detection System
echo                              Version %app_version%
echo                              Windows Version
echo ================================================================================
echo.
goto :eof

:show_main_menu
echo ================================================================================
echo                                MAIN MENU                                     
echo ================================================================================
echo.
echo 1) Process Invoices    - Run interactive invoice processing with discovery
echo 2) Manage Parts        - Add, update, import/export parts database
echo 3) Manage Database     - Backup, restore, and maintain database
echo 4) Setup               - Install, update, and configure system
echo 5) Exit                - Exit the application
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
    echo %ERROR_PREFIX% Git is required but not installed. Please install Git.
    pause
    exit /b 1
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

:create_desktop_shortcut
echo %INFO_PREFIX% Creating desktop shortcut...

set "desktop_dir=%USERPROFILE%\Desktop"
set "shortcut_file=%desktop_dir%\Invoice Rate Detector.bat"
set "launcher_path=%CD%\invoice-launcher.bat"

REM Create a batch file shortcut that opens in command prompt
echo @echo off > "%shortcut_file%"
echo cd /d "%CD%" >> "%shortcut_file%"
echo start "Invoice Rate Detector" cmd /k "invoice-launcher.bat" >> "%shortcut_file%"

if exist "%shortcut_file%" (
    echo %SUCCESS_PREFIX% Desktop shortcut created: Invoice Rate Detector.bat
    echo %INFO_PREFIX% You can now double-click the shortcut on your desktop to launch the application
) else (
    echo %WARNING_PREFIX% Could not create desktop shortcut
)
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

:process_invoices
echo %INFO_PREFIX% Starting invoice processing workflow...

cd "%PROJECT_DIR%"

REM Check system status first
echo %INFO_PREFIX% Checking system status...
uv run invoice-checker status

REM Interactive processing
echo %INFO_PREFIX% Starting interactive processing with discovery...
echo Please select your invoice folder when prompted

REM Run discovery first
uv run invoice-checker discover --interactive

REM Then process invoices
uv run invoice-checker process --interactive

cd ..
echo %SUCCESS_PREFIX% Invoice processing completed
goto :eof

:manage_parts
echo %INFO_PREFIX% Starting parts management...

cd "%PROJECT_DIR%"

echo Parts Management Options:
echo 1) List all parts
echo 2) Add new part
echo 3) Update existing part
echo 4) Import parts from CSV
echo 5) Export parts to CSV
echo 6) Parts statistics
echo 7) Return to main menu

set /p "parts_choice=Select option (1-7): "

if "%parts_choice%"=="1" (
    uv run invoice-checker parts list
) else if "%parts_choice%"=="2" (
    echo Adding new part...
    set /p "part_num=Enter part number: "
    set /p "part_price=Enter authorized price: "
    set /p "part_desc=Enter description (optional): "
    set /p "part_cat=Enter category (optional): "
    
    set "cmd=uv run invoice-checker parts add !part_num! !part_price!"
    if not "!part_desc!"=="" set "cmd=!cmd! --description "!part_desc!""
    if not "!part_cat!"=="" set "cmd=!cmd! --category "!part_cat!""
    
    !cmd!
) else if "%parts_choice%"=="3" (
    uv run invoice-checker parts list
    set /p "part_num=Enter part number to update: "
    set /p "new_price=Enter new price (or press enter to skip): "
    
    set "cmd=uv run invoice-checker parts update !part_num!"
    if not "!new_price!"=="" set "cmd=!cmd! --price !new_price!"
    
    !cmd!
) else if "%parts_choice%"=="4" (
    set /p "csv_file=Enter CSV file path: "
    uv run invoice-checker parts import "!csv_file!"
) else if "%parts_choice%"=="5" (
    set /p "output_file=Enter output CSV file path: "
    uv run invoice-checker parts export "!output_file!"
) else if "%parts_choice%"=="6" (
    uv run invoice-checker parts stats
) else if "%parts_choice%"=="7" (
    cd ..
    goto :eof
) else (
    echo %ERROR_PREFIX% Invalid option
)

cd ..
goto :eof

:manage_database
echo %INFO_PREFIX% Starting database management...

cd "%PROJECT_DIR%"

echo Database Management Options:
echo 1) Create backup
echo 2) Restore from backup
echo 3) Database maintenance
echo 4) Database migration
echo 5) View backup history
echo 6) Return to main menu

set /p "db_choice=Select option (1-6): "

if "%db_choice%"=="1" (
    uv run invoice-checker database backup
) else if "%db_choice%"=="2" (
    echo Available backups:
    dir /b "%BACKUP_DIR%\*.db" 2>nul || echo No backups found
    set /p "backup_file=Enter backup file path: "
    uv run invoice-checker database restore "!backup_file!"
) else if "%db_choice%"=="3" (
    uv run invoice-checker database maintenance
) else if "%db_choice%"=="4" (
    uv run invoice-checker database migrate
) else if "%db_choice%"=="5" (
    echo Backup history:
    dir "%BACKUP_DIR%" 2>nul || echo No backups found
) else if "%db_choice%"=="6" (
    cd ..
    goto :eof
) else (
    echo %ERROR_PREFIX% Invalid option
)

cd ..
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