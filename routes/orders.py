from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta
from models import db, Order, SystemLog
from services.crypto_exchange import CryptoExchangeAPI

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/')
@login_required
def index():
    """Orders management page"""
    return render_template('orders/index.html')

@orders_bp.route('/api/orders')
@login_required
def api_orders():
    """Get orders with pagination and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        coin_filter = request.args.get('coin')
        
        query = Order.query
        
        if status_filter:
            query = query.filter(Order.status == status_filter)
        
        if coin_filter:
            query = query.join(Order.coin_ref).filter(Order.coin_ref.has(symbol=coin_filter))
        
        orders = query.order_by(Order.created_at.desc())\
                     .paginate(page=page, per_page=per_page, error_out=False)
        
        orders_data = []
        for order in orders.items:
            orders_data.append({
                'id': order.id,
                'coin_symbol': order.coin_ref.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'quantity': order.quantity,
                'price': order.price,
                'filled_quantity': order.filled_quantity,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'exchange_order_id': order.exchange_order_id,
                'is_manual': order.is_manual
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'orders': orders_data,
                'pagination': {
                    'page': orders.page,
                    'pages': orders.pages,
                    'total': orders.total,
                    'per_page': orders.per_page
                }
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@orders_bp.route('/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order"""
    try:
        order = Order.query.get_or_404(order_id)
        
        if order.status not in ['PENDING', 'PARTIALLY_FILLED']:
            flash('Order cannot be cancelled.', 'error')
            return redirect(url_for('orders.index'))
        
        # Cancel on exchange
        exchange_api = CryptoExchangeAPI()
        success = exchange_api.cancel_order(order.exchange_order_id)
        
        if success:
            order.status = 'CANCELLED'
            order.cancelled_at = datetime.utcnow()
            db.session.commit()
            
            SystemLog.log(
                level='INFO',
                category='TRADING',
                message=f'Order cancelled: {order.exchange_order_id}',
                order_id=order.id
            )
            
            flash('Order cancelled successfully!', 'success')
        else:
            flash('Failed to cancel order on exchange.', 'error')
        
        return redirect(url_for('orders.index'))
        
    except Exception as e:
        flash(f'Error cancelling order: {str(e)}', 'error')
        return redirect(url_for('orders.index')) 