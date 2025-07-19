import time
import logging
import threading
from datetime import datetime
from services.crypto_exchange import CryptoExchangeAPI
from models import db, Position, Order, SystemLog, get_open_positions

logger = logging.getLogger(__name__)

class TpSlMonitor:
    """Take Profit / Stop Loss Monitor - Checks TP/SL levels every 10 seconds"""
    
    def __init__(self, check_interval: int = 10):
        self.check_interval = check_interval  # seconds
        self.running = False
        self.exchange_api = CryptoExchangeAPI()
        
        logger.info(f"TP/SL Monitor initialized with {check_interval}s interval")
    
    def start(self):
        """Start the TP/SL monitor"""
        if self.running:
            logger.warning("TP/SL monitor is already running")
            return
        
        self.running = True
        logger.info("Starting TP/SL Monitor")
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=self.run, daemon=True)
        monitor_thread.start()
    
    def stop(self):
        """Stop the TP/SL monitor"""
        self.running = False
        logger.info("TP/SL Monitor stopped")
    
    def run(self):
        """Main TP/SL monitoring loop"""
        logger.info("TP/SL Monitor started")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Get open positions
                open_positions = get_open_positions()
                if not open_positions:
                    time.sleep(self.check_interval)
                    continue
                
                logger.debug(f"Checking TP/SL for {len(open_positions)} positions...")
                
                # Check each position
                for position in open_positions:
                    if not self.running:
                        break
                        
                    try:
                        self.check_position_tp_sl(position)
                        time.sleep(0.1)  # Small delay between checks
                    except Exception as e:
                        logger.error(f"Error checking TP/SL for position {position.id}: {str(e)}")
                        continue
                
                # Log completion
                elapsed = time.time() - start_time
                logger.debug(f"TP/SL check completed in {elapsed:.2f}s")
                
                # Sleep until next interval
                sleep_time = max(0, self.check_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in TP/SL monitor loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def check_position_tp_sl(self, position: Position):
        """Check if position has hit TP or SL levels"""
        try:
            if not position.current_price:
                # Update current price first
                self.update_position_price(position)
                
            if not position.current_price:
                return
            
            current_price = position.current_price
            entry_price = position.entry_price
            
            # Check stop loss
            if position.stop_loss and current_price <= position.stop_loss:
                logger.info(f"Stop Loss triggered for {position.coin_ref.symbol}: {current_price} <= {position.stop_loss}")
                self.trigger_stop_loss(position)
                return
            
            # Check take profit
            if position.take_profit and current_price >= position.take_profit:
                logger.info(f"Take Profit triggered for {position.coin_ref.symbol}: {current_price} >= {position.take_profit}")
                self.trigger_take_profit(position)
                return
            
            # Optional: Check for trailing stop
            if position.trailing_stop:
                self.check_trailing_stop(position)
                
        except Exception as e:
            logger.error(f"Error checking TP/SL for position {position.id}: {str(e)}")
    
    def update_position_price(self, position: Position):
        """Update position's current price"""
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
    
    def trigger_stop_loss(self, position: Position):
        """Trigger stop loss by placing a market sell order"""
        try:
            coin = position.coin_ref
            
            # Place market sell order
            order_result = self.exchange_api.place_order(
                instrument_name=coin.symbol,
                side='SELL',
                type_='MARKET',
                quantity=position.quantity
            )
            
            if not order_result:
                logger.error(f"Failed to place stop loss order for position {position.id}")
                return
            
            # Create order record
            sell_order = Order(
                coin_id=position.coin_id,
                position_id=position.id,
                order_type='MARKET',
                side='SELL',
                quantity=position.quantity,
                status='PENDING',
                exchange_order_id=order_result.get('order_id'),
                client_order_id=order_result.get('client_oid'),
                notes='Stop Loss Triggered'
            )
            
            db.session.add(sell_order)
            
            # Update position
            position.exit_order_id = sell_order.id
            position.status = 'closing'  # Will be set to 'closed' when order fills
            
            db.session.commit()
            
            SystemLog.log(
                level='WARNING',
                category='TRADING',
                message=f"Stop Loss triggered: {position.coin_ref.symbol} at {position.current_price}",
                details={
                    'entry_price': position.entry_price,
                    'stop_loss': position.stop_loss,
                    'current_price': position.current_price,
                    'quantity': position.quantity,
                    'order_id': order_result.get('order_id')
                },
                position_id=position.id,
                order_id=sell_order.id
            )
            
            logger.info(f"Stop loss order placed for {coin.symbol}: Order ID {order_result.get('order_id')}")
            
        except Exception as e:
            logger.error(f"Error triggering stop loss for position {position.id}: {str(e)}")
    
    def trigger_take_profit(self, position: Position):
        """Trigger take profit by placing a market sell order"""
        try:
            coin = position.coin_ref
            
            # Place market sell order
            order_result = self.exchange_api.place_order(
                instrument_name=coin.symbol,
                side='SELL',
                type_='MARKET',
                quantity=position.quantity
            )
            
            if not order_result:
                logger.error(f"Failed to place take profit order for position {position.id}")
                return
            
            # Create order record
            sell_order = Order(
                coin_id=position.coin_id,
                position_id=position.id,
                order_type='MARKET',
                side='SELL',
                quantity=position.quantity,
                status='PENDING',
                exchange_order_id=order_result.get('order_id'),
                client_order_id=order_result.get('client_oid'),
                notes='Take Profit Triggered'
            )
            
            db.session.add(sell_order)
            
            # Update position
            position.exit_order_id = sell_order.id
            position.status = 'closing'  # Will be set to 'closed' when order fills
            
            db.session.commit()
            
            SystemLog.log(
                level='INFO',
                category='TRADING',
                message=f"Take Profit triggered: {position.coin_ref.symbol} at {position.current_price}",
                details={
                    'entry_price': position.entry_price,
                    'take_profit': position.take_profit,
                    'current_price': position.current_price,
                    'quantity': position.quantity,
                    'order_id': order_result.get('order_id')
                },
                position_id=position.id,
                order_id=sell_order.id
            )
            
            logger.info(f"Take profit order placed for {coin.symbol}: Order ID {order_result.get('order_id')}")
            
        except Exception as e:
            logger.error(f"Error triggering take profit for position {position.id}: {str(e)}")
    
    def check_trailing_stop(self, position: Position):
        """Check and update trailing stop level"""
        try:
            if not position.trailing_stop or not position.current_price:
                return
            
            current_price = position.current_price
            entry_price = position.entry_price
            
            # Calculate profit percentage
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Only update trailing stop if we're in profit
            if profit_pct > 0:
                # Calculate new trailing stop (percentage below current high)
                new_stop_loss = current_price * (1 - position.trailing_stop / 100)
                
                # Only update if new stop loss is higher than current stop loss
                if not position.stop_loss or new_stop_loss > position.stop_loss:
                    old_stop_loss = position.stop_loss
                    position.stop_loss = new_stop_loss
                    
                    db.session.commit()
                    
                    SystemLog.log(
                        level='INFO',
                        category='TRADING',
                        message=f"Trailing stop updated for {position.coin_ref.symbol}: {old_stop_loss} -> {new_stop_loss}",
                        details={
                            'current_price': current_price,
                            'profit_pct': profit_pct,
                            'trailing_stop_pct': position.trailing_stop
                        },
                        position_id=position.id
                    )
                    
        except Exception as e:
            logger.error(f"Error checking trailing stop for position {position.id}: {str(e)}")
    
    def get_status(self):
        """Get monitor status"""
        open_positions_count = Position.query.filter_by(status='open').count()
        
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'open_positions_count': open_positions_count,
            'last_check': datetime.utcnow().isoformat() if self.running else None
        } 