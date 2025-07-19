from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import func, text
import json

# This db instance will be initialized by app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    last_password_change = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Coin(db.Model):
    """Model for cryptocurrency coins being tracked"""
    __tablename__ = 'coins'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)  # e.g., BTC_USDT
    original_symbol = db.Column(db.String(20), nullable=False)  # e.g., BTC
    base_currency = db.Column(db.String(10), default='USDT')
    is_active = db.Column(db.Boolean, default=True)
    is_trading_enabled = db.Column(db.Boolean, default=True)
    min_order_size = db.Column(db.Float, default=10.0)
    max_order_size = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    technical_analyses = db.relationship('TechnicalAnalysis', backref='coin_ref', lazy=True, cascade='all, delete-orphan')
    trades = db.relationship('Trade', backref='coin_ref', lazy=True)
    orders = db.relationship('Order', backref='coin_ref', lazy=True)
    positions = db.relationship('Position', backref='coin_ref', lazy=True)
    
    def __repr__(self):
        return f'<Coin {self.symbol}>'
    
    @property
    def latest_analysis(self):
        """Get the latest technical analysis for this coin"""
        return TechnicalAnalysis.query.filter_by(coin_id=self.id).order_by(TechnicalAnalysis.timestamp.desc()).first()
    
    @property
    def open_positions(self):
        """Get open positions for this coin"""
        return Position.query.filter_by(coin_id=self.id, status='open').all()

class TechnicalAnalysis(db.Model):
    """Model for storing technical analysis data"""
    __tablename__ = 'technical_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, db.ForeignKey('coins.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Price data
    last_price = db.Column(db.Float, nullable=False)
    high_24h = db.Column(db.Float)
    low_24h = db.Column(db.Float)
    volume_24h = db.Column(db.Float)
    volume_ratio = db.Column(db.Float, default=1.0)
    
    # Technical indicators
    rsi = db.Column(db.Float)
    ma50 = db.Column(db.Float)
    ma200 = db.Column(db.Float)
    ema10 = db.Column(db.Float)
    atr = db.Column(db.Float)
    
    # Support and resistance
    support_level = db.Column(db.Float)
    resistance_level = db.Column(db.Float)
    
    # Trading signals
    buy_signal = db.Column(db.Boolean, default=False)
    sell_signal = db.Column(db.Boolean, default=False)
    action = db.Column(db.String(10), default='WAIT')  # BUY, SELL, WAIT
    
    # Take profit and stop loss recommendations
    take_profit = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    risk_reward_ratio = db.Column(db.Float)
    
    # Validation flags for moving averages
    ma50_valid = db.Column(db.Boolean, default=False)
    ma200_valid = db.Column(db.Boolean, default=False)
    ema10_valid = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<TechnicalAnalysis {self.coin.symbol} at {self.timestamp}>'
    
    @property
    def signal_strength(self):
        """Calculate signal strength based on multiple factors"""
        strength = 0
        if self.ma200_valid:
            strength += 1
        if self.ma50_valid:
            strength += 1
        if self.ema10_valid:
            strength += 1
        if self.volume_ratio > 1.5:
            strength += 1
        if self.rsi < 30:
            strength += 2
        elif self.rsi < 40:
            strength += 1
        return min(strength, 5)  # Max strength is 5

class Trade(db.Model):
    """Model for executed trades"""
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, db.ForeignKey('coins.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'))
    
    # Trade details
    trade_type = db.Column(db.String(10), nullable=False)  # BUY, SELL
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    fees = db.Column(db.Float, default=0.0)
    
    # Timestamps
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Exchange information
    exchange_order_id = db.Column(db.String(100))
    exchange_trade_id = db.Column(db.String(100))
    
    # Relationships
    orders = db.relationship('Order', backref='trade_ref', lazy=True)
    
    def __repr__(self):
        return f'<Trade {self.trade_type} {self.quantity} {self.coin.symbol} at {self.price}>'
    
    @property
    def total_with_fees(self):
        """Total value including fees"""
        return self.total_value + self.fees

