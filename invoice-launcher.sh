#!/bin/bash

# Invoice Rate Detection System - Launcher Script
# Description: Automated setup, update, and launcher for the invoice-checker system

set -e  # Exit on any error

# Configuration
REPO_URL="https://github.com/nuosis/invoice_line_cost_detection.git"  # Update with actual repo URL
PROJECT_DIR="invoice_line_cost_detection"
DB_FILE="invoice_data.db"
BACKUP_DIR="backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get version from Python module
get_app_version() {
    if [[ -d "$PROJECT_DIR" ]]; then
        local current_dir=$(pwd)
        cd "$PROJECT_DIR"
        local version=$(python3 -c "
try:
    from cli.version import get_version
    print(get_version(include_dirty=False))
except:
    print('1.0.0')
" 2>/dev/null || echo "1.0.0")
        cd "$current_dir"
        echo "$version"
    else
        echo "1.0.0"
    fi
}

# ASCII Art Banner
show_banner() {
    local app_version=$(get_app_version)
    echo -e "${CYAN}"
    cat << EOF
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║    ██╗███╗   ██╗██╗   ██╗ ██████╗ ██╗ ██████╗███████╗                             ║
║    ██║████╗  ██║██║   ██║██╔═══██╗██║██╔════╝██╔════╝                             ║
║    ██║██╔██╗ ██║██║   ██║██║   ██║██║██║     █████╗                               ║
║    ██║██║╚██╗██║╚██╗ ██╔╝██║   ██║██║██║     ██╔══╝                               ║
║    ██║██║ ╚████║ ╚████╔╝ ╚██████╔╝██║╚██████╗███████╗                             ║
║    ╚═╝╚═╝  ╚═══╝  ╚═══╝   ╚═════╝ ╚═╝ ╚═════╝╚══════╝                             ║
║                                                                                   ║
║                    ██████╗  █████╗ ████████╗███████╗                              ║
║                    ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝                              ║
║                    ██████╔╝███████║   ██║   █████╗                                ║
║                    ██╔══██╗██╔══██║   ██║   ██╔══╝                                ║
║                    ██║  ██║██║  ██║   ██║   ███████╗                              ║
║                    ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝                              ║
║                                                                                   ║
║               ██████╗ ███████╗████████╗███████╗ ██████╗████████╗ ██████╗ ██████╗  ║
║               ██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗ ║
║               ██║  ██║█████╗     ██║   █████╗  ██║        ██║   ██║   ██║██████╔╝ ║
║               ██║  ██║██╔══╝     ██║   ██╔══╝  ██║        ██║   ██║   ██║██╔══██╗ ║
║               ██████╔╝███████╗   ██║   ███████╗╚██████╗   ██║   ╚██████╔╝██║  ██║ ║
║               ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ║
║                                                                                   ║
║                          Advanced Invoice Rate Detection                          ║
║                         marcus@claritybusinesssolutions.ca                        ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
                                Version ${app_version}

EOF
    echo -e "${NC}"
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version="3.8"
    
    # Convert versions to comparable format (e.g., 3.13 -> 313, 3.8 -> 308)
    current_ver=$(echo "$python_version" | awk -F. '{printf "%d%02d", $1, $2}')
    required_ver=$(echo "$required_version" | awk -F. '{printf "%d%02d", $1, $2}')
    
    if [[ $current_ver -lt $required_ver ]]; then
        log_error "Python 3.8 or higher is required. Current version: $python_version"
        exit 1
    fi
    
    # Check UV
    if ! command_exists uv; then
        log_warning "UV package manager not found. Installing UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
        if ! command_exists uv; then
            log_error "Failed to install UV. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
    fi
    
    # Check Git
    if ! command_exists git; then
        log_warning "Git not found. Installing Git..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS - install via Homebrew or Xcode Command Line Tools
            if command_exists brew; then
                brew install git
            else
                log_info "Installing Xcode Command Line Tools (includes Git)..."
                xcode-select --install
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux - try common package managers
            if command_exists apt-get; then
                sudo apt-get update && sudo apt-get install -y git
            elif command_exists yum; then
                sudo yum install -y git
            elif command_exists dnf; then
                sudo dnf install -y git
            elif command_exists pacman; then
                sudo pacman -S git
            else
                log_error "Could not install Git automatically. Please install Git manually."
                exit 1
            fi
        else
            log_error "Could not install Git automatically on this platform. Please install Git manually."
            exit 1
        fi
        
        if ! command_exists git; then
            log_error "Git installation failed. Please install Git manually."
            exit 1
        fi
        log_success "Git installed successfully"
    fi
    
    log_success "All requirements satisfied"
}

# Check if project exists
check_project_exists() {
    if [[ -d "$PROJECT_DIR" ]]; then
        return 0
    else
        return 1
    fi
}

# Get current version from git
get_current_version() {
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        cd "$PROJECT_DIR"
        git rev-parse HEAD 2>/dev/null || echo "unknown"
        cd ..
    else
        echo "unknown"
    fi
}

# Get remote version from git
get_remote_version() {
    git ls-remote "$REPO_URL" HEAD 2>/dev/null | cut -f1 || echo "unknown"
}

# Install project
install_project() {
    log_info "Installing Invoice Rate Detection System..."
    
    if check_project_exists; then
        log_warning "Project directory already exists. Use update option instead."
        return 1
    fi
    
    # Clone repository
    log_info "Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    
    cd "$PROJECT_DIR"
    
    # Install dependencies
    log_info "Installing dependencies..."
    uv sync
    
    # Install package
    log_info "Installing package..."
    uv pip install .
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    cd ..
    log_success "Installation completed successfully"
}

# Update project
update_project() {
    log_info "Checking for updates..."
    
    if ! check_project_exists; then
        log_error "Project not found. Please install first."
        return 1
    fi
    
    current_version=$(get_current_version)
    remote_version=$(get_remote_version)
    
    if [[ "$current_version" == "$remote_version" ]]; then
        log_info "Already up to date"
        return 0
    fi
    
    log_info "New version available. Updating..."
    
    # Backup database if it exists
    if [[ -f "$PROJECT_DIR/$DB_FILE" ]]; then
        backup_file="$PROJECT_DIR/$BACKUP_DIR/pre_update_backup_$(date +%Y%m%d_%H%M%S).db"
        log_info "Backing up database to $backup_file"
        cp "$PROJECT_DIR/$DB_FILE" "$backup_file"
    fi
    
    cd "$PROJECT_DIR"
    
    # Pull latest changes
    git fetch origin
    git reset --hard origin/master
    
    # Update dependencies
    uv sync
    
    # Reinstall package
    uv pip install .
    
    cd ..
    log_success "Update completed successfully"
}

# Setup automatic backup
setup_automatic_backup() {
    log_info "Setting up automatic backup..."
    
    if ! check_project_exists; then
        log_error "Project not found. Please install first."
        return 1
    fi
    
    # Create backup script
    backup_script="$PROJECT_DIR/auto_backup.sh"
    cat > "$backup_script" << 'EOF'
#!/bin/bash
# Automatic backup script for invoice-checker database

PROJECT_DIR="$(dirname "$0")"
DB_FILE="invoice_data.db"
BACKUP_DIR="backups"
MAX_BACKUPS=30

cd "$PROJECT_DIR"

if [[ -f "$DB_FILE" ]]; then
    # Create backup with timestamp
    backup_file="$BACKUP_DIR/auto_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_FILE" "$backup_file"
    
    # Clean up old backups (keep only last MAX_BACKUPS)
    ls -t "$BACKUP_DIR"/auto_backup_*.db 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
    
    echo "Database backed up to $backup_file"
else
    echo "Database file not found: $DB_FILE"
fi
EOF
    
    chmod +x "$backup_script"
    
    # Setup cron job for daily backup at 2 AM
    cron_entry="0 2 * * * $PWD/$backup_script"
    
    # Check if cron entry already exists
    if ! crontab -l 2>/dev/null | grep -q "$backup_script"; then
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        log_success "Automatic daily backup configured"
    else
        log_info "Automatic backup already configured"
    fi
}

# Create desktop shortcut
create_desktop_shortcut() {
    log_info "Creating desktop shortcut..."
    
    local desktop_dir=""
    local shortcut_file=""
    local launcher_path="$(pwd)/invoice-launcher.sh"
    
    # Determine desktop directory
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        desktop_dir="$HOME/Desktop"
        shortcut_file="$desktop_dir/Invoice Rate Detector.command"
        
        # Create .command file for macOS
        cat > "$shortcut_file" << EOF
#!/bin/bash
cd "$(dirname "$launcher_path")"
./invoice-launcher.sh
EOF
        chmod +x "$shortcut_file"
        
    else
        # Linux
        desktop_dir="$HOME/Desktop"
        shortcut_file="$desktop_dir/Invoice Rate Detector.desktop"
        
        # Create .desktop file for Linux
        cat > "$shortcut_file" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Invoice Rate Detector
Comment=Advanced Invoice Rate Detection System
Exec=gnome-terminal --working-directory="$(dirname "$launcher_path")" -- bash -c "./invoice-launcher.sh; exec bash"
Icon=utilities-terminal
Terminal=true
Categories=Office;Finance;
StartupNotify=true
EOF
        chmod +x "$shortcut_file"
        
        # Try to make it trusted (Ubuntu/GNOME)
        if command -v gio &> /dev/null; then
            gio set "$shortcut_file" metadata::trusted true 2>/dev/null || true
        fi
    fi
    
    if [[ -f "$shortcut_file" ]]; then
        log_success "Desktop shortcut created: $(basename "$shortcut_file")"
        log_info "You can now double-click the shortcut on your desktop to launch the application"
    else
        log_warning "Could not create desktop shortcut"
    fi
}

# Verify backup system
verify_backup_system() {
    log_info "Verifying backup system..."
    
    if ! check_project_exists; then
        log_error "Project not found."
        return 1
    fi
    
    # Check if backup directory exists
    if [[ ! -d "$PROJECT_DIR/$BACKUP_DIR" ]]; then
        mkdir -p "$PROJECT_DIR/$BACKUP_DIR"
        log_info "Created backup directory"
    fi
    
    # Check if backup script exists
    if [[ -f "$PROJECT_DIR/auto_backup.sh" ]]; then
        log_success "Backup script found"
    else
        log_warning "Backup script not found. Setting up..."
        setup_automatic_backup
    fi
    
    # Check cron job
    if crontab -l 2>/dev/null | grep -q "auto_backup.sh"; then
        log_success "Automatic backup is configured"
    else
        log_warning "Automatic backup not configured. Setting up..."
        setup_automatic_backup
    fi
}

# Run database backup
run_backup() {
    if [[ -f "$PROJECT_DIR/$DB_FILE" ]]; then
        cd "$PROJECT_DIR"
        uv run invoice-checker database backup
        cd ..
        log_success "Database backup completed"
    else
        log_info "No database found to backup"
    fi
}

# Launch interactive application
launch_interactive_app() {
    log_info "Launching Invoice Rate Detection System..."
    
    cd "$PROJECT_DIR"
    
    # Check system status first
    log_info "Checking system status..."
    uv run invoice-checker status
    
    # Launch the Python interactive mode (this handles all application operations)
    log_info "Starting interactive application..."
    uv run invoice-checker
    
    cd ..
    log_success "Application session completed"
}

# Launch quick processing
launch_quick_process() {
    log_info "Starting Quick Process Mode..."
    
    cd "$PROJECT_DIR"
    
    # Check system status first
    log_info "Checking system status..."
    uv run invoice-checker status
    
    # Launch quick processing with defaults
    log_info "Running quick processing with all defaults..."
    uv run invoice-checker quick
    
    cd ..
    log_success "Quick processing completed"
}

# Setup workflow
setup_workflow() {
    log_info "Starting setup workflow..."
    
    echo -e "${CYAN}Setup Options:${NC}"
    echo "1) Initial system setup"
    echo "2) Configure automatic backup"
    echo "3) Verify system status"
    echo "4) Update system"
    echo "5) Return to main menu"
    
    read -p "Select option (1-5): " setup_choice
    
    case $setup_choice in
        1)
            check_requirements
            if ! check_project_exists; then
                install_project
            else
                log_info "System already installed"
            fi
            setup_automatic_backup
            ;;
        2)
            setup_automatic_backup
            ;;
        3)
            check_requirements
            verify_backup_system
            if check_project_exists; then
                cd "$PROJECT_DIR"
                uv run invoice-checker status
                cd ..
            fi
            ;;
        4)
            update_project
            ;;
        5)
            return 5  # Special exit code for "Return to main menu"
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
}

