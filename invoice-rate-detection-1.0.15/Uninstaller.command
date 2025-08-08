#!/bin/bash

# Clarity Invoice Validator - Uninstaller Script
# This file removes the Invoice Rate Detection System from the user's system
# Version: 1.0.0

set -e  # Exit on any error

# Configuration
APP_NAME="Clarity Invoice Validator"
if [[ "$OSTYPE" == "darwin"* ]]; then
    EXPECTED_LOCATION="$HOME/Applications/InvoiceRateDetector"
else
    EXPECTED_LOCATION="$HOME/.local/bin/InvoiceRateDetector"
fi
PROJECT_DIR="invoice_line_cost_detection"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

# Show banner
show_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║                        CLARITY INVOICE VALIDATOR                                  ║
║                     Advanced Invoice Rate Detection System                        ║
║                                UNINSTALLER                                        ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Confirm uninstallation
confirm_uninstall() {
    echo -e "${YELLOW}This will completely remove Clarity Invoice Validator from your system.${NC}"
    echo -e "${YELLOW}The following will be deleted:${NC}"
    echo "  • Application files in $EXPECTED_LOCATION"
    echo "  • All databases and configuration files"
    echo "  • All generated reports and logs"
    echo ""
    echo -e "${RED}WARNING: This action cannot be undone!${NC}"
    echo ""
    
    while true; do
        read -p "Are you sure you want to continue? (yes/no): " yn
        case $yn in
            [Yy]es|[Yy] ) 
                log_info "Proceeding with uninstallation..."
                return 0
                ;;
            [Nn]o|[Nn] ) 
                log_info "Uninstallation cancelled."
                exit 0
                ;;
            * ) 
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Remove installation directory
remove_installation() {
    if [[ -d "$EXPECTED_LOCATION" ]]; then
        log_info "Removing installation directory: $EXPECTED_LOCATION"
        
        # Remove the entire installation directory
        if rm -rf "$EXPECTED_LOCATION"; then
            log_success "Installation directory removed successfully."
        else
            log_error "Failed to remove installation directory."
            log_error "You may need to remove it manually: $EXPECTED_LOCATION"
            return 1
        fi
    else
        log_warning "Installation directory not found: $EXPECTED_LOCATION"
        log_info "The application may not be installed or was already removed."
    fi
}

# Remove any leftover files in common locations
cleanup_leftovers() {
    log_info "Checking for leftover files..."
    
    # Check for any databases or config files in home directory
    local home_files=(
        "$HOME/.invoice_validator"
        "$HOME/invoice_validator.db"
        "$HOME/invoice_validator_config.json"
    )
    
    local found_files=false
    for file in "${home_files[@]}"; do
        if [[ -e "$file" ]]; then
            log_info "Removing leftover file: $file"
            rm -rf "$file"
            found_files=true
        fi
    done
    
    if [[ "$found_files" == false ]]; then
        log_info "No leftover files found."
    else
        log_success "Leftover files cleaned up."
    fi
}

# Main uninstall function
main() {
    show_banner
    
    log_info "Starting Clarity Invoice Validator uninstallation..."
    
    # Confirm with user
    confirm_uninstall
    
    # Remove installation
    if remove_installation; then
        # Clean up any leftovers
        cleanup_leftovers
        
        echo ""
        log_success "Clarity Invoice Validator has been successfully uninstalled."
        log_info "Thank you for using Clarity Invoice Validator!"
        echo ""
        
        # Optional: Ask if user wants to provide feedback
        echo -e "${BLUE}If you have a moment, we'd appreciate feedback about your experience.${NC}"
        echo -e "${BLUE}You can contact us at: https://github.com/Nuosis/invoice_line_cost_detection${NC}"
        echo ""
        
    else
        log_error "Uninstallation completed with errors."
        log_info "Some files may need to be removed manually."
        exit 1
    fi
}

# Run main function
main "$@"