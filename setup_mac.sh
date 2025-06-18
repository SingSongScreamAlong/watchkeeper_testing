#!/bin/bash
# Mac Mini setup script for WATCHKEEPER Testing Edition
# This script sets up the environment for running WATCHKEEPER Testing Edition on a Mac Mini

# Print header
echo "=================================================="
echo "WATCHKEEPER Testing Edition - Mac Mini Setup Script"
echo "=================================================="
echo

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is designed for macOS only."
    exit 1
fi

# Check if running on a Mac Mini (best effort)
MODEL=$(system_profiler SPHardwareDataType | grep "Model Name" | awk -F': ' '{print $2}')
if [[ "$MODEL" != *"Mac mini"* ]]; then
    echo "Warning: This script is optimized for Mac Mini hardware."
    echo "Detected model: $MODEL"
    echo
    read -p "Continue anyway? (y/n): " confirm
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Create directories
echo "Creating directories..."
mkdir -p data/logs
echo "✓ Created data directories"

# Check for Python 3.8+
echo "Checking Python version..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8) ]]; then
        echo "Error: Python 3.8+ is required. Found Python $PYTHON_VERSION"
        echo "Please install Python 3.8 or newer."
        exit 1
    else
        echo "✓ Python $PYTHON_VERSION detected"
    fi
else
    echo "Error: Python 3 not found. Please install Python 3.8 or newer."
    exit 1
fi

# Check for pip
echo "Checking for pip..."
if ! command -v pip3 &>/dev/null; then
    echo "Error: pip3 not found. Please install pip for Python 3."
    exit 1
else
    echo "✓ pip3 detected"
fi

# Create virtual environment
echo "Setting up virtual environment..."
if ! command -v python3 -m venv &>/dev/null; then
    echo "Installing virtualenv..."
    pip3 install virtualenv
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Created virtual environment"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Check for Ollama
echo "Checking for Ollama..."
if ! command -v ollama &>/dev/null; then
    echo "Ollama not found. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
else
    echo "✓ Ollama detected"
fi

# Pull Llama 3.2 3B model
echo "Checking for Llama 3.2 3B model..."
if ! ollama list | grep -q "llama3.2:3b"; then
    echo "Downloading Llama 3.2 3B model (this may take a while)..."
    ollama pull llama3.2:3b
    echo "✓ Llama 3.2 3B model downloaded"
else
    echo "✓ Llama 3.2 3B model already downloaded"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    # Generate random API key
    API_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
    
    # Update API key in .env file
    sed -i '' "s/API_KEY=.*/API_KEY=$API_KEY/" .env
    
    echo "✓ Created .env file with random API key"
else
    echo "✓ .env file already exists"
fi

# Set up database
echo "Setting up database..."
python -c "from src.core.database import init_db; import asyncio; asyncio.run(init_db())"
echo "✓ Database initialized"

# Make run script executable
echo "Setting permissions..."
chmod +x run_testing.py
echo "✓ Made run_testing.py executable"

# Create launchd plist for auto-start (optional)
echo "Do you want to set up WATCHKEEPER to start automatically on boot? (y/n)"
read auto_start

if [[ $auto_start == "y" || $auto_start == "Y" ]]; then
    echo "Setting up auto-start..."
    
    # Get current directory
    CURRENT_DIR=$(pwd)
    
    # Create launchd plist
    cat > ~/Library/LaunchAgents/com.watchkeeper.testing.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.watchkeeper.testing</string>
    <key>ProgramArguments</key>
    <array>
        <string>${CURRENT_DIR}/venv/bin/python3</string>
        <string>${CURRENT_DIR}/run_testing.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${CURRENT_DIR}</string>
    <key>StandardOutPath</key>
    <string>${CURRENT_DIR}/data/logs/watchkeeper.log</string>
    <key>StandardErrorPath</key>
    <string>${CURRENT_DIR}/data/logs/watchkeeper_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOL

    # Load the plist
    launchctl load ~/Library/LaunchAgents/com.watchkeeper.testing.plist
    
    echo "✓ Auto-start configured"
fi

# Optimize Mac Mini settings for better performance
echo "Do you want to optimize Mac Mini settings for better performance? (y/n)"
read optimize

if [[ $optimize == "y" || $optimize == "Y" ]]; then
    echo "Optimizing Mac Mini settings..."
    
    # Disable unnecessary services
    echo "Disabling unnecessary services..."
    launchctl unload -w /System/Library/LaunchAgents/com.apple.notificationcenterui.plist 2>/dev/null || true
    
    # Reduce transparency and animations
    echo "Reducing visual effects..."
    defaults write com.apple.universalaccess reduceTransparency -bool true
    defaults write com.apple.universalaccess reduceMotion -bool true
    
    # Disable automatic updates
    echo "Disabling automatic updates..."
    sudo softwareupdate --schedule off
    
    echo "✓ Mac Mini optimized for better performance"
    echo "Note: Some changes may require a restart to take effect"
fi

# Print success message
echo
echo "=================================================="
echo "WATCHKEEPER Testing Edition setup complete!"
echo "=================================================="
echo
echo "To start the application, run:"
echo "  ./run_testing.py"
echo
echo "To access the API documentation, visit:"
echo "  http://localhost:8000/docs"
echo
echo "API Key: $(grep API_KEY .env | cut -d= -f2)"
echo
echo "For more information, see README.md"
echo "=================================================="

# Deactivate virtual environment
deactivate
