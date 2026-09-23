# Trading Bot - Termux Edition

A **lite trading bot** built for Termux on Android. No numpy/pandas required - pure Python!

## Features

- **Paper Trading**: Simulate trading with $5 USDT (or any amount)
- **Technical Indicators**: 
  - Simple Moving Average (SMA) Crossover
  - Relative Strength Index (RSI)
- **Terminal Interface**: Works perfectly in Termux
- **No Heavy Dependencies**: Uses only standard Python libraries
- **Backtesting**: Test strategies on generated market data

## Quick Start

```bash
# Just run it - no installation needed!
python trading_bot_lite.py
```

Then select option **1** for a default backtest with $5 USDT.

## Usage

### Option 1: Default Backtest
Run with your $5 USDT:
```bash
python trading_bot_lite.py
```
Select **1** from the menu.

### Option 2: Custom Backtest
Select **2** from the menu to customize:
- Initial balance
- Hours of data to simulate
- Trade quantity
- Strategy parameters (SMA periods, RSI settings)

## Strategy

The bot uses:
1. **SMA Crossover**: Buy when short SMA (10) crosses above long SMA (30)
2. **RSI Filter**: Only trade when RSI is not overbought (>70) or oversold (<30)

## Termux Tips

- **Colors**: The output uses ANSI colors. If colors don't work, your terminal doesn't support them.
- **Input**: Use the numeric keys to select menu options.
- **Storage**: The script uses minimal resources - perfect for phones.
- **Battery**: Long backtests won't drain your battery.

## Sample Output

```
==================================================
        LITE TRADING BOT - Termux Edition         
==================================================
Starting with $5 USDT paper trading...

Running backtest on sample data...

==================================================
              TRADING BOT DASHBOARD               
==================================================
Current Balance: $4.89
Total Value:     $4.89
Open Positions:  0
Total Trades:    1
Win Rate:        0.0%

--- TRADE HISTORY ---
Type   | Entry Time       |    Entry | Exit Time        |     Exit |   Profit
-------------------------------------------------------------------------------------
  SELL   | 2026-09-23 08:55 | $50960.34 | 2026-09-23 08:55 | $52089.57 | -$0.1129

==================================================
                 BACKTEST SUMMARY                 
==================================================
Initial Balance:  $5.00
Final Balance:    $4.89
Total Profit:     $-0.11 (-2.26%)
Total Trades:     1
Winning Trades:   0
Losing Trades:    1
Win Rate:         0.0%
```

## Customization

Edit `trading_bot_lite.py` to change:
- Default initial balance
- Strategy parameters
- Sample data generation
- Trade quantity

## Requirements

- Python 3.6+
- Termux (or any terminal)
- No other dependencies!

## Why This Works on Termux

Unlike the full version that requires numpy/pandas (which can be hard to compile on Android), this lite version:
- Uses pure Python lists instead of pandas DataFrames
- Implements SMA and RSI manually
- Has no C extensions to compile
- Runs fast on ARM processors

## License

MIT License - Free for personal and educational use.
