# macOS Manual Steps - Starting from NOTHING

**Use this guide when you have NO files and need to set everything up manually on macOS**

## What This Guide Does
This replaces the broken `.command` file and walks you through every single step to get the Invoice Validator working on your Mac.

## Step 1: Open Terminal
1. Press `Cmd + Space` to open Spotlight
2. Type "Terminal" and press Enter
3. A black window will open - this is your Terminal

## Step 2: Check What You Have

### Check Python
```bash
python3 --version
```

**If you get an error or version less than 3.8:**
```bash
# Install Python via Homebrew (recommended)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

**OR download Python from:** https://www.python.org/downloads/

### Check UV Package Manager
```bash
uv --version
```

**If you get "command not found":**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Check Git
```bash
git --version
```

**If you get "command not found":**
```bash
xcode-select --install
```
(This installs Git and other developer tools)

## Step 3: Create the Correct Working Directory
```bash
mkdir -p ~/Applications/InvoiceRateDetector
cd ~/Applications/InvoiceRateDetector
```

## Step 4: Download the Project
```bash
git clone https://github.com/nuosis/invoice_line_cost_detection.git
cd invoice_line_cost_detection
```

## Step 5: Install the Project
```bash
uv sync
uv pip install -e .
```

## Step 6: Test the Installation
```bash
uv run invoice-checker status
```

**You should see a status report. If you get errors, something went wrong in the previous steps.**

## Step 7: Run the Application

### Option A: Interactive Mode (Recommended)
```bash
uv run invoice-checker
```

This gives you a menu to:
- Set up parts database
- Process invoices
- Configure settings

### Option B: Quick Mode
```bash
uv run invoice-checker quick
```

This processes invoices with default settings.

## Step 8: Basic Usage

### Add Parts to Database
```bash
uv run invoice-checker parts add --code "ABC123" --description "Test Part" --rate 1.50
```

### Process Invoices
```bash
uv run invoice-checker process --input ~/Desktop/invoices --output ~/Desktop/report.csv
```

### View Report
```bash
open ~/Desktop/report.csv
```

## Complete Example Workflow

Here's everything in order if you're starting from absolutely nothing:

```bash
# 1. Open Terminal (Cmd+Space, type "Terminal")

# 2. Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Install Python (if needed)
brew install python

# 4. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 5. Install Git (if needed)
xcode-select --install

# 6. Create working directory (matches what .command script does)
mkdir -p ~/Applications/InvoiceRateDetector
cd ~/Applications/InvoiceRateDetector

# 7. Download project
git clone https://github.com/nuosis/invoice_line_cost_detection.git
cd invoice_line_cost_detection

# 8. Install project
uv sync
uv pip install -e .

# 9. Test it works
uv run invoice-checker status

# 10. Run the application
uv run invoice-checker
```

## Troubleshooting

### "Command not found" errors
- Restart Terminal after installing anything
- Or run: `source ~/.zshrc`

### "Permission denied" errors
```bash
sudo xcode-select --install
```

### "Git clone failed"
Check your internet connection and try again.

### "UV sync failed"
Make sure you're in the `invoice_line_cost_detection` directory:
```bash
pwd
ls -la
```
You should see `pyproject.toml` in the file list.

## What Each Command Does

- `python3 --version` - Checks if Python is installed
- `uv --version` - Checks if UV package manager is installed
- `git clone` - Downloads the project from GitHub
- `uv sync` - Installs all required dependencies
- `uv pip install -e .` - Installs the invoice checker program
- `uv run invoice-checker` - Runs the program

## Getting Help

If you get stuck:
1. Take a screenshot of the error
2. Email: marcus@claritybusinesssolutions.ca
3. Include what step you were on when it failed

## Summary

This guide replaces the broken `.command` file by doing everything manually:
1. Install required software (Python, UV, Git)
2. Download the project
3. Install dependencies
4. Run the application

Once this is done once, you can just run `uv run invoice-checker` from the project directory to use the application.