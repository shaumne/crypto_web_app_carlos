from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import (db, Coin, TechnicalAnalysis, Trade, Order, Position, 
                   SystemLog, get_active_coins, get_open_positions, 
                   get_pending_orders, get_trading_performance)
from services.technical_analysis import TechnicalAnalysisService
from services.crypto_exchange import CryptoExchangeAPI

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def dashboard():
    """Main dashboard page"""
    try:
        # Get overview statistics
        total_coins = Coin.query.filter_by(is_active=True).count()
        open_positions = get_open_positions()
        pending_orders = get_pending_orders()
        
        # Get recent trading performance (last 30 days)
        performance = get_trading_performance(days=30)
        
        # Get latest buy signals
        latest_signals = TechnicalAnalysis.query.filter_by(action='BUY')\
                                               .order_by(desc(TechnicalAnalysis.timestamp))\
                                               .limit(5).all()
        
        # Get recent system logs
        recent_logs = SystemLog.query.order_by(desc(SystemLog.timestamp))\
                                   .limit(10).all()
        
        # Calculate portfolio metrics
        total_portfolio_value = sum(pos.current_value for pos in open_positions if pos.current_value)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in open_positions if pos.unrealized_pnl)
        
        # Get account balance (if API is configured)
        account_balance = None
        try:
            exchange_api = CryptoExchangeAPI()
            if exchange_api.api_key and exchange_api.api_secret:
                balances = exchange_api.get_balance()
                if balances:
                    account_balance = balances
        except Exception as e:
            print(f"Error getting account balance: {e}")
        
        dashboard_data = {
            'total_coins': total_coins,
            'open_positions_count': len(open_positions),
            'pending_orders_count': len(pending_orders),
            'total_portfolio_value': total_portfolio_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'performance': performance,
            'latest_signals': latest_signals,
            'recent_logs': recent_logs,
            'account_balance': account_balance
        }
        
        return render_template('dashboard/index.html', **dashboard_data)
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template('dashboard/index.html', error=str(e))