class Order(db.Model):
    """Model for orders (including pending orders)"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, db.ForeignKey('coins.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'))
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'))
    
    # Order details
    order_type = db.Column(db.String(20), nullable=False)  # MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT
    side = db.Column(db.String(10), nullable=False)  # BUY, SELL
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)  # Null for market orders
    stop_price = db.Column(db.Float)  # For stop orders
    
    # Status tracking
    status = db.Column(db.String(20), default='PENDING')  # PENDING, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED
    filled_quantity = db.Column(db.Float, default=0.0)
    average_fill_price = db.Column(db.Float)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    filled_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Exchange information
    exchange_order_id = db.Column(db.String(100), unique=True)
    client_order_id = db.Column(db.String(100))
    
    # Additional metadata
    notes = db.Column(db.Text)
    is_manual = db.Column(db.Boolean, default=False)  # True if manually placed
    
    def __repr__(self):
        return f'<Order {self.side} {self.quantity} {self.coin.symbol} - {self.status}>'
    
    @property
    def remaining_quantity(self):
        """Remaining quantity to be filled"""
        return self.quantity - self.filled_quantity
    
    @property
    def fill_percentage(self):
        """Percentage of order that has been filled"""
        if self.quantity == 0:
            return 0
        return (self.filled_quantity / self.quantity) * 100

class Position(db.Model):
    """Model for trading positions"""
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, db.ForeignKey('coins.id'), nullable=False)
    
    # Position details
    quantity = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float)
    
    # Entry information
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    entry_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    
    # Exit information
    exit_price = db.Column(db.Float)
    exit_date = db.Column(db.DateTime)
    exit_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    
    # Risk management
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    trailing_stop = db.Column(db.Float)
    
    # Position status
    status = db.Column(db.String(20), default='open')  # open, closed, partially_closed
    
    # P&L tracking
    unrealized_pnl = db.Column(db.Float, default=0.0)
    realized_pnl = db.Column(db.Float, default=0.0)
    fees_paid = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trades = db.relationship('Trade', backref='position_ref', lazy=True)
    orders = db.relationship('Order', backref='position_ref', lazy=True, 
                           foreign_keys='Order.position_id')
    
    def __repr__(self):
        return f'<Position {self.quantity} {self.coin.symbol} at {self.entry_price}>'
    
    @property
    def total_value(self):
        """Total value of the position at entry"""
        return self.quantity * self.entry_price
    
    @property
    def current_value(self):
        """Current value of the position"""
        if self.current_price:
            return self.quantity * self.current_price
        return self.total_value
    
    @property
    def pnl_percentage(self):
        """P&L as percentage"""
        if self.status == 'closed':
            if self.exit_price and self.entry_price:
                return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:
            if self.current_price and self.entry_price:
                return ((self.current_price - self.entry_price) / self.entry_price) * 100
        return 0.0
    
    @property
    def pnl_amount(self):
        """P&L in absolute amount"""
        if self.status == 'closed':
            return self.realized_pnl
        else:
            return self.unrealized_pnl
    
    def update_unrealized_pnl(self):
        """Update unrealized P&L based on current price"""
        if self.current_price and self.status == 'open':
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
            db.session.commit()

class TradingSettings(db.Model):
    """Model for storing trading settings and preferences"""
    __tablename__ = 'trading_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Trading parameters
    default_trade_amount = db.Column(db.Float, default=10.0)
    max_positions = db.Column(db.Integer, default=10)
    risk_percentage = db.Column(db.Float, default=2.0)  # % of portfolio per trade
    stop_loss_percentage = db.Column(db.Float, default=5.0)
    take_profit_percentage = db.Column(db.Float, default=10.0)
    
    # Technical analysis settings
    rsi_oversold = db.Column(db.Float, default=30.0)
    rsi_overbought = db.Column(db.Float, default=70.0)
    atr_multiplier = db.Column(db.Float, default=2.0)
    volume_threshold = db.Column(db.Float, default=1.5)
    
    # Exchange settings
    exchange_name = db.Column(db.String(50), default='crypto.com')
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    sandbox_mode = db.Column(db.Boolean, default=True)
    
    # Notification settings
    telegram_enabled = db.Column(db.Boolean, default=False)
    telegram_bot_token = db.Column(db.String(200))
    telegram_chat_id = db.Column(db.String(100))
    
    # Monitoring settings
    analysis_interval = db.Column(db.Integer, default=30)  # seconds
    tp_sl_check_interval = db.Column(db.Integer, default=10)  # seconds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TradingSettings for User {self.user_id}>'

class SystemLog(db.Model):
    """Model for system logs and events"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(10), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    category = db.Column(db.String(50), nullable=False)  # TRADING, ANALYSIS, SYSTEM, API
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)  # JSON string for additional details
    
    # Related entities
    coin_id = db.Column(db.Integer, db.ForeignKey('coins.id'))
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'))
    
    def __repr__(self):
        return f'<SystemLog {self.level} - {self.category}: {self.message[:50]}>'
    
    @staticmethod
    def log(level, category, message, details=None, **kwargs):
        """Helper method to create log entries"""
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            details=json.dumps(details) if details else None,
            **kwargs
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

# Helper functions for database operations
def get_active_coins():
    """Get all active coins for trading"""
    return Coin.query.filter_by(is_active=True, is_trading_enabled=True).all()

def get_open_positions():
    """Get all open positions"""
    return Position.query.filter_by(status='open').all()

def get_pending_orders():
    """Get all pending orders"""
    return Order.query.filter(Order.status.in_(['PENDING', 'PARTIALLY_FILLED'])).all()

def get_recent_trades(days=7):
    """Get recent trades within specified days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    return Trade.query.filter(Trade.executed_at >= cutoff_date).all()

def get_trading_performance(days=30):
    """Get trading performance metrics for the last N days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get closed positions
    closed_positions = Position.query.filter(
        Position.status == 'closed',
        Position.exit_date >= cutoff_date
    ).all()
    
    total_trades = len(closed_positions)
    winning_trades = len([p for p in closed_positions if p.realized_pnl > 0])
    losing_trades = total_trades - winning_trades
    
    total_pnl = sum(p.realized_pnl for p in closed_positions)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'closed_positions': closed_positions
    } 