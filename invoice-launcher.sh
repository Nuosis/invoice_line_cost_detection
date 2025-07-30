#!/bin/bash

# Invoice Rate Detection System - Launcher Script
# Version: 1.0.0
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

# ASCII Art Banner
show_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
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
    if [[ $(echo "$python_version 3.8" | awk '{print ($1 >= $2)}') -eq 0 ]]; then
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
        log_error "Git is required but not installed. Please install Git."
        exit 1
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
    git reset --hard origin/main
    
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

# Process invoices workflow
process_invoices() {
    log_info "Starting invoice processing workflow..."
    
    cd "$PROJECT_DIR"
    
    # Check system status first
    log_info "Checking system status..."
    uv run invoice-checker status
    
    # Interactive mode with discovery
    log_info "Starting interactive processing with discovery..."
    echo -e "${YELLOW}Please select your invoice folder when prompted${NC}"
    
    # Run discovery first
    uv run invoice-checker discover --interactive
    
    # Then process invoices
    uv run invoice-checker process --interactive
    
    # Run backup if database changed
    run_backup
    
    cd ..
    log_success "Invoice processing completed"
}

# Manage parts workflow
manage_parts() {
    log_info "Starting parts management..."
    
    cd "$PROJECT_DIR"
    
    echo -e "${CYAN}Parts Management Options:${NC}"
    echo "1) List all parts"
    echo "2) Add new part"
    echo "3) Update existing part"
    echo "4) Import parts from CSV"
    echo "5) Export parts to CSV"
    echo "6) Parts statistics"
    echo "7) Return to main menu"
    
    read -p "Select option (1-7): " parts_choice
    
    case $parts_choice in
        1)
            uv run invoice-checker parts list
            ;;
        2)
            echo "Adding new part..."
            read -p "Enter part number: " part_num
            read -p "Enter authorized price: " part_price
            read -p "Enter description (optional): " part_desc
            read -p "Enter category (optional): " part_cat
            
            cmd="uv run invoice-checker parts add $part_num $part_price"
            [[ -n "$part_desc" ]] && cmd="$cmd --description \"$part_desc\""
            [[ -n "$part_cat" ]] && cmd="$cmd --category \"$part_cat\""
            
            eval $cmd
            ;;
        3)
            uv run invoice-checker parts list
            read -p "Enter part number to update: " part_num
            read -p "Enter new price (or press enter to skip): " new_price
            
            cmd="uv run invoice-checker parts update $part_num"
            [[ -n "$new_price" ]] && cmd="$cmd --price $new_price"
            
            eval $cmd
            ;;
        4)
            read -p "Enter CSV file path: " csv_file
            uv run invoice-checker parts import "$csv_file"
            ;;
        5)
            read -p "Enter output CSV file path: " output_file
            uv run invoice-checker parts export "$output_file"
            ;;
        6)
            uv run invoice-checker parts stats
            ;;
        7)
            cd ..
            return
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
    
    cd ..
}

# Manage database workflow
manage_database() {
    log_info "Starting database management..."
    
    cd "$PROJECT_DIR"
    
    echo -e "${CYAN}Database Management Options:${NC}"
    echo "1) Create backup"
    echo "2) Restore from backup"
    echo "3) Database maintenance"
    echo "4) Database migration"
    echo "5) View backup history"
    echo "6) Return to main menu"
    
    read -p "Select option (1-6): " db_choice
    
    case $db_choice in
        1)
            uv run invoice-checker database backup
            ;;
        2)
            echo "Available backups:"
            ls -la "$BACKUP_DIR"/*.db 2>/dev/null || echo "No backups found"
            read -p "Enter backup file path: " backup_file
            uv run invoice-checker database restore "$backup_file"
            ;;
        3)
            uv run invoice-checker database maintenance
            ;;
        4)
            uv run invoice-checker database migrate
            ;;
        5)
            echo "Backup history:"
            ls -la "$BACKUP_DIR"/ 2>/dev/null || echo "No backups found"
            ;;
        6)
            cd ..
            return
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
    
    cd ..
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
            return
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
}

# Main menu
show_main_menu() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                              MAIN MENU                                       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Process Invoices    - Run interactive invoice processing with discovery"
    echo -e "${GREEN}2)${NC} Manage Parts        - Add, update, import/export parts database"
    echo -e "${GREEN}3)${NC} Manage Database     - Backup, restore, and maintain database"
    echo -e "${GREEN}4)${NC} Setup               - Install, update, and configure system"
    echo -e "${GREEN}5)${NC} Exit                - Exit the application"
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
        
        read -p "Select option (1-5): " choice
        
        case $choice in
            1)
                process_invoices
                read -p "Press Enter to continue..."
                ;;
            2)
                manage_parts
                read -p "Press Enter to continue..."
                ;;
            3)
                manage_database
                read -p "Press Enter to continue..."
                ;;
            4)
                setup_workflow
                read -p "Press Enter to continue..."
                ;;
            5)
                log_info "Thank you for using Invoice Rate Detection System!"
                exit 0
                ;;
            *)
                log_error "Invalid option. Please select 1-5."
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Run main function
main "$@"