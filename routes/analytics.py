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

# Additional API endpoints for comprehensive analytics
@analytics_bp.route('/api/analytics/performance')
@login_required
def performance_analytics():
    """Get detailed performance analytics"""
    try:
        days = request.args.get('days', '30')
        
        # Mock performance data - would normally calculate from database
        performance_data = {
            'total_pnl': 250.75,
            'pnl_change': 12.5,
            'win_rate': 68.5,
            'winning_trades': 27,
            'total_trades': 40,
            'avg_trade_size': 15.25,
            'sharpe_ratio': 1.45,
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'cumulative_pnl': [100, 150, 250.75],
            'portfolio_values': [1000, 1100, 1250.75],
            'daily_volume': [500, 750, 650]
        }
        
        return jsonify({'success': True, **performance_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/api/analytics/allocation')
@login_required
def portfolio_allocation():
    """Get portfolio allocation data"""
    try:
        # Mock allocation data
        allocation_data = {
            'symbols': ['BTC', 'ETH', 'ADA', 'SOL'],
            'values': [40, 30, 20, 10]
        }
        
        return jsonify({'success': True, **allocation_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/api/analytics/trade-analysis')
@login_required
def trade_analysis():
    """Get trade analysis data"""
    try:
        days = request.args.get('days', '30')
        
        # Mock trade analysis data
        analysis_data = {
            'total_return': 275.50,
            'total_return_percent': 27.55,
            'annualized_return': 45.2,
            'max_drawdown': -8.5,
            'volatility': 15.2,
            'sharpe_ratio': 1.45,
            'total_trades': 40,
            'winning_trades': 27,
            'losing_trades': 13,
            'avg_win': 25.50,
            'avg_loss': -12.25,
            'profit_factor': 2.08,
            'monthly_labels': ['Jan', 'Feb', 'Mar'],
            'monthly_pnl': [85, 95, 95.75],
            'top_assets': [
                {'symbol': 'BTC', 'trades': 15, 'win_rate': 73.3, 'total_pnl': 150.25, 'avg_pnl': 10.02},
                {'symbol': 'ETH', 'trades': 12, 'win_rate': 66.7, 'total_pnl': 85.50, 'avg_pnl': 7.13},
                {'symbol': 'ADA', 'trades': 8, 'win_rate': 62.5, 'total_pnl': 32.00, 'avg_pnl': 4.00},
                {'symbol': 'SOL', 'trades': 5, 'win_rate': 60.0, 'total_pnl': 7.75, 'avg_pnl': 1.55}
            ]
        }
        
        return jsonify({'success': True, **analysis_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/api/analytics/signal-performance')
@login_required
def signal_performance():
    """Get signal performance data"""
    try:
        days = request.args.get('days', '30')
        
        # Mock signal performance data
        signal_data = {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'accuracy_over_time': [65, 68, 72],
            'signal_distribution': [12, 15, 8, 3, 2],  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
            'signal_performance': [
                {'type': 'STRONG_BUY', 'total_signals': 12, 'executed': 10, 'success_rate': 80.0, 'avg_return': 8.5},
                {'type': 'BUY', 'total_signals': 15, 'executed': 12, 'success_rate': 75.0, 'avg_return': 5.2},
                {'type': 'SELL', 'total_signals': 3, 'executed': 3, 'success_rate': 66.7, 'avg_return': -2.1},
                {'type': 'STRONG_SELL', 'total_signals': 2, 'executed': 2, 'success_rate': 50.0, 'avg_return': -5.5}
            ]
        }
        
        return jsonify({'success': True, **signal_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/api/analytics/risk-metrics')
@login_required
def risk_metrics():
    """Get risk analysis data"""
    try:
        days = request.args.get('days', '30')
        
        # Mock risk metrics data
        risk_data = {
            'portfolio_beta': 1.15,
            'value_at_risk': -45.50,
            'expected_shortfall': -65.25,
            'max_consecutive_losses': 3,
            'current_drawdown': -2.5,
            'recovery_factor': 3.25,
            'position_size_vs_pnl': [
                {'x': 10, 'y': 5.5},
                {'x': 15, 'y': 8.2},
                {'x': 20, 'y': -3.1},
                {'x': 25, 'y': 12.0}
            ],
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'drawdown_series': [0, -2.1, -1.5]
        }
        
        return jsonify({'success': True, **risk_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/api/analytics/export')
@login_required
def export_analytics():
    """Export analytics report"""
    try:
        days = request.args.get('days', '30')
        
        from flask import make_response
        import json
        
        # Mock export data
        export_data = {
            'report_date': '2024-01-03',
            'period_days': int(days),
            'performance_summary': {
                'total_return': 275.50,
                'win_rate': 68.5,
                'total_trades': 40,
                'sharpe_ratio': 1.45
            },
            'detailed_trades': [],  # Would include all trade data
            'risk_metrics': {
                'max_drawdown': -8.5,
                'volatility': 15.2
            }
        }
        
        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=analytics_report_{days}days.json'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 