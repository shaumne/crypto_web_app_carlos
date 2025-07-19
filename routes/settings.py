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