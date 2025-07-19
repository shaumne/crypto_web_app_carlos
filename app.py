from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import threading
import time
import logging
from typing import Dict, List, Optional
import ccxt
import requests
import hmac
import hashlib
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'crypto-trading-webapp-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crypto_trading.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models first
from models import db, User, Coin, Trade, Order, Position, TechnicalAnalysis, TradingSettings, SystemLog

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

def create_admin_user():
    """Create default admin user if it doesn't exist"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@cryptotrading.local',
            password_hash=generate_password_hash('1234'),
            is_admin=True,
            created_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin user created with username: admin, password: 1234")

def initialize_database():
    """Initialize database with default data"""
    with app.app_context():
        db.create_all()
        create_admin_user()
        logger.info("Database initialized successfully")

def register_blueprints():
    """Register all blueprints after database initialization"""
    # Import routes
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.trading import trading_bp
    from routes.orders import orders_bp
    from routes.positions import positions_bp
    from routes.analytics import analytics_bp
    from routes.settings import settings_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(positions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)

if __name__ == '__main__':
    initialize_database()
    register_blueprints()
    
    # Start background monitoring threads
    from services.trading_monitor import TradingMonitor
    from services.tp_sl_monitor import TpSlMonitor
    
    trading_monitor = TradingMonitor()
    tp_sl_monitor = TpSlMonitor()
    
    # Start monitoring in background threads
    threading.Thread(target=trading_monitor.run, daemon=True).start()
    threading.Thread(target=tp_sl_monitor.run, daemon=True).start()
    
    logger.info("Starting Crypto Trading Web Application")
    app.run(host='0.0.0.0', port=5000, debug=True) 