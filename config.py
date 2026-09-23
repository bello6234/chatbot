"""Configuration for the trading bot"""

# Trading settings
INITIAL_BALANCE = 5.0  # $5 USDT
TRADE_SYMBOL = "BTCUSDT"  # Trading pair
TRADE_QUANTITY = 0.0001  # Small quantity for testing

# Strategy settings
SHORT_SMA = 10  # Short-term Simple Moving Average
LONG_SMA = 30  # Long-term Simple Moving Average
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# API settings (for real trading - currently using paper trading)
BINANCE_API_KEY = None
BINANCE_API_SECRET = None

# Paper trading mode
PAPER_TRADING = True

# Timeframe for trading
TIMEFRAME = "1h"  # 1 hour candles
LOOKBACK_PERIODS = 100  # Number of candles to fetch
