#!/bin/bash

# Deploy script for Invoice Rate Detection System
# This script:
# 1. Creates summary of changes since last commit
# 2. Updates CHANGELOG with date and version
# 3. Commits git with unique commit title (timestamp) and pushes to origin

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CHANGELOG_FILE="CHANGELOG.md"
VERSION_FILE="cli/version.py"

# Helper functions
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

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository. Please initialize git first."
        exit 1
    fi
}

# Check if there are uncommitted changes
check_uncommitted_changes() {
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "There are uncommitted changes in the repository."
        echo "Uncommitted changes:"
        git status --short
        echo
        read -p "Do you want to continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled."
            exit 0
        fi
    fi
}

# Get current version from version.py
get_current_version() {
    python3 -c "
import sys
sys.path.insert(0, '.')
from cli.version import get_version
print(get_version(include_commit=True, include_dirty=False))
"
}

# Get base version from version.py
get_base_version() {
    python3 -c "
import sys
sys.path.insert(0, '.')
from cli.version import BASE_VERSION
print(BASE_VERSION)
"
}

# Generate summary of changes since last commit
generate_changes_summary() {
    local last_commit=$(git rev-parse HEAD 2>/dev/null || echo "")
    local changes_summary=""
    
    if [[ -z "$last_commit" ]]; then
        # No previous commits, this is initial commit
        changes_summary="Initial commit - Invoice Rate Detection System setup"
    else
        # Get changes since last commit
        local modified_files=$(git diff --name-only HEAD 2>/dev/null || echo "")
        local staged_files=$(git diff --cached --name-only 2>/dev/null || echo "")
        local untracked_files=$(git ls-files --others --exclude-standard 2>/dev/null || echo "")
        
        if [[ -n "$staged_files" ]]; then
            changes_summary+="Staged changes:\n"
            while IFS= read -r file; do
                [[ -n "$file" ]] && changes_summary+="  - Modified: $file\n"
            done <<< "$staged_files"
        fi
        
        if [[ -n "$modified_files" ]]; then
            changes_summary+="Modified files:\n"
            while IFS= read -r file; do
                [[ -n "$file" ]] && changes_summary+="  - Modified: $file\n"
            done <<< "$modified_files"
        fi
        
        if [[ -n "$untracked_files" ]]; then
            changes_summary+="New files:\n"
            while IFS= read -r file; do
                [[ -n "$file" ]] && changes_summary+="  - Added: $file\n"
            done <<< "$untracked_files"
        fi
        
        if [[ -z "$changes_summary" ]]; then
            changes_summary="No changes detected since last commit"
        fi
    fi
    
    echo -e "$changes_summary"
}