@dashboard_bp.route('/api/overview')
@login_required
def api_overview():
    """API endpoint for dashboard overview data"""
    try:
        # Real-time statistics
        total_coins = Coin.query.filter_by(is_active=True).count()
        open_positions = get_open_positions()
        pending_orders = get_pending_orders()
        
        # Performance metrics
        performance = get_trading_performance(days=30)
        
        # Portfolio value
        total_portfolio_value = sum(pos.current_value for pos in open_positions if pos.current_value)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in open_positions if pos.unrealized_pnl)
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_coins': total_coins,
                'open_positions': len(open_positions),
                'pending_orders': len(pending_orders),
                'total_portfolio_value': round(total_portfolio_value, 2),
                'total_unrealized_pnl': round(total_unrealized_pnl, 2),
                'performance': {
                    'total_trades': performance['total_trades'],
                    'win_rate': round(performance['win_rate'], 2),
                    'total_pnl': round(performance['total_pnl'], 2)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/signals')
@login_required
def api_signals():
    """API endpoint for latest trading signals"""
    try:
        # Get latest analyses for all coins
        subquery = db.session.query(
            TechnicalAnalysis.coin_id,
            func.max(TechnicalAnalysis.timestamp).label('max_timestamp')
        ).group_by(TechnicalAnalysis.coin_id).subquery()
        
        latest_analyses = db.session.query(TechnicalAnalysis)\
            .join(subquery, 
                  (TechnicalAnalysis.coin_id == subquery.c.coin_id) & 
                  (TechnicalAnalysis.timestamp == subquery.c.max_timestamp))\
            .join(Coin, TechnicalAnalysis.coin_id == Coin.id)\
            .filter(Coin.is_active == True)\
            .order_by(desc(TechnicalAnalysis.timestamp))\
            .all()
        
        signals_data = []
        for analysis in latest_analyses:
            coin = analysis.coin_ref
            
            signals_data.append({
                'id': analysis.id,
                'coin_symbol': coin.symbol,
                'coin_name': coin.original_symbol,
                'last_price': analysis.last_price,
                'rsi': round(analysis.rsi, 2),
                'volume_ratio': round(analysis.volume_ratio, 2),
                'action': analysis.action,
                'signal_strength': analysis.signal_strength,
                'ma50_valid': analysis.ma50_valid,
                'ma200_valid': analysis.ma200_valid,
                'ema10_valid': analysis.ema10_valid,
                'take_profit': analysis.take_profit,
                'stop_loss': analysis.stop_loss,
                'risk_reward_ratio': round(analysis.risk_reward_ratio, 2) if analysis.risk_reward_ratio else 0,
                'timestamp': analysis.timestamp.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'data': signals_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/positions')
@login_required
def api_positions():
    """API endpoint for open positions"""
    try:
        open_positions = get_open_positions()
        
        positions_data = []
        for position in open_positions:
            coin = position.coin_ref
            
            positions_data.append({
                'id': position.id,
                'coin_symbol': coin.symbol,
                'coin_name': coin.original_symbol,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price or position.entry_price,
                'total_value': position.total_value,
                'current_value': position.current_value,
                'unrealized_pnl': position.unrealized_pnl,
                'pnl_percentage': round(position.pnl_percentage, 2),
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'entry_date': position.entry_date.isoformat(),
                'status': position.status
            })
        
        return jsonify({
            'status': 'success',
            'data': positions_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/orders')
@login_required
def api_orders():
    """API endpoint for pending orders"""
    try:
        pending_orders = get_pending_orders()
        
        orders_data = []
        for order in pending_orders:
            coin = order.coin_ref
            
            orders_data.append({
                'id': order.id,
                'coin_symbol': coin.symbol,
                'coin_name': coin.original_symbol,
                'order_type': order.order_type,
                'side': order.side,
                'quantity': order.quantity,
                'price': order.price,
                'filled_quantity': order.filled_quantity,
                'remaining_quantity': order.remaining_quantity,
                'fill_percentage': round(order.fill_percentage, 2),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'exchange_order_id': order.exchange_order_id
            })
        
        return jsonify({
            'status': 'success',
            'data': orders_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/performance')
@login_required
def api_performance():
    """API endpoint for trading performance metrics"""
    try:
        # Get performance for different time periods
        performance_7d = get_trading_performance(days=7)
        performance_30d = get_trading_performance(days=30)
        performance_90d = get_trading_performance(days=90)
        
        # Get daily PnL for chart (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        daily_pnl = db.session.query(
            func.date(Position.exit_date).label('date'),
            func.sum(Position.realized_pnl).label('daily_pnl')
        ).filter(
            Position.status == 'closed',
            Position.exit_date >= start_date,
            Position.exit_date <= end_date
        ).group_by(func.date(Position.exit_date)).all()
        
        # Format daily PnL for chart
        pnl_chart_data = []
        for record in daily_pnl:
            pnl_chart_data.append({
                'date': record.date.isoformat(),
                'pnl': float(record.daily_pnl or 0)
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'performance_7d': performance_7d,
                'performance_30d': performance_30d,
                'performance_90d': performance_90d,
                'daily_pnl_chart': pnl_chart_data
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/account-balance')
@login_required
def api_account_balance():
    """API endpoint for account balance from exchange"""
    try:
        exchange_api = CryptoExchangeAPI()
        
        if not exchange_api.api_key or not exchange_api.api_secret:
            return jsonify({
                'status': 'error',
                'message': 'Exchange API credentials not configured'
            }), 400
        
        # Test connection first
        if not exchange_api.test_connection():
            return jsonify({
                'status': 'error',
                'message': 'Failed to connect to exchange API'
            }), 500
        
        # Get account balance
        balances = exchange_api.get_balance()
        
        # Filter out zero balances and format
        formatted_balances = []
        for balance in balances:
            available = float(balance.get('available', 0))
            balance_amount = float(balance.get('balance', 0))
            
            if balance_amount > 0:
                formatted_balances.append({
                    'currency': balance.get('currency'),
                    'balance': balance_amount,
                    'available': available,
                    'in_orders': balance_amount - available
                })
        
        return jsonify({
            'status': 'success',
            'data': formatted_balances
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/api/system-logs')
@login_required
def api_system_logs():
    """API endpoint for recent system logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        level_filter = request.args.get('level', None)
        category_filter = request.args.get('category', None)
        
        query = SystemLog.query
        
        if level_filter:
            query = query.filter(SystemLog.level == level_filter.upper())
        
        if category_filter:
            query = query.filter(SystemLog.category == category_filter.upper())
        
        logs = query.order_by(desc(SystemLog.timestamp))\
                   .paginate(page=page, per_page=per_page, error_out=False)
        
        logs_data = []
        for log in logs.items:
            logs_data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'category': log.category,
                'message': log.message,
                'details': log.details,
                'coin_id': log.coin_id,
                'trade_id': log.trade_id,
                'order_id': log.order_id,
                'position_id': log.position_id
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': logs_data,
                'pagination': {
                    'page': logs.page,
                    'pages': logs.pages,
                    'total': logs.total,
                    'per_page': logs.per_page,
                    'has_prev': logs.has_prev,
                    'has_next': logs.has_next
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/signals')
@login_required
def signals():
    """Trading signals page"""
    return render_template('dashboard/signals.html')

@dashboard_bp.route('/positions')
@login_required
def positions():
    """Positions page"""
    return render_template('dashboard/positions.html')

@dashboard_bp.route('/orders')
@login_required
def orders():
    """Orders page"""
    return render_template('dashboard/orders.html')

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """Analytics page"""
    return render_template('dashboard/analytics.html')

@dashboard_bp.route('/logs')
@login_required
def logs():
    """System logs page"""
    return render_template('dashboard/logs.html') 