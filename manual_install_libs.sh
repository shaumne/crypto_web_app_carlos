#!/bin/bash

#=============================================================================
# Manual Library Installation for Crypto Trading App
# Run this after deploy_crypto_app.sh completes
#=============================================================================

APP_DIR="/home/ubuntu/crypto_trading_app"

echo "📦 Installing Python libraries manually..."

# Check if app directory exists
if [[ ! -d "$APP_DIR" ]]; then
    echo "❌ Error: $APP_DIR not found!"
    echo "💡 Run deploy_crypto_app.sh first"
    exit 1
fi

cd "$APP_DIR"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "❌ Error: Virtual environment not found!"
    echo "💡 Run deploy_crypto_app.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "🔧 Installing core Flask dependencies..."
pip install --no-cache-dir flask flask-sqlalchemy flask-login gunicorn python-dotenv requests

echo "📈 Installing trading/financial libraries..."
pip install --no-cache-dir yfinance ccxt

echo "🚀 Installing production server dependencies..."  
pip install --no-cache-dir gevent

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
    echo "🗄️ Initializing database..."
    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Database initialized successfully!')
"
    
    echo "🚀 Starting crypto trading service..."
    sudo systemctl start crypto-trading.service
    
    sleep 3
    
    if sudo systemctl is-active --quiet crypto-trading.service; then
        echo "✅ Crypto Trading service started successfully!"
        
        # Test HTTP response
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|302"; then
            echo "✅ HTTP response test passed!"
            echo "🌐 Application is ready and accessible!"
        else
            echo "⚠️ HTTP response test failed, but service is running"
        fi
    else
        echo "❌ Service failed to start. Check logs:"
        sudo journalctl -u crypto-trading.service --no-pager -n 20
    fi
else
    echo "❌ Application import failed!"
fi

echo ""
echo "🎉 Manual installation completed!"
echo ""
echo "📋 Status Check:"
echo "  • Nginx: $(sudo systemctl is-active nginx)"
echo "  • Crypto Trading: $(sudo systemctl is-active crypto-trading.service)"
echo ""
echo "🌐 Access your app:"
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
echo "  • URL: http://$SERVER_IP"
echo "  • Login: admin / 1234"
echo ""
echo "💡 Don't forget to change the default password!" 