# Create or update CHANGELOG
update_changelog() {
    local version="$1"
    local changes="$2"
    local date=$(date '+%Y-%m-%d')
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
    
    # Create CHANGELOG if it doesn't exist
    if [[ ! -f "$CHANGELOG_FILE" ]]; then
        log_info "Creating new CHANGELOG.md file"
        cat > "$CHANGELOG_FILE" << EOF
# Changelog

All notable changes to the Invoice Rate Detection System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

EOF
    fi
    
    # Create temporary file for new changelog content
    local temp_changelog=$(mktemp)
    
    # Read existing changelog and insert new version
    local in_unreleased=false
    local added_new_version=false
    
    while IFS= read -r line; do
        if [[ "$line" == "## [Unreleased]" ]]; then
            echo "$line" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
            echo "## [$version] - $date" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
            echo "### Changes" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
            echo -e "$changes" | sed 's/^//' >> "$temp_changelog"
            echo "" >> "$temp_changelog"
            echo "**Deployment:** $timestamp" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
            added_new_version=true
        else
            echo "$line" >> "$temp_changelog"
        fi
    done < "$CHANGELOG_FILE"
    
    # If we didn't find an [Unreleased] section, add the version at the top
    if [[ "$added_new_version" == false ]]; then
        # Insert after the header
        local temp_changelog2=$(mktemp)
        local header_done=false
        
        while IFS= read -r line; do
            echo "$line" >> "$temp_changelog2"
            if [[ "$line" =~ ^#[[:space:]]*Changelog ]] && [[ "$header_done" == false ]]; then
                echo "" >> "$temp_changelog2"
                echo "All notable changes to the Invoice Rate Detection System will be documented in this file." >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                echo "## [Unreleased]" >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                echo "## [$version] - $date" >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                echo "### Changes" >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                echo -e "$changes" | sed 's/^//' >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                echo "**Deployment:** $timestamp" >> "$temp_changelog2"
                echo "" >> "$temp_changelog2"
                header_done=true
            fi
        done < "$temp_changelog"
        
        mv "$temp_changelog2" "$temp_changelog"
    fi
    
    # Replace original changelog
    mv "$temp_changelog" "$CHANGELOG_FILE"
    
    log_success "Updated $CHANGELOG_FILE with version $version"
}

# Generate unique commit message with timestamp
generate_commit_message() {
    local version="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    echo "deploy: v${version} - ${timestamp}"
}

# Main deployment function
deploy() {
    log_info "Starting deployment process..."
    
    # Pre-flight checks
    check_git_repo
    check_uncommitted_changes
    
    # Get version information
    local current_version
    current_version=$(get_current_version)
    if [[ $? -ne 0 ]]; then
        log_error "Failed to get current version from $VERSION_FILE"
        exit 1
    fi
    
    log_info "Current version: $current_version"
    
    # Generate changes summary
    log_info "Generating changes summary..."
    local changes_summary
    changes_summary=$(generate_changes_summary)
    
    echo "Changes to be deployed:"
    echo "======================"
    echo -e "$changes_summary"
    echo "======================"
    echo
    
    # Confirm deployment
    read -p "Proceed with deployment of version $current_version? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled."
        exit 0
    fi
    
    # Update CHANGELOG
    log_info "Updating CHANGELOG..."
    update_changelog "$current_version" "$changes_summary"
    
    # Stage all changes including the updated CHANGELOG
    log_info "Staging changes for commit..."
    git add .
    
    # Generate commit message
    local commit_message
    commit_message=$(generate_commit_message "$current_version")
    
    # Commit changes
    log_info "Committing changes with message: $commit_message"
    git commit -m "$commit_message"
    
    # Push to origin
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "Pushing to origin/$current_branch..."
    
    if git push origin "$current_branch"; then
        log_success "Successfully deployed version $current_version!"
        log_success "Commit: $commit_message"
        log_success "Branch: $current_branch"
        
        # Show final status
        echo
        echo "Deployment Summary:"
        echo "=================="
        echo "Version: $current_version"
        echo "Commit: $(git rev-parse --short HEAD)"
        echo "Branch: $current_branch"
        echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
        echo "CHANGELOG updated: Yes"
        echo "=================="
    else
        log_error "Failed to push to origin/$current_branch"
        log_error "Deployment incomplete. Please check your git configuration and network connection."
        exit 1
    fi
}

# Script entry point
main() {
    # Check for help flag
    if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        echo "Usage: $0 [options]"
        echo ""
        echo "Deploy script for Invoice Rate Detection System"
        echo ""
        echo "This script will:"
        echo "  1. Create a summary of changes since last commit"
        echo "  2. Update CHANGELOG.md with date and version"
        echo "  3. Commit git with unique commit title (timestamp) and push to origin"
        echo ""
        echo "Options:"
        echo "  -h, --help    Show this help message"
        echo "  --dry-run     Show what would be done without making changes"
        echo ""
        echo "Requirements:"
        echo "  - Git repository initialized"
        echo "  - Python 3 available"
        echo "  - cli/version.py file with version information"
        echo ""
        exit 0
    fi
    
    # Check for dry-run flag
    if [[ "$1" == "--dry-run" ]]; then
        log_info "DRY RUN MODE - No changes will be made"
        echo ""
        
        check_git_repo
        
        local current_version
        current_version=$(get_current_version)
        echo "Current version: $current_version"
        echo ""
        
        local changes_summary
        changes_summary=$(generate_changes_summary)
        echo "Changes that would be deployed:"
        echo "==============================="
        echo -e "$changes_summary"
        echo "==============================="
        echo ""
        
        local commit_message
        commit_message=$(generate_commit_message "$current_version")
        echo "Commit message: $commit_message"
        echo "CHANGELOG would be updated with version $current_version"
        echo ""
        log_info "Dry run complete. Use '$0' to perform actual deployment."
        exit 0
    fi
    
    # Run deployment
    deploy
}

# Run main function with all arguments
main "$@"