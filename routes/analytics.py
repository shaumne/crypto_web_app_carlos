from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from models import get_trading_performance

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
@login_required  
def index():
    """Analytics page"""
    return render_template('analytics/index.html')

@analytics_bp.route('/api/performance')
@login_required
def api_performance():
    """Get trading performance data"""
    try:
        days = request.args.get('days', 30, type=int)
        performance = get_trading_performance(days=days)
        
        return jsonify({
            'status': 'success',
            'data': performance
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500 