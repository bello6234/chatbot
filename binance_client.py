"""
Binance API Client for Termux Trading Bot
Lightweight Binance API wrapper - no heavy dependencies
"""

import hashlib
import hmac
import time
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List


class BinanceClient:
    """
    Lightweight Binance API client for Termux
    Supports REST API only (no websockets to keep it simple)
    """
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        """
        Initialize Binance client
        
        Args:
            api_key: Your Binance API key
            api_secret: Your Binance API secret
            testnet: Use testnet (True) or real API (False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
    
    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)
    
    def _sign_request(self, query_string: str) -> str:
        """Sign the request with API secret"""
        if not self.api_secret:
            return query_string
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(
        self, 
        endpoint: str, 
        method: str = "GET", 
        params: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API
        
        Args:
            endpoint: API endpoint (e.g., "/api/v3/time")
            method: HTTP method (GET, POST, DELETE)
            params: Request parameters
            signed: Whether to sign the request
            
        Returns:
            Dictionary with API response
        """
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        # Add timestamp for signed requests
        if signed:
            params['timestamp'] = self._get_timestamp()
        
        # Convert params to query string
        query_string = urllib.parse.urlencode(params)
        
        # Sign the request if needed
        if signed and self.api_secret:
            params['signature'] = self._sign_request(query_string)
            query_string = urllib.parse.urlencode(params)
        
        # Build full URL
        if method == "GET":
            full_url = f"{url}?{query_string}"
            data = None
        else:
            full_url = url
            data = query_string.encode('utf-8')
        
        # Make request
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            req = urllib.request.Request(full_url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                return {'error': error_json.get('msg', str(e))}
            except:
                return {'error': str(e)}
        except Exception as e:
            return {'error': str(e)}
    
    # ========== Public API Methods ==========
    
    def ping(self) -> bool:
        """Test connectivity to Binance API"""
        result = self._make_request("/api/v3/ping")
        return result.get('error') is None
    
    def get_server_time(self) -> Dict[str, Any]:
        """Get server time"""
        return self._make_request("/api/v3/time")
    
    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a symbol"""
        return self._make_request("/api/v3/ticker/price", params={'symbol': symbol})
    
    def get_ticker_24hr(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr price change statistics"""
        return self._make_request("/api/v3/ticker/24hr", params={'symbol': symbol})
    
    def get_depth(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get order book depth"""
        return self._make_request("/api/v3/depth", params={'symbol': symbol, 'limit': limit})
    
    def get_recent_trades(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Get recent trades"""
        return self._make_request("/api/v3/trades", params={'symbol': symbol, 'limit': limit})
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str = "1h", 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get candlestick/kline data
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of candlesticks (max 1000)
            
        Returns:
            List of candlestick dictionaries
        """
        result = self._make_request(
            "/api/v3/klines",
            params={'symbol': symbol, 'interval': interval, 'limit': limit}
        )
        
        if 'error' in result:
            return []
        
        # Convert to simpler format
        klines = []
        for k in result:
            klines.append({
                'open_time': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': k[6],
                'quote_volume': float(k[7]),
                'trades': k[8],
                'taker_buy_base': float(k[9]),
                'taker_buy_quote': float(k[10]),
                'ignore': k[11]
            })
        return klines
    
    def get_historical_klines(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get historical candlestick data with pagination
        """
        all_klines = []
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1000)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        while len(all_klines) < limit:
            result = self._make_request("/api/v3/klines", params=params)
            if 'error' in result:
                break
            
            # Convert and add
            for k in result:
                all_klines.append({
                    'open_time': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6]
                })
            
            # Check if we got less than limit (end of data)
            if len(result) < params['limit']:
                break
            
            # Update start time for next page
            params['startTime'] = result[-1][0] + 1
            
            # Don't exceed total limit
            if len(all_klines) >= limit:
                all_klines = all_klines[:limit]
                break
        
        return all_klines
    
    # ========== Private API Methods ==========
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.api_key or not self.api_secret:
            return {'error': 'API keys required for private endpoints'}
        return self._make_request("/api/v3/account", signed=True)
    
    def get_balance(self, asset: str = "USDT") -> Dict[str, Any]:
        """Get balance for a specific asset"""
        account = self.get_account_info()
        if 'error' in account:
            return account
        
        for balance in account.get('balances', []):
            if balance['asset'] == asset:
                return {
                    'asset': balance['asset'],
                    'free': float(balance['free']),
                    'locked': float(balance['locked'])
                }
        return {'asset': asset, 'free': 0.0, 'locked': 0.0}
    
    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Create a new order
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "BUY" or "SELL"
            order_type: "MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_LIMIT", etc.
            quantity: Order quantity
            price: Price for LIMIT orders
            stop_price: Stop price for STOP orders
            time_in_force: "GTC", "IOC", "FOK"
            
        Returns:
            Order confirmation dictionary
        """
        if not self.api_key or not self.api_secret:
            return {'error': 'API keys required for trading'}
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'timeInForce': time_in_force
        }
        
        if price is not None:
            params['price'] = f"{price:.8f}"
        if stop_price is not None:
            params['stopPrice'] = f"{stop_price:.8f}"
        
        return self._make_request("/api/v3/order", method="POST", params=params, signed=True)
    
    def create_test_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a test order (TESTNET only)
        """
        if not self.testnet:
            return {'error': 'Test orders only work on testnet'}
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }
        
        if price is not None:
            params['price'] = f"{price:.8f}"
        
        return self._make_request("/api/v3/order/test", method="POST", params=params, signed=True)
    
    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get order status"""
        if not self.api_key or not self.api_secret:
            return {'error': 'API keys required'}
        return self._make_request(
            "/api/v3/order",
            params={'symbol': symbol, 'orderId': order_id},
            signed=True
        )
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an order"""
        if not self.api_key or not self.api_secret:
            return {'error': 'API keys required'}
        return self._make_request(
            "/api/v3/order",
            method="DELETE",
            params={'symbol': symbol, 'orderId': order_id},
            signed=True
        )
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        if not self.api_key or not self.api_secret:
            return []
        
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        result = self._make_request("/api/v3/openOrders", params=params, signed=True)
        return result.get('error') and [] or result
    
    def get_all_orders(
        self,
        symbol: str,
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all orders for a symbol"""
        if not self.api_key or not self.api_secret:
            return []
        
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        result = self._make_request("/api/v3/allOrders", params=params, signed=True)
        return result.get('error') and [] or result
    
    def get_trade_history(
        self,
        symbol: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get trade history"""
        if not self.api_key or not self.api_secret:
            return []
        
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        result = self._make_request("/api/v3/myTrades", params=params, signed=True)
        return result.get('error') and [] or result
    
    # ========== Utility Methods ==========
    
    def get_symbol_info(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Get exchange info for a symbol"""
        result = self._make_request("/api/v3/exchangeInfo")
        if 'error' in result:
            return {}
        
        for s in result.get('symbols', []):
            if s['symbol'] == symbol:
                return s
        return {}
    
    def get_min_notional(self, symbol: str = "BTCUSDT") -> float:
        """Get minimum notional (order value) for a symbol"""
        info = self.get_symbol_info(symbol)
        for f in info.get('filters', []):
            if f.get('filterType') == 'MIN_NOTIONAL':
                return float(f.get('minNotional', 0))
        return 10.0  # Default
    
    def get_price_precision(self, symbol: str = "BTCUSDT") -> int:
        """Get price precision for a symbol"""
        info = self.get_symbol_info(symbol)
        for f in info.get('filters', []):
            if f.get('filterType') == 'PRICE_FILTER':
                tick_size = float(f.get('tickSize', '0.01'))
                return len(f"{tick_size:.8f}".rstrip('0').split('.')[-1])
        return 2
    
    def get_quantity_precision(self, symbol: str = "BTCUSDT") -> int:
        """Get quantity precision for a symbol"""
        info = self.get_symbol_info(symbol)
        for f in info.get('filters', []):
            if f.get('filterType') == 'LOT_SIZE':
                step_size = float(f.get('stepSize', '0.00000001'))
                return len(f"{step_size:.8f}".rstrip('0').split('.')[-1])
        return 8
    
    def format_price(self, price: float, symbol: str = "BTCUSDT") -> str:
        """Format price with correct precision"""
        precision = self.get_price_precision(symbol)
        return f"{price:.{precision}f}"
    
    def format_quantity(self, quantity: float, symbol: str = "BTCUSDT") -> str:
        """Format quantity with correct precision"""
        precision = self.get_quantity_precision(symbol)
        return f"{quantity:.{precision}f}"


def test_binance_connection():
    """Test Binance API connection"""
    print("Testing Binance API connection...")
    
    # Test with testnet first
    client = BinanceClient(testnet=True)
    
    if client.ping():
        print("✓ Testnet connection successful")
        
        # Get server time
        time_result = client.get_server_time()
        if 'serverTime' in time_result:
            print(f"✓ Server time: {time_result['serverTime']}")
        
        # Get BTC price
        price_result = client.get_ticker_price("BTCUSDT")
        if 'price' in price_result:
            print(f"✓ BTC/USDT price: ${price_result['price']}")
        
        # Get recent klines
        klines = client.get_klines("BTCUSDT", "1h", 10)
        if klines:
            print(f"✓ Retrieved {len(klines)} candlesticks")
            print(f"  Last close: ${klines[-1]['close']:.2f}")
        
        return True
    else:
        print("✗ Testnet connection failed")
        return False


if __name__ == "__main__":
    test_binance_connection()
