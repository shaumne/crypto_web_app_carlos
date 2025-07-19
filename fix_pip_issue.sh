#!/bin/bash

#=============================================================================
# Quick Fix for Pip Setuptools Issue
# Run this on Ubuntu server if deployment fails with setuptools error
#=============================================================================

APP_DIR="/home/ubuntu/crypto_trading_app"

echo "🔧 Fixing pip setuptools issue..."

# Navigate to app directory
cd "$APP_DIR" || { echo "❌ App directory not found!"; exit 1; }

# Activate virtual environment
source venv/bin/activate || { echo "❌ Virtual environment not found!"; exit 1; }

echo "📦 Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

echo "📋 Installing requirements with fallback..."

# Try installing requirements normally first
if pip install --no-cache-dir -r requirements.txt; then
    echo "✅ Requirements installed successfully!"
else
    echo "⚠️ Normal installation failed, trying one by one..."
    
    # Install core dependencies first
    pip install --no-cache-dir flask flask-sqlalchemy flask-login gunicorn python-dotenv
    
    # Then install each requirement individually
    while IFS= read -r requirement; do
        if [[ ! -z "$requirement" && ! "$requirement" =~ ^#.* ]]; then
            echo "Installing: $requirement"
            pip install --no-cache-dir "$requirement" || echo "⚠️ Failed to install: $requirement"
        fi
    done < requirements.txt
fi

# Install production dependencies
echo "🚀 Installing production dependencies..."
pip install --no-cache-dir gunicorn gevent

echo "🧪 Testing application import..."
python -c "
try:
    from app import app
    print('✅ Application imports successfully!')
except Exception as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Application test passed!"
    
    # Restart service if it exists
    if systemctl is-enabled crypto-trading.service >/dev/null 2>&1; then
        echo "🔄 Restarting service..."
        sudo systemctl restart crypto-trading.service
        
        sleep 3
        
        if sudo systemctl is-active --quiet crypto-trading.service; then
            echo "✅ Service restarted successfully!"
        else
            echo "❌ Service restart failed. Check logs:"
            sudo journalctl -u crypto-trading.service --no-pager -n 20
        fi
    else
        echo "ℹ️ Service not found, continuing..."
    fi
else
    echo "❌ Application test failed!"
fi

echo "🎉 Fix completed!" 