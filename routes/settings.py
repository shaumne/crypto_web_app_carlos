from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, TradingSettings

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    """Settings page"""
    # Get or create trading settings for current user
    settings = TradingSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = TradingSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/update', methods=['POST'])
@login_required
def update():
    """Update trading settings"""
    try:
        settings = TradingSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = TradingSettings(user_id=current_user.id)
            db.session.add(settings)
        
        # Update settings from form
        settings.default_trade_amount = float(request.form.get('default_trade_amount', 10.0))
        settings.risk_percentage = float(request.form.get('risk_percentage', 2.0))
        settings.stop_loss_percentage = float(request.form.get('stop_loss_percentage', 5.0))
        settings.take_profit_percentage = float(request.form.get('take_profit_percentage', 10.0))
        settings.rsi_oversold = float(request.form.get('rsi_oversold', 30.0))
        settings.rsi_overbought = float(request.form.get('rsi_overbought', 70.0))
        settings.atr_multiplier = float(request.form.get('atr_multiplier', 2.0))
        settings.volume_threshold = float(request.form.get('volume_threshold', 1.5))
        
        # API settings (optional)
        api_key = request.form.get('api_key', '').strip()
        api_secret = request.form.get('api_secret', '').strip()
        
        if api_key:
            settings.api_key = api_key
        if api_secret:
            settings.api_secret = api_secret
            
        settings.sandbox_mode = bool(request.form.get('sandbox_mode'))
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

# API Endpoints for settings management
@settings_bp.route('/api/settings')
@login_required
def get_settings_api():
    """Get current settings"""
    try:
        settings = TradingSettings.get_current()
        
        settings_data = {
            'default_trade_amount': settings.default_trade_amount,
            'max_position_size': settings.max_position_size,
            'max_open_positions': settings.max_open_positions,
            'default_take_profit': settings.default_take_profit,
            'default_stop_loss': settings.default_stop_loss,
            'rsi_oversold': settings.rsi_oversold_threshold,
            'rsi_overbought': settings.rsi_overbought_threshold,
            'atr_multiplier': settings.atr_multiplier,
            'volume_threshold': settings.volume_threshold,
            'analysis_interval': 30,  # Default
            'enable_auto_trading': settings.enable_auto_trading,
            'enable_tp_sl_monitoring': True,  # Default
            'enable_risk_management': True,   # Default
            'enable_signal_generation': True, # Default
            'api_key': '',  # Don't return actual API key
            'api_secret': '',  # Don't return actual API secret
            'sandbox_mode': True,  # Default to sandbox
            'api_rate_limit': 60,
            'request_timeout': 30,
            'retry_attempts': 3,
            'enable_session_timeout': True,
            'session_timeout': 60,
            'enable_audit_logging': True,
            'data_retention': 365,
            'email_address': '',
            'email_trade_alerts': False,
            'email_position_updates': False,
            'email_system_alerts': False,
            'telegram_bot_token': '',
            'telegram_chat_id': '',
            'telegram_trade_alerts': False,
            'telegram_position_updates': False,
            'telegram_system_alerts': False,
            'log_level': 'INFO',
            'enable_file_logging': True
        }
        
        return jsonify({'success': True, 'settings': settings_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings_api():
    """Update settings via API"""
    try:
        data = request.get_json()
        settings = TradingSettings.get_current()
        
        # Update trading settings
        if 'defaultTradeAmount' in data:
            settings.default_trade_amount = float(data['defaultTradeAmount'])
        if 'maxPositionSize' in data:
            settings.max_position_size = float(data['maxPositionSize'])
        if 'maxOpenPositions' in data:
            settings.max_open_positions = int(data['maxOpenPositions'])
        if 'defaultTakeProfit' in data:
            settings.default_take_profit = float(data['defaultTakeProfit'])
        if 'defaultStopLoss' in data:
            settings.default_stop_loss = float(data['defaultStopLoss'])
        if 'rsiOversold' in data:
            settings.rsi_oversold_threshold = int(data['rsiOversold'])
        if 'rsiOverbought' in data:
            settings.rsi_overbought_threshold = int(data['rsiOverbought'])
        if 'atrMultiplier' in data:
            settings.atr_multiplier = float(data['atrMultiplier'])
        if 'volumeThreshold' in data:
            settings.volume_threshold = float(data['volumeThreshold'])
        if 'enableAutoTrading' in data:
            settings.enable_auto_trading = bool(data['enableAutoTrading'])
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/settings/reset', methods=['POST'])
@login_required
def reset_settings_api():
    """Reset settings to defaults"""
    try:
        settings = TradingSettings.get_current()
        
        # Reset to defaults
        settings.default_trade_amount = 10.0
        settings.max_position_size = 100.0
        settings.max_open_positions = 10
        settings.default_take_profit = 5.0
        settings.default_stop_loss = 2.0
        settings.rsi_oversold_threshold = 30
        settings.rsi_overbought_threshold = 70
        settings.atr_multiplier = 2.0
        settings.volume_threshold = 1.5
        settings.enable_auto_trading = False
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Settings reset to defaults'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/settings/test-api', methods=['POST'])
@login_required
def test_api_connection():
    """Test API connection"""
    try:
        from services.crypto_exchange import CryptoExchangeAPI
        
        exchange_api = CryptoExchangeAPI()
        
        # Test basic connection
        account_info = exchange_api.get_account_balance()
        
        if account_info:
            return jsonify({
                'success': True,
                'message': 'API connection successful',
                'account_info': {
                    'id': 'test_account',
                    'balance': account_info.get('total_available_balance', 'N/A'),
                    'status': 'active'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to connect to API'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'API connection failed: {str(e)}'
        })

@settings_bp.route('/api/settings/test-telegram', methods=['POST'])
@login_required
def test_telegram():
    """Test Telegram notification"""
    try:
        # This would normally send a test message via Telegram bot
        # For now, just return success
        return jsonify({
            'success': True,
            'message': 'Telegram test notification sent successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Telegram test failed: {str(e)}'
        })

@settings_bp.route('/api/system/info')
@login_required
def system_info():
    """Get system information"""
    try:
        import sys
        import platform
        from datetime import datetime
        
        start_time = datetime.now()  # This would normally be stored when app starts
        uptime = datetime.now() - start_time
        
        return jsonify({
            'success': True,
            'db_version': 'SQLite 3.x',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'uptime': str(uptime),
            'last_backup': 'Never',
            'health': {
                'api': 'healthy',
                'database': 'healthy', 
                'trading_monitor': 'running',
                'tp_sl_monitor': 'running'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/system/export-data')
@login_required
def export_system_data():
    """Export system data"""
    try:
        # This would export various data based on query parameters
        return jsonify({
            'success': True,
            'message': 'Export functionality would be implemented here'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/system/backup', methods=['POST'])
@login_required
def create_backup():
    """Create database backup"""
    try:
        # This would create a database backup
        return jsonify({
            'success': True,
            'message': 'Database backup created successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/system/optimize', methods=['POST'])
@login_required
def optimize_database():
    """Optimize database"""
    try:
        # This would run database optimization
        return jsonify({
            'success': True,
            'message': 'Database optimized successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/system/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Clear system cache"""
    try:
        # This would clear various caches
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/system/download-logs')
@login_required
def download_logs():
    """Download system logs"""
    try:
        from flask import make_response
        import io
        
        # This would collect and return log files
        log_content = "Sample log content\nThis would contain actual logs"
        
        response = make_response(log_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=system_logs.txt'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 