# Show help and documentation
show_help() {
    log_info "Displaying help and documentation..."
    
    # Check if USER_MANUAL.md exists and display it
    if [[ -f "docs/USER_MANUAL.md" ]]; then
        echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║                                USER MANUAL                                        ║${NC}"
        echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Navigation: Use arrow keys or Page Up/Down to scroll. Press 'q' to exit.${NC}"
        echo ""
        read -p "Press Enter to open the manual..."
        
        # Display the manual with pagination
        if command -v less >/dev/null 2>&1; then
            less docs/USER_MANUAL.md
        elif command -v more >/dev/null 2>&1; then
            more docs/USER_MANUAL.md
        else
            cat docs/USER_MANUAL.md
            echo ""
            read -p "Press Enter to continue..."
        fi
    elif [[ -f "$PROJECT_DIR/docs/USER_MANUAL.md" ]]; then
        echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║                                USER MANUAL                                        ║${NC}"
        echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Navigation: Use arrow keys or Page Up/Down to scroll. Press 'q' to exit.${NC}"
        echo ""
        read -p "Press Enter to open the manual..."
        
        # Display the manual with pagination
        if command -v less >/dev/null 2>&1; then
            less "$PROJECT_DIR/docs/USER_MANUAL.md"
        elif command -v more >/dev/null 2>&1; then
            more "$PROJECT_DIR/docs/USER_MANUAL.md"
        else
            cat "$PROJECT_DIR/docs/USER_MANUAL.md"
            echo ""
            read -p "Press Enter to continue..."
        fi
    else
        # Fallback to basic help if manual not found
        echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║                                HELP & DOCUMENTATION                               ║${NC}"
        echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        echo -e "${YELLOW}User manual not found. Displaying basic help...${NC}"
        echo ""
        
        echo -e "${GREEN}OVERVIEW${NC}"
        echo "The Clarity Invoice Validator is an advanced invoice rate detection system"
        echo "designed to help businesses identify pricing anomalies in their invoices."
        echo ""
        
        echo -e "${GREEN}GETTING STARTED${NC}"
        echo "1. First time users should run 'Setup' to install and configure the system"
        echo "2. Launch the application to access all features interactively"
        echo "3. Use the application's main menu to manage parts and process invoices"
        echo "4. Review generated reports in CSV format (can be opened in Excel)"
        echo ""
        
        echo -e "${GREEN}SUPPORT${NC}"
        echo "• Contact: marcus@claritybusinesssolutions.ca"
        echo "• GitHub: https://github.com/Nuosis/invoice_line_cost_detection"
        echo ""
        
        read -p "Press Enter to continue..."
    fi
}

