#!/bin/bash
#
# Step 4: Clone GitHub Repository
# Gets your BMS analytics code from GitHub
#

set -e

echo "=========================================="
echo "Clone GitHub Repository"
echo "=========================================="
echo ""

REPO_URL="https://github.com/birdlab-tech/building-analytics.git"
INSTALL_DIR="/opt/bms-analytics"

# Clone repository
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Directory exists. Pulling latest changes..."
    cd $INSTALL_DIR
    git pull
else
    echo "📥 Cloning repository..."
    git clone $REPO_URL $INSTALL_DIR
fi

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
cd $INSTALL_DIR
python3 -m venv venv

# Install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Repository cloned and dependencies installed!"
echo ""
echo "Location: $INSTALL_DIR"
echo ""
