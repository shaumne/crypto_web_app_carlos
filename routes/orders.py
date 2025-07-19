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
    """Get orders with filters"""
    try:
        status_filter = request.args.get('status')
        coin_filter = request.args.get('symbol')
        
        query = Order.query
        
        if status_filter:
            query = query.filter(Order.status == status_filter.upper())
        
        if coin_filter:
            query = query.filter(Order.symbol == coin_filter.upper())
        
        orders = query.order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'id': order.id,
                'order_id': order.order_id,
                'symbol': order.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'quantity': order.quantity,
                'price': order.price,
                'filled_quantity': order.filled_quantity,
                'total_value': order.total_value,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                'cancelled_at': order.cancelled_at.isoformat() if order.cancelled_at else None,
                'take_profit': order.take_profit,
                'stop_loss': order.stop_loss
            })
        
        return jsonify({
            'success': True,
            'orders': orders_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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

# API Endpoints
@orders_bp.route('/api/orders/summary')
@login_required
def orders_summary():
    """Get orders summary statistics"""
    try:
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='PENDING').count()
        filled_orders = Order.query.filter_by(status='FILLED').count()
        
        # Calculate total volume
        filled_order_list = Order.query.filter_by(status='FILLED').all()
        total_volume = sum(order.total_value or 0 for order in filled_order_list)
        
        return jsonify({
            'success': True,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'filled_orders': filled_orders,
            'total_volume': total_volume
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@orders_bp.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order_api(order_id):
    """Cancel an order via API"""
    try:
        order = Order.query.get_or_404(order_id)
        
        if order.status != 'PENDING':
            return jsonify({'success': False, 'message': 'Order cannot be cancelled'})
        
        # Try to cancel on exchange
        exchange_api = CryptoExchangeAPI()
        success = exchange_api.cancel_order(order.exchange_order_id)
        
        if success:
            order.status = 'CANCELLED'
            order.cancelled_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Order cancelled successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to cancel order on exchange'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@orders_bp.route('/api/orders/cancel-all-pending', methods=['POST'])
@login_required
def cancel_all_pending_api():
    """Cancel all pending orders"""
    try:
        pending_orders = Order.query.filter_by(status='PENDING').all()
        exchange_api = CryptoExchangeAPI()
        
        cancelled_count = 0
        for order in pending_orders:
            try:
                success = exchange_api.cancel_order(order.exchange_order_id)
                if success:
                    order.status = 'CANCELLED'
                    order.cancelled_at = datetime.utcnow()
                    cancelled_count += 1
            except:
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cancelled_count': cancelled_count,
            'message': f'Cancelled {cancelled_count} orders'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@orders_bp.route('/api/orders/export')
@login_required
def export_orders():
    """Export orders to CSV"""
    try:
        import csv
        import io
        from flask import make_response
        
        orders = Order.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Order ID', 'Symbol', 'Side', 'Type', 'Quantity', 'Price', 
                        'Filled Quantity', 'Total Value', 'Status', 'Created At'])
        
        # Write data
        for order in orders:
            writer.writerow([
                order.order_id or order.id,
                order.symbol,
                order.side,
                order.order_type,
                order.quantity,
                order.price,
                order.filled_quantity,
                order.total_value,
                order.status,
                order.created_at
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=orders.csv'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 