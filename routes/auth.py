from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Account is deactivated. Please contact administrator.', 'error')
                return render_template('auth/login.html')
            
            # Login successful
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler"""
    username = current_user.username
    logout_user()
    flash(f'You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page and handler"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        if len(new_password) < 4:
            flash('New password must be at least 4 characters long.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password == current_password:
            flash('New password must be different from current password.', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        current_user.last_password_change = datetime.utcnow()
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('auth/change_password.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    email = request.form.get('email', '').strip()
    
    if not email:
        flash('Email address is required.', 'error')
        return redirect(url_for('auth.profile'))
    
    # Check if email is already used by another user
    existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing_user:
        flash('Email address is already in use.', 'error')
        return redirect(url_for('auth.profile'))
    
    # Update email
    current_user.email = email
    db.session.commit()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('auth.profile'))

# API routes for AJAX requests
@auth_bp.route('/api/check-password', methods=['POST'])
@login_required
def check_password_api():
    """API endpoint to check if current password is correct"""
    data = request.get_json()
    password = data.get('password', '')
    
    is_correct = check_password_hash(current_user.password_hash, password)
    
    return jsonify({
        'valid': is_correct,
        'message': 'Password is correct' if is_correct else 'Password is incorrect'
    })

@auth_bp.route('/api/validate-password', methods=['POST'])
@login_required
def validate_password_api():
    """API endpoint to validate new password strength"""
    data = request.get_json()
    password = data.get('password', '')
    
    issues = []
    
    if len(password) < 4:
        issues.append('Password must be at least 4 characters long')
    
    if len(password) > 128:
        issues.append('Password must be less than 128 characters')
    
    # Check if password is same as current
    if check_password_hash(current_user.password_hash, password):
        issues.append('New password must be different from current password')
    
    return jsonify({
        'valid': len(issues) == 0,
        'issues': issues,
        'strength': calculate_password_strength(password)
    })

def calculate_password_strength(password):
    """Calculate password strength score (0-100)"""
    if not password:
        return 0
    
    score = 0
    length = len(password)
    
    # Length score (max 40 points)
    if length >= 8:
        score += 40
    elif length >= 6:
        score += 30
    elif length >= 4:
        score += 20
    else:
        score += 10
    
    # Character diversity (max 60 points)
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    char_types = sum([has_lower, has_upper, has_digit, has_special])
    score += char_types * 15  # 15 points per character type
    
    return min(score, 100)

# API Endpoints for profile management
@auth_bp.route('/api/auth/user-stats')
@login_required
def user_stats():
    """Get user trading statistics"""
    try:
        from models import Trade, Position
        
        # Get user's trades and positions
        trades = Trade.query.filter_by(user_id=current_user.id).all()
        closed_positions = Position.query.filter_by(status='CLOSED').all()
        
        total_trades = len(trades)
        winning_trades = len([trade for trade in trades if (trade.realized_pnl or 0) > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(trade.realized_pnl or 0 for trade in trades)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@auth_bp.route('/api/auth/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        from models import db
        
        data = request.get_json()
        
        # Update user fields
        if 'display_name' in data:
            current_user.display_name = data['display_name']
        if 'email' in data:
            current_user.email = data['email']
        if 'timezone' in data:
            current_user.timezone = data['timezone']
        if 'language' in data:
            current_user.language = data['language']
        if 'currency' in data:
            current_user.currency = data['currency']
        
        # Update trading preferences (could be stored in user preferences table)
        current_user.preferences = current_user.preferences or {}
        if 'default_trade_amount' in data:
            current_user.preferences['default_trade_amount'] = data['default_trade_amount']
        if 'risk_level' in data:
            current_user.preferences['risk_level'] = data['risk_level']
        if 'enable_auto_trading' in data:
            current_user.preferences['enable_auto_trading'] = data['enable_auto_trading']
        if 'default_take_profit' in data:
            current_user.preferences['default_take_profit'] = data['default_take_profit']
        if 'default_stop_loss' in data:
            current_user.preferences['default_stop_loss'] = data['default_stop_loss']
        if 'enable_notifications' in data:
            current_user.preferences['enable_notifications'] = data['enable_notifications']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        from models import db
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@auth_bp.route('/api/auth/update-preference', methods=['POST'])
@login_required
def update_preference():
    """Update a single user preference"""
    try:
        from models import db
        
        data = request.get_json()
        current_user.preferences = current_user.preferences or {}
        
        # Update the specific preference
        for key, value in data.items():
            current_user.preferences[key] = value
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        from models import db
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@auth_bp.route('/api/auth/activity-log')
@login_required
def activity_log():
    """Get user activity log"""
    try:
        from models import SystemLog
        
        # Get recent user activities (could be improved with user-specific logging)
        activities = SystemLog.query.filter_by(
            category='USER'
        ).order_by(SystemLog.timestamp.desc()).limit(50).all()
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'timestamp': activity.timestamp.isoformat(),
                'action': activity.level,
                'details': activity.message,
                'ip_address': 'N/A'  # Would need to be stored separately
            })
        
        return jsonify({
            'success': True,
            'activities': activity_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@auth_bp.route('/api/auth/export-user-data')
@login_required
def export_user_data():
    """Export user's data"""
    try:
        import json
        from flask import make_response
        from models import Trade, Position, Order
        
        # Collect user data
        user_data = {
            'profile': {
                'username': current_user.username,
                'email': current_user.email,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'preferences': current_user.preferences
            },
            'trades': [
                {
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'quantity': trade.quantity,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'realized_pnl': trade.realized_pnl,
                    'entry_date': trade.entry_date.isoformat() if trade.entry_date else None,
                    'exit_date': trade.exit_date.isoformat() if trade.exit_date else None
                }
                for trade in Trade.query.filter_by(user_id=current_user.id).all()
            ],
            'positions': [
                {
                    'id': pos.id,
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'status': pos.status,
                    'created_at': pos.created_at.isoformat() if pos.created_at else None
                }
                for pos in Position.query.all()
            ]
        }
        
        response = make_response(json.dumps(user_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=user_data.json'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 