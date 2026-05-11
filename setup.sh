#!/bin/bash

# Restaurant Invoices - Easy Setup Script
# This script sets up the environment and dependencies for the app.

echo "🚀 Starting Restaurant Invoices Setup..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# 2. Check for Poppler (required for PDF extraction)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "⚠️ Homebrew not found. Cannot check for 'poppler' (needed for PDFs)."
    elif ! brew list poppler &> /dev/null; then
        echo "📦 Installing poppler for PDF support..."
        brew install poppler
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &> /dev/null; then
        echo "📦 Installing poppler-utils for PDF support..."
        sudo apt-get update && sudo apt-get install -y poppler-utils
    fi
fi

# 3. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 4. Install Dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Initialize Database
echo "Initializing database..."
python3 -c "from app.database.models import init_db; init_db()"

echo "------------------------------------------------"
echo "✅ Setup Complete!"
echo "To start the app, run:"
echo "source venv/bin/activate"
echo "streamlit run main.py"
echo "------------------------------------------------"
