from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Coin, TechnicalAnalysis, Order, Position, SystemLog
from services.crypto_exchange import CryptoExchangeAPI
from services.technical_analysis import TechnicalAnalysisService

trading_bp = Blueprint('trading', __name__, url_prefix='/trading')

@trading_bp.route('/')
@login_required
def index():
    """Trading management page"""
    coins = Coin.query.filter_by(is_active=True).all()
    return render_template('trading/index.html', coins=coins)

@trading_bp.route('/coins')
@login_required
def coins():
    """Coin management page"""
    active_coins = Coin.query.filter_by(is_active=True).all()
    inactive_coins = Coin.query.filter_by(is_active=False).all()
    
    return render_template('trading/coins.html', 
                         active_coins=active_coins, 
                         inactive_coins=inactive_coins)

@trading_bp.route('/add-coin', methods=['POST'])
@login_required
def add_coin():
    """Add a new coin for tracking"""
    try:
        symbol = request.form.get('symbol', '').strip().upper()
        original_symbol = request.form.get('original_symbol', '').strip().upper()
        base_currency = request.form.get('base_currency', 'USDT').strip().upper()
        
        if not symbol or not original_symbol:
            flash('Symbol and original symbol are required.', 'error')
            return redirect(url_for('trading.coins'))
        
        # Check if coin already exists
        existing_coin = Coin.query.filter_by(symbol=symbol).first()
        if existing_coin:
            flash(f'Coin {symbol} already exists.', 'warning')
            return redirect(url_for('trading.coins'))
        
        # Validate symbol format
        if '_' not in symbol:
            symbol = f"{original_symbol}_{base_currency}"
        
        # Test if the symbol exists on the exchange
        exchange_api = CryptoExchangeAPI()
        ticker = exchange_api.get_ticker(symbol)
        
        if not ticker:
            flash(f'Symbol {symbol} not found on exchange.', 'error')
            return redirect(url_for('trading.coins'))
        
        # Create new coin
        new_coin = Coin(
            symbol=symbol,
            original_symbol=original_symbol,
            base_currency=base_currency,
            is_active=True,
            is_trading_enabled=True
        )
        
        db.session.add(new_coin)
        db.session.commit()
        
        SystemLog.log(
            level='INFO',
            category='TRADING',
            message=f'New coin added: {symbol}',
            coin_id=new_coin.id
        )
        
        flash(f'Coin {symbol} added successfully!', 'success')
        return redirect(url_for('trading.coins'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding coin: {str(e)}', 'error')
        return redirect(url_for('trading.coins'))

@trading_bp.route('/toggle-coin/<int:coin_id>', methods=['POST'])
@login_required
def toggle_coin(coin_id):
    """Toggle coin active status"""
    try:
        coin = Coin.query.get_or_404(coin_id)
        coin.is_active = not coin.is_active
        db.session.commit()
        
        status = 'activated' if coin.is_active else 'deactivated'
        SystemLog.log(
            level='INFO',
            category='TRADING',
            message=f'Coin {coin.symbol} {status}',
            coin_id=coin.id
        )
        
        flash(f'Coin {coin.symbol} {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating coin: {str(e)}', 'error')
    
    return redirect(url_for('trading.coins'))

@trading_bp.route('/toggle-trading/<int:coin_id>', methods=['POST'])
@login_required
def toggle_trading(coin_id):
    """Toggle coin trading enabled status"""
    try:
        coin = Coin.query.get_or_404(coin_id)
        coin.is_trading_enabled = not coin.is_trading_enabled
        db.session.commit()
        
        status = 'enabled' if coin.is_trading_enabled else 'disabled'
        SystemLog.log(
            level='INFO',
            category='TRADING',
            message=f'Trading {status} for {coin.symbol}',
            coin_id=coin.id
        )
        
        flash(f'Trading {status} for {coin.symbol}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating trading status: {str(e)}', 'error')
    
    return redirect(url_for('trading.coins'))

@trading_bp.route('/manual-order', methods=['GET', 'POST'])
@login_required
def manual_order():
    """Place manual order"""
    if request.method == 'GET':
        coins = Coin.query.filter_by(is_active=True, is_trading_enabled=True).all()
        return render_template('trading/manual_order.html', coins=coins)
    
    try:
        coin_id = request.form.get('coin_id', type=int)
        side = request.form.get('side')  # BUY or SELL
        order_type = request.form.get('order_type')  # MARKET or LIMIT
        quantity = request.form.get('quantity', type=float)
        price = request.form.get('price', type=float) if order_type == 'LIMIT' else None
        
        if not all([coin_id, side, order_type, quantity]):
            flash('All fields are required.', 'error')
            return redirect(url_for('trading.manual_order'))
        
        coin = Coin.query.get_or_404(coin_id)
        
        # Validate order
        if quantity <= 0:
            flash('Quantity must be positive.', 'error')
            return redirect(url_for('trading.manual_order'))
        
        if order_type == 'LIMIT' and (not price or price <= 0):
            flash('Price is required for limit orders.', 'error')
            return redirect(url_for('trading.manual_order'))
        
        # Place order through exchange API
        exchange_api = CryptoExchangeAPI()
        
        order_result = exchange_api.place_order(
            instrument_name=coin.symbol,
            side=side,
            type_=order_type,
            quantity=quantity,
            price=price
        )
        
        if not order_result:
            flash('Failed to place order on exchange.', 'error')
            return redirect(url_for('trading.manual_order'))
        
        # Create order record
        new_order = Order(
            coin_id=coin.id,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            status='PENDING',
            exchange_order_id=order_result.get('order_id'),
            client_order_id=order_result.get('client_oid'),
            is_manual=True
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        SystemLog.log(
            level='INFO',
            category='TRADING',
            message=f'Manual order placed: {side} {quantity} {coin.symbol}',
            coin_id=coin.id,
            order_id=new_order.id
        )
        
        flash(f'Order placed successfully! Order ID: {order_result.get("order_id")}', 'success')
        return redirect(url_for('dashboard.orders'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error placing order: {str(e)}', 'error')
        return redirect(url_for('trading.manual_order'))

@trading_bp.route('/api/coin-price/<int:coin_id>')
@login_required
def api_coin_price(coin_id):
    """Get current price for a coin"""
    try:
        coin = Coin.query.get_or_404(coin_id)
        
        exchange_api = CryptoExchangeAPI()
        ticker = exchange_api.get_ticker(coin.symbol)
        
        if not ticker:
            return jsonify({
                'status': 'error',
                'message': 'Failed to get price data'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': {
                'symbol': coin.symbol,
                'price': float(ticker.get('a', 0)),  # Ask price
                'bid': float(ticker.get('b', 0)),   # Bid price
                'high_24h': float(ticker.get('h', 0)),
                'low_24h': float(ticker.get('l', 0)),
                'volume_24h': float(ticker.get('v', 0)),
                'change_24h': float(ticker.get('c', 0))
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading_bp.route('/api/analyze-coin/<int:coin_id>')
@login_required
def api_analyze_coin(coin_id):
    """Trigger analysis for a specific coin"""
    try:
        coin = Coin.query.get_or_404(coin_id)
        
        analysis_service = TechnicalAnalysisService()
        analysis_data = analysis_service.analyze_coin(coin)
        
        if not analysis_data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to analyze coin'
            }), 500
        
        # Save analysis
        analysis = analysis_service.save_analysis(analysis_data)
        
        if not analysis:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save analysis'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': {
                'coin_symbol': coin.symbol,
                'last_price': analysis.last_price,
                'rsi': analysis.rsi,
                'action': analysis.action,
                'signal_strength': analysis_service.get_signal_strength(analysis),
                'timestamp': analysis.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading_bp.route('/api/available-instruments')
@login_required
def api_available_instruments():
    """Get available trading instruments from exchange"""
    try:
        exchange_api = CryptoExchangeAPI()
        instruments = exchange_api.get_instruments()
        
        # Filter and format instruments
        formatted_instruments = []
        for instrument in instruments:
            if instrument.get('tradable'):
                formatted_instruments.append({
                    'symbol': instrument.get('instrument_name'),
                    'base_currency': instrument.get('base_currency'),
                    'quote_currency': instrument.get('quote_currency'),
                    'min_quantity': float(instrument.get('min_quantity', 0)),
                    'price_decimals': int(instrument.get('price_decimals', 2)),
                    'quantity_decimals': int(instrument.get('quantity_decimals', 6))
                })
        
        # Sort by symbol
        formatted_instruments.sort(key=lambda x: x['symbol'])
        
        return jsonify({
            'status': 'success',
            'data': formatted_instruments
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading_bp.route('/bulk-analyze', methods=['POST'])
@login_required
def bulk_analyze():
    """Trigger analysis for all active coins"""
    try:
        analysis_service = TechnicalAnalysisService()
        results = analysis_service.analyze_all_coins()
        
        SystemLog.log(
            level='INFO',
            category='ANALYSIS',
            message=f'Bulk analysis completed for {len(results)} coins'
        )
        
        flash(f'Analysis completed for {len(results)} coins!', 'success')
        
    except Exception as e:
        flash(f'Error during bulk analysis: {str(e)}', 'error')
    
    return redirect(url_for('trading.index'))

@trading_bp.route('/import-popular-coins', methods=['POST'])
@login_required
def import_popular_coins():
    """Import popular cryptocurrency pairs"""
    try:
        # Popular crypto pairs to add
        popular_pairs = [
            {'symbol': 'BTC_USDT', 'original': 'BTC'},
            {'symbol': 'ETH_USDT', 'original': 'ETH'},
            {'symbol': 'BNB_USDT', 'original': 'BNB'},
            {'symbol': 'ADA_USDT', 'original': 'ADA'},
            {'symbol': 'SOL_USDT', 'original': 'SOL'},
            {'symbol': 'XRP_USDT', 'original': 'XRP'},
            {'symbol': 'DOT_USDT', 'original': 'DOT'},
            {'symbol': 'DOGE_USDT', 'original': 'DOGE'},
            {'symbol': 'AVAX_USDT', 'original': 'AVAX'},
            {'symbol': 'MATIC_USDT', 'original': 'MATIC'}
        ]
        
        exchange_api = CryptoExchangeAPI()
        added_count = 0
        
        for pair in popular_pairs:
            # Check if coin already exists
            existing_coin = Coin.query.filter_by(symbol=pair['symbol']).first()
            if existing_coin:
                continue
            
            # Verify the pair exists on exchange
            ticker = exchange_api.get_ticker(pair['symbol'])
            if not ticker:
                continue
            
            # Add the coin
            new_coin = Coin(
                symbol=pair['symbol'],
                original_symbol=pair['original'],
                base_currency='USDT',
                is_active=True,
                is_trading_enabled=True
            )
            
            db.session.add(new_coin)
            added_count += 1
        
        db.session.commit()
        
        SystemLog.log(
            level='INFO',
            category='TRADING',
            message=f'Imported {added_count} popular coins'
        )
        
        flash(f'Successfully imported {added_count} popular coins!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing coins: {str(e)}', 'error')
    
    return redirect(url_for('trading.coins'))

# API Endpoints for frontend
@trading_bp.route('/api/trading/stats')
@login_required  
def trading_stats():
    """Get trading statistics"""
    try:
        total_coins = Coin.query.count()
        active_signals = TechnicalAnalysis.query.filter(
            TechnicalAnalysis.signal.in_(['BUY', 'STRONG_BUY'])
        ).count()
        pending_orders = Order.query.filter_by(status='PENDING').count()
        
        # Calculate portfolio value
        positions = Position.query.filter_by(status='OPEN').all()
        portfolio_value = sum(pos.market_value or 0 for pos in positions)
        
        return jsonify({
            'success': True,
            'total_coins': total_coins,
            'active_signals': active_signals,
            'pending_orders': pending_orders,
            'portfolio_value': portfolio_value
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@trading_bp.route('/api/trading/coins')
@login_required
def get_coins_api():
    """Get all coins with their analysis data"""
    try:
        coins = Coin.query.all()
        
        coins_data = []
        for coin in coins:
            # Get latest analysis
            latest_analysis = TechnicalAnalysis.query.filter_by(
                symbol=coin.symbol
            ).order_by(TechnicalAnalysis.timestamp.desc()).first()
            
            coin_data = {
                'symbol': coin.symbol,
                'name': coin.name,
                'is_active': coin.is_active,
                'current_price': coin.current_price,
                'price_change_24h': coin.price_change_24h,
                'market_cap': coin.market_cap,
                'volume_24h': coin.volume_24h,
                'rsi': latest_analysis.rsi if latest_analysis else None,
                'signal': latest_analysis.signal if latest_analysis else 'HOLD'
            }
            coins_data.append(coin_data)
        
        return jsonify({'success': True, 'coins': coins_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@trading_bp.route('/api/trading/coins', methods=['POST'])
@login_required
def add_coin_api():
    """Add a new coin via API"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        name = data.get('name', '').strip()
        is_active = data.get('is_active', True)
        
        if not symbol:
            return jsonify({'success': False, 'message': 'Symbol is required'})
        
        # Check if coin already exists
        existing_coin = Coin.query.filter_by(symbol=symbol).first()
        if existing_coin:
            return jsonify({'success': False, 'message': f'Coin {symbol} already exists'})
        
        # Create new coin
        new_coin = Coin(
            symbol=symbol,
            name=name,
            is_active=is_active
        )
        
        db.session.add(new_coin)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Coin {symbol} added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@trading_bp.route('/api/trading/import-popular', methods=['POST'])
@login_required
def import_popular_api():
    """Import popular coins via API"""
    try:
        popular_pairs = [
            {'symbol': 'BTC_USDT', 'name': 'Bitcoin'},
            {'symbol': 'ETH_USDT', 'name': 'Ethereum'},
            {'symbol': 'BNB_USDT', 'name': 'Binance Coin'},
            {'symbol': 'ADA_USDT', 'name': 'Cardano'},
            {'symbol': 'SOL_USDT', 'name': 'Solana'},
            {'symbol': 'XRP_USDT', 'name': 'Ripple'},
            {'symbol': 'DOT_USDT', 'name': 'Polkadot'},
            {'symbol': 'DOGE_USDT', 'name': 'Dogecoin'},
            {'symbol': 'AVAX_USDT', 'name': 'Avalanche'},
            {'symbol': 'MATIC_USDT', 'name': 'Polygon'}
        ]
        
        added_count = 0
        for pair in popular_pairs:
            existing_coin = Coin.query.filter_by(symbol=pair['symbol']).first()
            if existing_coin:
                continue
            
            new_coin = Coin(
                symbol=pair['symbol'],
                name=pair['name'],
                is_active=True
            )
            
            db.session.add(new_coin)
            added_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'imported': added_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@trading_bp.route('/api/trading/analyze-all', methods=['POST'])
@login_required
def analyze_all_api():
    """Analyze all active coins"""
    try:
        ta_service = TechnicalAnalysisService()
        active_coins = Coin.query.filter_by(is_active=True).all()
        
        analyzed_count = 0
        for coin in active_coins:
            try:
                ta_service.analyze_coin(coin.symbol)
                analyzed_count += 1
            except:
                continue
        
        return jsonify({'success': True, 'analyzed': analyzed_count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 