# Main menu
show_main_menu() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                     MAIN MENU                                     ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Quick Process       - Process invoices with defaults (discovery enabled)"
    echo -e "${GREEN}2)${NC} Launch Application  - Start the interactive Invoice Rate Detection System"
    echo -e "${GREEN}3)${NC} Setup               - Install, update, and configure system"
    echo -e "${GREEN}4)${NC} Configuration       - Setup and manage system options"
    echo -e "${GREEN}5)${NC} Help                - Show help and documentation"
    echo -e "${GREEN}6)${NC} Exit                - Exit the launcher"
    echo ""
    echo -e "${YELLOW}Note: Quick Process uses all configured defaults but still discovers new parts."
    echo -e "Use Launch Application for full interactive control.${NC}"
    echo ""
}

# Main function
main() {
    # Check if we need to install first
    if ! check_project_exists; then
        echo -e "${YELLOW}Invoice Rate Detection System not found in current directory.${NC}"
        echo ""
        echo -e "${CYAN}Recommended installation locations:${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  • ~/Applications/InvoiceRateDetector (recommended for macOS)"
            echo "  • ~/.local/bin/InvoiceRateDetector"
        else
            echo "  • ~/.local/bin/InvoiceRateDetector (recommended for Linux)"
            echo "  • ~/Applications/InvoiceRateDetector"
        fi
        echo "  • Current directory: $(pwd)"
        echo ""
        
        read -p "Would you like to install it in the current directory? (y/n): " install_choice
        
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            check_requirements
            install_project
            setup_automatic_backup
        else
            echo ""
            echo -e "${CYAN}To install in a recommended location:${NC}"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                echo "  mkdir -p ~/Applications && cd ~/Applications"
            else
                echo "  mkdir -p ~/.local/bin && cd ~/.local/bin"
            fi
            echo "  curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.sh"
            echo "  chmod +x invoice-launcher.sh && ./invoice-launcher.sh"
            log_error "Installation cancelled. Please run this script from your desired installation directory."
            exit 1
        fi
    else
        # Check for updates
        update_project
    fi
    
    # Verify backup system
    verify_backup_system
    
    # Main application loop
    while true; do
        clear
        show_banner
        show_main_menu
        
        read -p "Select option (1-6): " choice
        
        case $choice in
            1)
                launch_quick_process
                read -p "Press Enter to continue..."
                ;;
            2)
                launch_interactive_app
                read -p "Press Enter to continue..."
                ;;
            3)
                setup_workflow
                # Check if user selected "Return to main menu" (exit code 5)
                if [[ $? -ne 5 ]]; then
                    read -p "Press Enter to continue..."
                fi
                ;;
            4)
                # Configuration management (interactive setup wizard)
                if [[ -d "$PROJECT_DIR" ]]; then
                    cd "$PROJECT_DIR"
                    uv run invoice-checker config setup
                    cd ..
                else
                    log_error "Project not found. Please install the system first."
                fi
                read -p "Press Enter to continue..."
                ;;
            5)
                show_help
                ;;
            6)
                log_info "Thank you for using Invoice Rate Detection System!"
                exit 0
                ;;
            *)
                log_error "Invalid option. Please select 1-6."
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Run main function
main "$@"