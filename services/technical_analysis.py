import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from services.crypto_exchange import CryptoExchangeAPI
from models import db, Coin, TechnicalAnalysis, SystemLog

logger = logging.getLogger(__name__)

class TechnicalAnalysisService:
    """Technical Analysis Service for generating trading signals"""
    
    def __init__(self, exchange_api: CryptoExchangeAPI = None):
        self.exchange_api = exchange_api or CryptoExchangeAPI()
        self.timeframe = '15m'  # Default timeframe
        self.data_points = 200  # Number of candles to fetch for analysis
        
        # Technical analysis parameters
        self.rsi_period = 14
        self.ma50_period = 50
        self.ma200_period = 200
        self.ema10_period = 10
        self.atr_period = 14
        self.atr_multiplier = 2.0
        
        # Signal thresholds
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.volume_threshold = 1.5
        
        logger.info("Technical Analysis Service initialized")
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return np.full(len(prices), 50.0)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        rs_values = []
        
        # First RSI calculation
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100
        rs_values.append(rsi)
        
        # Calculate remaining RSI values using smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
            rs_values.append(rsi)
        
        # Pad the beginning with neutral values
        result = np.full(len(prices), 50.0)
        result[period:] = rs_values
        
        return result
    
    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return np.full(len(prices), np.mean(prices))
        
        sma = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])
        
        # Fill initial values with expanding mean
        for i in range(period - 1):
            sma[i] = np.mean(prices[:i + 1])
        
        return sma
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) == 0:
            return np.array([])
        
        ema = np.zeros(len(prices))
        multiplier = 2 / (period + 1)
        
        # First EMA value is just the first price
        ema[0] = prices[0]
        
        # Calculate EMA for remaining values
        for i in range(1, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, 
                      closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Average True Range"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return np.full(len(highs), 0.0)
        
        # Calculate True Range
        tr = np.zeros(len(highs))
        tr[0] = highs[0] - lows[0]  # First TR is just high - low
        
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr[i] = max(tr1, tr2, tr3)
        
        # Calculate ATR using simple moving average of TR
        atr = self._calculate_sma(tr, period)
        
        return atr
    
    def _calculate_volume_ratio(self, volumes: np.ndarray, period: int = 14) -> float:
        """Calculate current volume ratio to average volume"""
        if len(volumes) < period + 1:
            return 1.0
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-(period+1):-1])  # Exclude current volume
        
        if avg_volume > 0:
            return current_volume / avg_volume
        return 1.0
    
    def get_candlestick_data(self, instrument_name: str) -> Optional[pd.DataFrame]:
        """Get candlestick data for analysis"""
        try:
            candles = self.exchange_api.get_candlestick_data(
                instrument_name=instrument_name,
                timeframe=self.timeframe,
                count=self.data_points
            )
            
            if not candles:
                logger.warning(f"No candlestick data received for {instrument_name}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            
            # Rename columns to standard format
            df = df.rename(columns={
                'o': 'open',
                'h': 'high', 
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            })
            
            # Convert price columns to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Retrieved {len(df)} candles for {instrument_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting candlestick data for {instrument_name}: {str(e)}")
            return None
    
    def analyze_coin(self, coin: Coin) -> Optional[Dict]:
        """Perform complete technical analysis for a coin"""
        try:
            # Format symbol for exchange API
            instrument_name = f"{coin.original_symbol}_{coin.base_currency}"
            
            # Get candlestick data
            df = self.get_candlestick_data(instrument_name)
            if df is None or len(df) < 20:
                logger.warning(f"Insufficient data for analysis: {instrument_name}")
                return None
            
            # Extract price data
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values
            
            # Calculate technical indicators
            rsi = self._calculate_rsi(closes, self.rsi_period)
            ma50 = self._calculate_sma(closes, self.ma50_period)
            ma200 = self._calculate_sma(closes, self.ma200_period)
            ema10 = self._calculate_ema(closes, self.ema10_period)
            atr = self._calculate_atr(highs, lows, closes, self.atr_period)
            
            # Get latest values
            current_price = closes[-1]
            current_high = highs[-1]
            current_low = lows[-1]
            current_volume = volumes[-1]
            current_rsi = rsi[-1]
            current_ma50 = ma50[-1]
            current_ma200 = ma200[-1]
            current_ema10 = ema10[-1]
            current_atr = atr[-1]
            
            # Calculate volume ratio
            volume_ratio = self._calculate_volume_ratio(volumes)
            
            # Calculate support and resistance levels
            recent_highs = highs[-20:]  # Last 20 periods
            recent_lows = lows[-20:]
            resistance_level = np.max(recent_highs) * 1.02  # 2% above recent high
            support_level = np.min(recent_lows) * 0.98     # 2% below recent low
            
            # Validate moving averages
            ma50_valid = current_price > current_ma50
            ma200_valid = current_price > current_ma200
            ema10_valid = current_price > current_ema10
            
            # Count valid MA conditions
            valid_ma_count = sum([ma50_valid, ma200_valid, ema10_valid])
            
            # Generate trading signals
            buy_signal = self._generate_buy_signal(
                current_rsi, valid_ma_count, volume_ratio
            )
            
            sell_signal = self._generate_sell_signal(
                current_rsi, current_price, resistance_level
            )
            
            # Determine action
            if buy_signal:
                action = 'BUY'
            elif sell_signal:
                action = 'SELL'
            else:
                action = 'WAIT'
            
            # Calculate take profit and stop loss
            take_profit, stop_loss = self._calculate_tp_sl(
                current_price, current_atr, resistance_level, support_level
            )
            
            # Calculate risk/reward ratio
            risk = current_price - stop_loss if stop_loss > 0 else 0
            reward = take_profit - current_price if take_profit > 0 else 0
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # Create analysis result
            analysis = {
                'coin_id': coin.id,
                'timestamp': datetime.utcnow(),
                'last_price': current_price,
                'high_24h': current_high,
                'low_24h': current_low,
                'volume_24h': current_volume,
                'volume_ratio': volume_ratio,
                'rsi': current_rsi,
                'ma50': current_ma50,
                'ma200': current_ma200,
                'ema10': current_ema10,
                'atr': current_atr,
                'support_level': support_level,
                'resistance_level': resistance_level,
                'buy_signal': buy_signal,
                'sell_signal': sell_signal,
                'action': action,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'risk_reward_ratio': risk_reward_ratio,
                'ma50_valid': ma50_valid,
                'ma200_valid': ma200_valid,
                'ema10_valid': ema10_valid
            }
            
            logger.info(f"Analysis completed for {coin.symbol}: {action} signal")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {coin.symbol}: {str(e)}")
            SystemLog.log(
                level='ERROR',
                category='ANALYSIS',
                message=f"Technical analysis failed for {coin.symbol}",
                details={'error': str(e)},
                coin_id=coin.id
            )
            return None
    
    def _generate_buy_signal(self, rsi: float, valid_ma_count: int, 
                           volume_ratio: float) -> bool:
        """Generate buy signal based on technical conditions"""
        # Buy conditions (from original algorithm):
        # 1) RSI < 40 and at least 2 MA conditions
        # 2) RSI < 30 and at least 1 MA condition
        # 3) RSI < 45 and at least 1 MA condition and volume_ratio >= 1.5
        
        condition1 = rsi < 40 and valid_ma_count >= 2
        condition2 = rsi < 30 and valid_ma_count >= 1
        condition3 = rsi < 45 and valid_ma_count >= 1 and volume_ratio >= 1.5
        
        return condition1 or condition2 or condition3
    
    def _generate_sell_signal(self, rsi: float, price: float, 
                            resistance: float) -> bool:
        """Generate sell signal based on technical conditions"""
        # Sell condition: RSI > 70 and price breaks resistance
        return rsi > 70 and price > resistance
    
    def _calculate_tp_sl(self, entry_price: float, atr: float, 
                        resistance: float, support: float) -> Tuple[float, float]:
        """Calculate take profit and stop loss levels"""
        # ATR-based calculations
        if atr > 0:
            # Stop Loss: Entry price - (ATR * multiplier)
            atr_stop_loss = entry_price - (atr * self.atr_multiplier)
            
            # Use support level if it's closer than ATR stop loss
            if support > 0 and support < entry_price:
                stop_loss = min(atr_stop_loss, support * 0.99)  # 1% buffer below support
            else:
                stop_loss = atr_stop_loss
            
            # Take Profit: Entry price + (ATR * multiplier)
            atr_take_profit = entry_price + (atr * self.atr_multiplier)
            
            # Use resistance level if it's higher than ATR take profit
            if resistance > atr_take_profit:
                take_profit = resistance
            else:
                take_profit = atr_take_profit
        else:
            # Fallback to percentage-based if ATR is not available
            stop_loss = entry_price * 0.95   # 5% stop loss
            take_profit = entry_price * 1.10  # 10% take profit
        
        return take_profit, stop_loss
    
    def save_analysis(self, analysis_data: Dict) -> Optional[TechnicalAnalysis]:
        """Save technical analysis to database"""
        try:
            # Create new analysis record
            analysis = TechnicalAnalysis(**analysis_data)
            db.session.add(analysis)
            db.session.commit()
            
            logger.info(f"Saved analysis for coin_id {analysis_data['coin_id']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error saving analysis: {str(e)}")
            db.session.rollback()
            return None
    
    def get_signal_strength(self, analysis: TechnicalAnalysis) -> int:
        """Calculate signal strength (1-5 scale)"""
        strength = 0
        
        # MA validations (3 points max)
        if analysis.ma200_valid:
            strength += 1
        if analysis.ma50_valid:
            strength += 1  
        if analysis.ema10_valid:
            strength += 1
        
        # Volume factor (1 point)
        if analysis.volume_ratio >= 1.5:
            strength += 1
        
        # RSI factor (1 point)
        if analysis.rsi < 30:  # Oversold
            strength += 1
        
        return min(strength, 5)
    
    def analyze_all_coins(self) -> List[TechnicalAnalysis]:
        """Analyze all active coins and save results"""
        try:
            active_coins = Coin.query.filter_by(is_active=True, is_trading_enabled=True).all()
            results = []
            
            logger.info(f"Starting analysis for {len(active_coins)} coins")
            
            for coin in active_coins:
                try:
                    analysis_data = self.analyze_coin(coin)
                    if analysis_data:
                        analysis = self.save_analysis(analysis_data)
                        if analysis:
                            results.append(analysis)
                except Exception as e:
                    logger.error(f"Error analyzing coin {coin.symbol}: {str(e)}")
                    continue
            
            logger.info(f"Completed analysis for {len(results)} coins")
            return results
            
        except Exception as e:
            logger.error(f"Error in analyze_all_coins: {str(e)}")
            return []
    
    def get_latest_analysis(self, coin_id: int) -> Optional[TechnicalAnalysis]:
        """Get the latest technical analysis for a coin"""
        return TechnicalAnalysis.query.filter_by(coin_id=coin_id)\
                                    .order_by(TechnicalAnalysis.timestamp.desc())\
                                    .first()
    
    def get_buy_signals(self, limit: int = 10) -> List[TechnicalAnalysis]:
        """Get latest buy signals"""
        return TechnicalAnalysis.query.filter_by(action='BUY')\
                                    .order_by(TechnicalAnalysis.timestamp.desc())\
                                    .limit(limit).all() 