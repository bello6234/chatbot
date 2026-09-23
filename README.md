# Binance Trading Bot - Termux Edition

A **complete trading bot** for Binance with paper trading, testnet, and live trading modes. Built for Termux on Android.

## Features

### Trading Modes
- **📄 Paper Trading**: Simulate trading with virtual money (no API keys needed)
- **🧪 Testnet Trading**: Real orders with fake money on Binance Testnet
- **🔥 Live Trading**: Real orders with real money on Binance (use with caution!)

### Strategies
- **SMA Crossover + RSI** - Classic crossover with RSI filter
- **Mean Reversion** - Buy low, sell high
- **Breakout** - Trade on price breakouts
- **Trend Following** - Uses EMA crossover

### Risk Management
- **Stop-Loss**: Automatic 1% stop loss on every trade
- **Take-Profit**: Automatic 3% take profit
- **Position Sizing**: Calculates quantity based on 2% risk per trade
- **Max Drawdown Tracking**: Monitors worst loss

### Technical Indicators
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI) - Wilder's method
- Bollinger Bands

## Quick Start

### Option 1: Paper Trading (No Setup)
```bash
python trading_bot_binance.py
```
Select **Mode 1** (Paper Trading) and run a backtest.

### Option 2: Testnet Trading (Free Practice)
1. Get API keys from [Binance Testnet](https://testnet.binance.vision/)
2. Run the bot and select **Mode 2**
3. Enter your API keys when prompted
4. Start trading with fake money!

### Option 3: Live Trading (Real Money)
1. Get API keys from [Binance](https://www.binance.com/en/my/settings/api-management)
2. Run the bot and select **Mode 3**
3. Enter your API keys when prompted
4. **BE CAREFUL** - This uses real money!

## Installation

### On Termux
```bash
# Install Python
pkg install python

# Clone or download the bot files
cd ~/chatbot
# Download trading_bot_binance.py and binance_client.py

# Run it
python trading_bot_binance.py
```

### On Any System
```bash
# No dependencies needed!
python trading_bot_binance.py
```

## Usage

### Menu Options
1. **Paper Trading** - Simulate with historical-like data
2. **Testnet Trading** - Real orders, fake money (requires Binance Testnet API keys)
3. **Live Trading** - Real orders, real money (requires Binance API keys)

### Strategy Selection
- **1. SMA Crossover + RSI** (Recommended for beginners)
- **2. Mean Reversion** (Good for ranging markets)
- **3. Breakout** (Good for trending markets)
- **4. Trend Following** (Good for strong trends)

### Custom Parameters
- **Initial Balance**: Starting capital (default: $5)
- **Symbol**: Trading pair (default: BTCUSDT)
- **Risk per Trade**: Percentage of balance to risk (default: 2%)
- **Stop Loss**: Percentage stop loss (default: 1%)
- **Take Profit**: Percentage take profit (default: 3%)

## API Key Setup

### For Testnet
1. Go to [Binance Testnet](https://testnet.binance.vision/)
2. Register or login
3. Go to API Management
4. Create new API keys
5. Save keys when prompted by the bot

### For Live Trading
1. Go to [Binance](https://www.binance.com/)
2. Login to your account
3. Go to Settings > API Management
4. Create new API keys with **Spot & Margin Trading** permissions
5. **DO NOT enable withdrawals** (for security)
6. Save keys when prompted by the bot

## Files

- `trading_bot_binance.py` - Main trading bot
- `binance_client.py` - Binance API wrapper
- `README.md` - This file

## Requirements

- Python 3.6+
- No other dependencies (uses only standard library)
- Termux (for Android) or any terminal

## Security

- API keys are saved locally in `binance_keys.json`
- Never share your API keys
- For live trading, disable withdrawals on your API keys
- Use testnet for testing before using real money

## Risk Warning

⚠️ **TRADING INVOLVES RISK**

- This bot is for educational purposes
- Past performance does not guarantee future results
- Always test with paper trading or testnet first
- Never invest more than you can afford to lose
- Use at your own risk

## Example Output

```
============================================================
              BINANCE TRADING BOT - Termux Edition
============================================================

Select Trading Mode:
1. Paper Trading (simulated)
2. Testnet Trading (real orders, fake money)
3. Live Trading (real orders, real money)

Mode (1-3): 1
Symbol (e.g., BTCUSDT): BTCUSDT
Initial balance ($): 5

Select Strategy:
1. SMA Crossover + RSI (default)
2. Mean Reversion
3. Breakout
4. Trend Following
Strategy (1-4): 1
Risk per trade (%): 2
Stop loss (%): 1
Take profit (%): 3

Starting PAPER trading on BTCUSDT...
Strategy: SMA Crossover + RSI
Risk: 2.0% | SL: 1.0% | TP: 3.0%

Running backtest...

============================================================
                   TRADING BOT DASHBOARD
============================================================
Current Balance: $4.99
Total Value:     $4.99
Open Positions:  0
Total Trades:    12
Total Profit:    $-0.01 (-0.20%)
Win Rate:        41.7%
Profit Factor:   0.98
Max Drawdown:   6.22%

--- OPEN POSITIONS ---

--- TRADE HISTORY ---
  BUY    | 2026-09-23 09:37 | $48706.03 | 2026-09-23 09:37 | $50179.36 | +$0.3034
  SELL   | 2026-09-23 09:37 | $51641.19 | 2026-09-23 09:37 | $52066.21 | -$0.0835

============================================================
                      BACKTEST SUMMARY
============================================================
Initial Balance:  $5.00
Final Balance:    $4.99
Total Profit:     $-0.01 (-0.20%)
Total Trades:     12
Winning Trades:   5
Losing Trades:    7
Win Rate:         41.7%
Profit Factor:    0.98
Max Drawdown:    6.22%
```

## Troubleshooting

### "No module named..."
The bot uses only standard Python libraries. No installation needed.

### Connection Errors
- Check your internet connection
- Binance API might be down (check [Binance Status](https://www.binance.com/en/status))
- Testnet might be down

### API Key Errors
- Verify your API keys are correct
- Ensure you have the right permissions (Spot & Margin Trading)
- For testnet, use testnet API keys
- For live, use live API keys

## Support

For issues or questions:
- Check the README
- Try paper trading first
- Use testnet before live trading
- Review your API key permissions

## License

MIT License - Free for personal and educational use.

## Disclaimer

This software is provided "as is" without warranty of any kind. Use at your own risk.
