#!/bin/bash
# Script to fix backend dependencies and restart the server

echo "🔧 Fixing backend dependencies..."

# Activate virtual environment
source venv/bin/activate 2>/dev/null || {
    echo "❌ Virtual environment not found. Please activate it manually."
    exit 1
}

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Reinstall specific packages with compatible versions
echo "🔄 Reinstalling dependencies with compatible versions..."
pip install --upgrade requests==2.31.0 urllib3==2.0.7 charset-normalizer==3.3.2

# Verify installation
echo "✅ Verifying installation..."
python -c "import requests; print(f'requests version: {requests.__version__}')"
python -c "import urllib3; print(f'urllib3 version: {urllib3.__version__}')"
python -c "import charset_normalizer; print(f'charset_normalizer version: {charset_normalizer.__version__}')"

echo "✨ Dependencies fixed! You can now restart your backend server."
echo ""
echo "To restart the server, run:"
echo "  cd /Users/admin/Documents/AI-Playground/ReachGenie/backend"
echo "  nvm use node"
echo "  python src/main.py"
