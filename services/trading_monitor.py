import time
import logging
import threading
from datetime import datetime, timedelta
from services.technical_analysis import TechnicalAnalysisService
from services.crypto_exchange import CryptoExchangeAPI
from models import db, Coin, TechnicalAnalysis, Order, Position, SystemLog, get_active_coins

logger = logging.getLogger(__name__)

class TradingMonitor:
    """Trading Monitor Service - Continuously analyzes coins and generates trading signals"""
    
    def __init__(self, analysis_interval: int = 30):
        self.analysis_interval = analysis_interval  # seconds
        self.running = False
        self.analysis_service = TechnicalAnalysisService()
        self.exchange_api = CryptoExchangeAPI()
        
        logger.info(f"Trading Monitor initialized with {analysis_interval}s interval")
    
    def start(self):
        """Start the trading monitor"""
        if self.running:
            logger.warning("Trading monitor is already running")
            return
        
        self.running = True
        logger.info("Starting Trading Monitor")
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=self.run, daemon=True)
        monitor_thread.start()
    
    def stop(self):
        """Stop the trading monitor"""
        self.running = False
        logger.info("Trading Monitor stopped")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Trading Monitor started")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Get active coins
                active_coins = get_active_coins()
                if not active_coins:
                    logger.info("No active coins to analyze")
                    time.sleep(self.analysis_interval)
                    continue
                
                logger.info(f"Analyzing {len(active_coins)} coins...")
                
                # Analyze each coin
                for coin in active_coins:
                    if not self.running:
                        break
                        
                    try:
                        self.analyze_coin(coin)
                        time.sleep(1)  # Small delay between analyses
                    except Exception as e:
                        logger.error(f"Error analyzing {coin.symbol}: {str(e)}")
                        continue
                
                # Check for completed orders and update positions
                self.check_order_updates()
                
                # Update open position prices
                self.update_position_prices()
                
                # Log completion
                elapsed = time.time() - start_time
                logger.info(f"Analysis cycle completed in {elapsed:.2f}s")
                
                # Sleep until next interval
                sleep_time = max(0, self.analysis_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in trading monitor loop: {str(e)}")
                time.sleep(10)  # Wait before retrying
    
    def analyze_coin(self, coin: Coin):
        """Analyze a single coin and update database"""
        try:
            # Get latest analysis
            analysis_data = self.analysis_service.analyze_coin(coin)
            if not analysis_data:
                return
            
            # Save analysis
            analysis = self.analysis_service.save_analysis(analysis_data)
            if not analysis:
                return
            
            # Check if this is a buy signal and no open position exists
            if analysis.action == 'BUY':
                self.handle_buy_signal(coin, analysis)
            
            logger.debug(f"Analysis saved for {coin.symbol}: {analysis.action}")
            
        except Exception as e:
            logger.error(f"Error analyzing coin {coin.symbol}: {str(e)}")
    
    def handle_buy_signal(self, coin: Coin, analysis: TechnicalAnalysis):
        """Handle buy signal by checking for existing positions and potentially placing orders"""
        try:
            # Check if coin already has open positions
            open_positions = Position.query.filter_by(coin_id=coin.id, status='open').all()
            if open_positions:
                logger.info(f"Skipping buy signal for {coin.symbol} - open position exists")
                return
            
            # Check if there are pending buy orders
            pending_orders = Order.query.filter_by(
                coin_id=coin.id,
                side='BUY',
                status='PENDING'
            ).all()
            
            if pending_orders:
                logger.info(f"Skipping buy signal for {coin.symbol} - pending buy order exists")
                return
            
            # Log the buy signal
            SystemLog.log(
                level='INFO',
                category='TRADING',
                message=f"Buy signal detected for {coin.symbol} - RSI: {analysis.rsi:.2f}, Price: {analysis.last_price}",
                details={
                    'rsi': analysis.rsi,
                    'price': analysis.last_price,
                    'volume_ratio': analysis.volume_ratio,
                    'signal_strength': analysis.signal_strength
                },
                coin_id=coin.id
            )
            
            # In a real implementation, you might:
            # 1. Check account balance
            # 2. Calculate position size
            # 3. Place buy order
            # For now, we just log the signal
            
        except Exception as e:
            logger.error(f"Error handling buy signal for {coin.symbol}: {str(e)}")
    
    def check_order_updates(self):
        """Check for order updates from the exchange"""
        try:
            # Get pending orders
            pending_orders = Order.query.filter(
                Order.status.in_(['PENDING', 'PARTIALLY_FILLED'])
            ).all()
            
            if not pending_orders:
                return
            
            logger.debug(f"Checking {len(pending_orders)} pending orders")
            
            for order in pending_orders:
                try:
                    self.update_order_status(order)
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error updating order {order.id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking order updates: {str(e)}")
    
    def update_order_status(self, order: Order):
        """Update order status from exchange"""
        try:
            if not order.exchange_order_id:
                return
            
            # Get order status from exchange
            order_status = self.exchange_api.get_order_status(order.exchange_order_id)
            if not order_status:
                return
            
            # Update order based on exchange status
            exchange_status = order_status.get('status', '').upper()
            
            if exchange_status in ['FILLED', 'ACTIVE']:
                # Order is filled or partially filled
                filled_quantity = float(order_status.get('cumulative_quantity', 0))
                avg_price = float(order_status.get('avg_price', 0))
                
                if filled_quantity > order.filled_quantity:
                    # Update order
                    order.filled_quantity = filled_quantity
                    order.average_fill_price = avg_price
                    
                    if filled_quantity >= order.quantity:
                        order.status = 'FILLED'
                        order.filled_at = datetime.utcnow()
                        
                        # Create position if it's a buy order
                        if order.side == 'BUY':
                            self.create_position_from_order(order)
                            
                    else:
                        order.status = 'PARTIALLY_FILLED'
                    
                    db.session.commit()
                    
                    SystemLog.log(
                        level='INFO',
                        category='TRADING',
                        message=f"Order updated: {order.side} {filled_quantity} {order.coin_ref.symbol}",
                        order_id=order.id
                    )
            
            elif exchange_status in ['CANCELLED', 'REJECTED']:
                order.status = exchange_status
                if exchange_status == 'CANCELLED':
                    order.cancelled_at = datetime.utcnow()
                db.session.commit()
                
                SystemLog.log(
                    level='INFO',
                    category='TRADING',
                    message=f"Order {exchange_status.lower()}: {order.exchange_order_id}",
                    order_id=order.id
                )
                
        except Exception as e:
            logger.error(f"Error updating order status for {order.id}: {str(e)}")
    
    def create_position_from_order(self, order: Order):
        """Create position from filled buy order"""
        try:
            # Check if position already exists
            existing_position = Position.query.filter_by(
                coin_id=order.coin_id,
                entry_order_id=order.id
            ).first()
            
            if existing_position:
                return existing_position
            
            # Get latest analysis for TP/SL levels
            latest_analysis = TechnicalAnalysis.query.filter_by(coin_id=order.coin_id)\
                                                   .order_by(TechnicalAnalysis.timestamp.desc())\
                                                   .first()
            
            # Create new position
            position = Position(
                coin_id=order.coin_id,
                quantity=order.filled_quantity,
                entry_price=order.average_fill_price,
                current_price=order.average_fill_price,
                entry_order_id=order.id,
                status='open'
            )
            
            # Set TP/SL from latest analysis if available
            if latest_analysis:
                position.take_profit = latest_analysis.take_profit
                position.stop_loss = latest_analysis.stop_loss
            
            db.session.add(position)
            db.session.commit()
            
            SystemLog.log(
                level='INFO',
                category='TRADING',
                message=f"Position created: {position.quantity} {order.coin_ref.symbol} at {position.entry_price}",
                position_id=position.id,
                coin_id=order.coin_id
            )
            
            return position
            
        except Exception as e:
            logger.error(f"Error creating position from order {order.id}: {str(e)}")
            return None
    
    def update_position_prices(self):
        """Update current prices for open positions"""
        try:
            open_positions = Position.query.filter_by(status='open').all()
            if not open_positions:
                return
            
            logger.debug(f"Updating prices for {len(open_positions)} positions")
            
            for position in open_positions:
                try:
                    self.update_position_price(position)
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error updating position {position.id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error updating position prices: {str(e)}")
    
    def update_position_price(self, position: Position):
        """Update current price for a position"""
        try:
            coin = position.coin_ref
            
            # Get current price from exchange
            ticker = self.exchange_api.get_ticker(coin.symbol)
            if not ticker:
                return
            
            current_price = float(ticker.get('a', 0))  # Ask price
            if current_price <= 0:
                return
            
            # Update position
            position.current_price = current_price
            position.update_unrealized_pnl()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating price for position {position.id}: {str(e)}")
    
    def get_status(self):
        """Get monitor status"""
        return {
            'running': self.running,
            'analysis_interval': self.analysis_interval,
            'last_run': datetime.utcnow().isoformat() if self.running else None
        } 