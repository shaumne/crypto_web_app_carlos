from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from models import Position, get_open_positions, get_trading_performance

positions_bp = Blueprint('positions', __name__, url_prefix='/positions')

@positions_bp.route('/')
@login_required
def index():
    """Positions page"""
    return render_template('positions/index.html')

@positions_bp.route('/api/positions')
@login_required
def api_positions():
    """Get positions with filters"""
    try:
        status_filter = request.args.get('status', None)
        
        query = Position.query
        if status_filter:
            query = query.filter_by(status=status_filter.upper())
        
        positions = query.order_by(Position.created_at.desc()).all()
        
        positions_data = []
        for position in positions:
            positions_data.append({
                'id': position.id,
                'symbol': position.symbol,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'market_value': position.market_value,
                'unrealized_pnl': position.unrealized_pnl,
                'pnl_percentage': position.pnl_percentage,
                'take_profit': position.take_profit,
                'stop_loss': position.stop_loss,
                'status': position.status,
                'order_type': position.order_type,
                'created_at': position.created_at.isoformat() if position.created_at else None,
                'updated_at': position.updated_at.isoformat() if position.updated_at else None,
                'closed_at': position.closed_at.isoformat() if position.closed_at else None
            })
        
        return jsonify({
            'success': True,
            'positions': positions_data
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@positions_bp.route('/api/positions/summary')
@login_required
def positions_summary():
    """Get positions summary statistics"""
    try:
        positions = Position.query.all()
        open_positions = Position.query.filter_by(status='OPEN').all()
        
        total_positions = len(positions)
        total_pnl = sum(pos.unrealized_pnl or 0 for pos in open_positions)
        portfolio_value = sum(pos.market_value or 0 for pos in open_positions)
        
        # Calculate win rate
        closed_positions = Position.query.filter_by(status='CLOSED').all()
        winning_positions = [pos for pos in closed_positions if (pos.unrealized_pnl or 0) > 0]
        win_rate = (len(winning_positions) / len(closed_positions) * 100) if closed_positions else 0
        
        return jsonify({
            'success': True,
            'total_positions': total_positions,
            'total_pnl': total_pnl,
            'portfolio_value': portfolio_value,
            'win_rate': win_rate
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@positions_bp.route('/api/positions/<int:position_id>/update-tp-sl', methods=['POST'])
@login_required
def update_tp_sl(position_id):
    """Update take profit and stop loss for a position"""
    try:
        from models import db
        
        position = Position.query.get_or_404(position_id)
        data = request.get_json()
        
        if 'take_profit' in data:
            position.take_profit = data['take_profit']
        if 'stop_loss' in data:
            position.stop_loss = data['stop_loss']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'TP/SL updated successfully'})
    except Exception as e:
        from models import db
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@positions_bp.route('/api/positions/export')
@login_required
def export_positions():
    """Export positions to CSV"""
    try:
        import csv
        import io
        from flask import make_response
        
        positions = Position.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Symbol', 'Quantity', 'Entry Price', 'Current Price', 
                        'Market Value', 'P&L', 'P&L %', 'Status', 'Created At'])
        
        # Write data
        for position in positions:
            writer.writerow([
                position.symbol,
                position.quantity,
                position.entry_price,
                position.current_price,
                position.market_value,
                position.unrealized_pnl,
                position.pnl_percentage,
                position.status,
                position.created_at
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=positions.csv'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 