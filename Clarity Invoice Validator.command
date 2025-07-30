#!/bin/bash

# Clarity Invoice Validator - Bootstrap Script
# This file automatically sets up and launches the Invoice Rate Detection System
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
LAUNCHER_URL="https://raw.githubusercontent.com/Nuosis/invoice_line_cost_detection/main/invoice-launcher.sh"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
║                              Bootstrap Launcher                                   ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main function
main() {
    show_banner
    
    # Check if CLI is installed in expected location
    if [[ -d "$EXPECTED_LOCATION/$PROJECT_DIR" ]]; then
        log_success "Found existing installation at $EXPECTED_LOCATION"
        log_info "Launching Clarity Invoice Validator..."
        
        # Change to the expected location and run the launcher
        cd "$EXPECTED_LOCATION"
        if [[ -f "invoice-launcher.sh" ]]; then
            ./invoice-launcher.sh
        else
            log_warning "Launcher script not found. Setting up..."
            setup_installation
        fi
    else
        log_info "No existing installation found."
        log_info "Setting up Clarity Invoice Validator for first-time use..."
        
        # Create the expected directory
        mkdir -p "$EXPECTED_LOCATION"
        
        # Change to the expected location
        cd "$EXPECTED_LOCATION"
        
        setup_installation
    fi
}

setup_installation() {
    # First try to copy from local source if available
    if [[ -f "$SCRIPT_DIR/invoice-launcher.sh" ]]; then
        log_info "Copying launcher script from local source..."
        copy_from_local
    else
        log_info "Local source not found. Downloading from GitHub..."
        download_launcher
    fi
}

copy_from_local() {
    # Copy the launcher script
    if cp "$SCRIPT_DIR/invoice-launcher.sh" "invoice-launcher.sh"; then
        chmod +x "invoice-launcher.sh"
        log_success "Launcher script copied successfully."
        log_info "Starting setup process..."
        
        # Run the launcher script
        ./invoice-launcher.sh
    else
        log_error "Failed to copy launcher script from local source."
        log_info "Falling back to download from GitHub..."
        download_launcher
    fi
}

download_launcher() {
    log_info "Downloading launcher script from GitHub..."
    
    # Check if curl is available
    if ! command_exists curl; then
        log_error "curl is not available. Please install curl or download manually."
        log_info "Manual download URL: $LAUNCHER_URL"
        exit 1
    fi
    
    # Download the launcher script
    if curl -L -o "invoice-launcher.sh" "$LAUNCHER_URL"; then
        chmod +x "invoice-launcher.sh"
        log_success "Launcher script downloaded successfully."
        log_info "Starting setup process..."
        
        # Run the launcher script
        ./invoice-launcher.sh
    else
        log_error "Failed to download launcher script."
        log_info "Please check your internet connection and try again."
        log_info "Manual download URL: $LAUNCHER_URL"
        exit 1
    fi
}

# Run main function
main "$@"