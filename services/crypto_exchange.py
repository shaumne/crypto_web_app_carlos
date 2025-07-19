import os
import time
import hmac
import hashlib
import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from models import db, SystemLog

logger = logging.getLogger(__name__)

class CryptoExchangeAPI:
    """Crypto.com Exchange API Integration"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, sandbox: bool = True):
        self.api_key = api_key or os.getenv('CRYPTO_API_KEY')
        self.api_secret = api_secret or os.getenv('CRYPTO_API_SECRET')
        self.sandbox = sandbox
        
        if self.sandbox:
            self.base_url = "https://uat-api.3ona.co/exchange/v1"  # Sandbox URL
        else:
            self.base_url = "https://api.crypto.com/exchange/v1"  # Production URL
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'crypto-trading-webapp/1.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        logger.info(f"Crypto.com API initialized - Sandbox: {self.sandbox}")
    
    def _wait_for_rate_limit(self):
        """Ensure minimum time between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _generate_signature(self, method: str, path: str, params: dict = None, body: str = "") -> str:
        """Generate signature for authenticated requests"""
        if not self.api_secret:
            raise ValueError("API secret is required for authenticated requests")
        
        # Create the signature string
        nonce = str(int(time.time() * 1000))
        
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            path_with_params = f"{path}?{query_string}"
        else:
            path_with_params = path
        
        sig_payload = method + path_with_params + body + nonce
        
        # Generate HMAC signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sig_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, nonce
    
    def _make_request(self, method: str, endpoint: str, params: dict = None, 
                     data: dict = None, authenticated: bool = False) -> dict:
        """Make HTTP request to the API"""
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = self.session.headers.copy()
        
        # Prepare request body
        body = ""
        if data:
            body = json.dumps(data, separators=(',', ':'))
        
        # Add authentication headers if required
        if authenticated:
            if not self.api_key or not self.api_secret:
                raise ValueError("API credentials are required for authenticated requests")
            
            signature, nonce = self._generate_signature(method, endpoint, params, body)
            headers.update({
                'api-key': self.api_key,
                'signature': signature,
                'nonce': nonce
            })
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=body if body else None,
                headers=headers,
                timeout=30
            )
            
            # Log request
            SystemLog.log(
                level='INFO',
                category='API',
                message=f"API Request: {method} {endpoint}",
                details={
                    'status_code': response.status_code,
                    'authenticated': authenticated,
                    'params': params,
                    'data': data
                }
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {method} {endpoint} - {str(e)}"
            logger.error(error_msg)
            
            SystemLog.log(
                level='ERROR',
                category='API',
                message=error_msg,
                details={
                    'method': method,
                    'endpoint': endpoint,
                    'error': str(e),
                    'params': params,
                    'data': data
                }
            )
            
            raise
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self._make_request('GET', '/public/get-instruments')
            return response.get('code') == 0
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_instruments(self) -> List[dict]:
        """Get available trading instruments"""
        try:
            response = self._make_request('GET', '/public/get-instruments')
            if response.get('code') == 0:
                return response.get('result', {}).get('data', [])
            else:
                logger.error(f"Failed to get instruments: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting instruments: {str(e)}")
            return []
    
    def get_ticker(self, instrument_name: str) -> Optional[dict]:
        """Get ticker information for an instrument"""
        try:
            params = {'instrument_name': instrument_name}
            response = self._make_request('GET', '/public/get-ticker', params=params)
            
            if response.get('code') == 0:
                data = response.get('result', {}).get('data', [])
                return data[0] if data else None
            else:
                logger.error(f"Failed to get ticker for {instrument_name}: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting ticker for {instrument_name}: {str(e)}")
            return None
    
    def get_orderbook(self, instrument_name: str, depth: int = 10) -> Optional[dict]:
        """Get orderbook for an instrument"""
        try:
            params = {
                'instrument_name': instrument_name,
                'depth': depth
            }
            response = self._make_request('GET', '/public/get-book', params=params)
            
            if response.get('code') == 0:
                data = response.get('result', {}).get('data', [])
                return data[0] if data else None
            else:
                logger.error(f"Failed to get orderbook for {instrument_name}: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting orderbook for {instrument_name}: {str(e)}")
            return None
    
    def get_candlestick_data(self, instrument_name: str, timeframe: str = '5m', 
                           count: int = 100) -> List[dict]:
        """Get candlestick data for technical analysis"""
        try:
            params = {
                'instrument_name': instrument_name,
                'timeframe': timeframe,
                'count': count
            }
            response = self._make_request('GET', '/public/get-candlestick', params=params)
            
            if response.get('code') == 0:
                return response.get('result', {}).get('data', [])
            else:
                logger.error(f"Failed to get candlestick data for {instrument_name}: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting candlestick data for {instrument_name}: {str(e)}")
            return []
    
    # Authenticated endpoints
    def get_account_info(self) -> Optional[dict]:
        """Get account information"""
        try:
            response = self._make_request('POST', '/private/get-account-summary', authenticated=True)
            
            if response.get('code') == 0:
                return response.get('result')
            else:
                logger.error(f"Failed to get account info: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_balance(self, currency: str = None) -> List[dict]:
        """Get account balance"""
        try:
            data = {}
            if currency:
                data['currency'] = currency
                
            response = self._make_request('POST', '/private/get-account-summary', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                accounts = response.get('result', {}).get('accounts', [])
                if currency:
                    return [acc for acc in accounts if acc.get('currency') == currency]
                return accounts
            else:
                logger.error(f"Failed to get balance: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return []
    
    def place_order(self, instrument_name: str, side: str, type_: str, 
                   quantity: float, price: float = None, time_in_force: str = 'GTC',
                   client_oid: str = None) -> Optional[dict]:
        """Place a new order"""
        try:
            data = {
                'instrument_name': instrument_name,
                'side': side.upper(),  # BUY or SELL
                'type': type_.upper(),  # LIMIT, MARKET, STOP_LOSS, STOP_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT
                'quantity': str(quantity),
                'time_in_force': time_in_force
            }
            
            if price:
                data['price'] = str(price)
            
            if client_oid:
                data['client_oid'] = client_oid
            
            response = self._make_request('POST', '/private/create-order', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                result = response.get('result')
                
                SystemLog.log(
                    level='INFO',
                    category='TRADING',
                    message=f"Order placed: {side} {quantity} {instrument_name}",
                    details={
                        'order_id': result.get('order_id'),
                        'client_oid': result.get('client_oid'),
                        'type': type_,
                        'price': price
                    }
                )
                
                return result
            else:
                error_msg = f"Failed to place order: {response}"
                logger.error(error_msg)
                
                SystemLog.log(
                    level='ERROR',
                    category='TRADING',
                    message=error_msg,
                    details={
                        'instrument_name': instrument_name,
                        'side': side,
                        'type': type_,
                        'quantity': quantity,
                        'price': price
                    }
                )
                
                return None
        except Exception as e:
            error_msg = f"Error placing order: {str(e)}"
            logger.error(error_msg)
            
            SystemLog.log(
                level='ERROR',
                category='TRADING',
                message=error_msg,
                details={
                    'instrument_name': instrument_name,
                    'side': side,
                    'type': type_,
                    'quantity': quantity,
                    'price': price,
                    'error': str(e)
                }
            )
            
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            data = {'order_id': order_id}
            response = self._make_request('POST', '/private/cancel-order', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                SystemLog.log(
                    level='INFO',
                    category='TRADING',
                    message=f"Order cancelled: {order_id}"
                )
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}: {response}")
                return False
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get order status"""
        try:
            data = {'order_id': order_id}
            response = self._make_request('POST', '/private/get-order-detail', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                return response.get('result')
            else:
                logger.error(f"Failed to get order status for {order_id}: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {str(e)}")
            return None
    
    def get_open_orders(self, instrument_name: str = None) -> List[dict]:
        """Get open orders"""
        try:
            data = {}
            if instrument_name:
                data['instrument_name'] = instrument_name
            
            response = self._make_request('POST', '/private/get-open-orders', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                return response.get('result', {}).get('order_list', [])
            else:
                logger.error(f"Failed to get open orders: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting open orders: {str(e)}")
            return []
    
    def get_order_history(self, instrument_name: str = None, 
                         start_ts: int = None, end_ts: int = None,
                         page_size: int = 100, page: int = 0) -> List[dict]:
        """Get order history"""
        try:
            data = {
                'page_size': page_size,
                'page': page
            }
            
            if instrument_name:
                data['instrument_name'] = instrument_name
            if start_ts:
                data['start_ts'] = start_ts
            if end_ts:
                data['end_ts'] = end_ts
            
            response = self._make_request('POST', '/private/get-order-history', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                return response.get('result', {}).get('order_list', [])
            else:
                logger.error(f"Failed to get order history: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []
    
    def get_trades(self, instrument_name: str = None, 
                  start_ts: int = None, end_ts: int = None,
                  page_size: int = 100, page: int = 0) -> List[dict]:
        """Get trade history"""
        try:
            data = {
                'page_size': page_size,
                'page': page
            }
            
            if instrument_name:
                data['instrument_name'] = instrument_name
            if start_ts:
                data['start_ts'] = start_ts
            if end_ts:
                data['end_ts'] = end_ts
            
            response = self._make_request('POST', '/private/get-trades', 
                                        data=data, authenticated=True)
            
            if response.get('code') == 0:
                return response.get('result', {}).get('trade_list', [])
            else:
                logger.error(f"Failed to get trades: {response}")
                return []
        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return []
    
    # Helper methods
    def get_minimum_order_size(self, instrument_name: str) -> float:
        """Get minimum order size for an instrument"""
        instruments = self.get_instruments()
        for instrument in instruments:
            if instrument.get('instrument_name') == instrument_name:
                return float(instrument.get('min_quantity', 0))
        return 0.0
    
    def get_price_precision(self, instrument_name: str) -> int:
        """Get price precision for an instrument"""
        instruments = self.get_instruments()
        for instrument in instruments:
            if instrument.get('instrument_name') == instrument_name:
                return int(instrument.get('price_decimals', 2))
        return 2
    
    def get_quantity_precision(self, instrument_name: str) -> int:
        """Get quantity precision for an instrument"""
        instruments = self.get_instruments()
        for instrument in instruments:
            if instrument.get('instrument_name') == instrument_name:
                return int(instrument.get('quantity_decimals', 6))
        return 6
    
    def format_price(self, price: float, instrument_name: str) -> str:
        """Format price according to instrument precision"""
        precision = self.get_price_precision(instrument_name)
        return f"{price:.{precision}f}"
    
    def format_quantity(self, quantity: float, instrument_name: str) -> str:
        """Format quantity according to instrument precision"""
        precision = self.get_quantity_precision(instrument_name)
        return f"{quantity:.{precision}f}"
    
    def calculate_notional_value(self, quantity: float, price: float) -> float:
        """Calculate notional value of an order"""
        return quantity * price
    
    def is_sufficient_balance(self, currency: str, required_amount: float) -> bool:
        """Check if account has sufficient balance"""
        try:
            balances = self.get_balance(currency)
            if not balances:
                return False
            
            available = float(balances[0].get('available', 0))
            return available >= required_amount
        except Exception as e:
            logger.error(f"Error checking balance for {currency}: {str(e)}")
            return False 